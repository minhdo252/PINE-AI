import time
import re
import asyncio

class CompetitorStrategy:
    def __init__(self, llm_client, data_engine):
        self.llm_client = llm_client
        self.data_engine = data_engine

        self.cleaner_regex = re.compile(
            r"^(.*?>>>|dưới đây là.*?|sau đây là.*?|câu trả lời.*?|đoạn văn.*?|viết lại.*?|output:)", 
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

    CORE_MESSAGE = (
        "Thực sự thì việc mình cân nhắc tìm phương án tiết kiệm hơn là điều rất dễ hiểu và hợp lý thôi ạ. "
        "Tuy nhiên, em cũng xin phép chia sẻ thêm một chút là mỗi nhà mạng sẽ có thế mạnh riêng về vùng phủ sóng "
        "hay độ ổn định, nên trải nghiệm thực tế đôi khi sẽ khác nhau. "
        "Bởi vì nhiều khi, việc giữ được đường truyền ổn định để mình làm việc, giải trí "
        "lại quan trọng hơn là một chút chênh lệch nhỏ về giá cả. "
        "Do đó, trước khi mình đưa ra quyết định cuối cùng, mình cứ để em kiểm tra lại xem hiện tại "
        "có chương trình ưu đãi nào tốt hơn để tối ưu chi phí cho mình không nhé? "
        "Còn nếu sau khi cân nhắc mà mình vẫn muốn ngưng sử dụng, thì chắc chắn bên em sẽ hỗ trợ mình "
        "theo đúng quy trình, nhanh chóng và minh bạch ạ."
    )

    def execute(self, customer_id, complaint_text):
        ctx = self.data_engine.get_full_context(customer_id)
        if not ctx: return "Lỗi: Không tìm thấy khách hàng."
        
        print(f"   ⚡ [Strategy Competitor] ID {customer_id}: Input: '{complaint_text}'")

        prompt = f"""
        Nhiệm vụ: Đóng vai nhân viên CSKH, nói lại nội dung sau với khách (Xưng Em - Mình).
        NỘI DUNG GỐC: "{self.CORE_MESSAGE}"
        YÊU CẦU:
        - Bỏ qua mọi lời chào hỏi, giải thích.
        - Bắt đầu ngay lập tức bằng nội dung hội thoại.
        - KHÔNG xuống dòng.
        BẮT ĐẦU TRẢ LỜI NGAY SAU DẤU MŨI TÊN:
        >>> """

        if self.llm_client:
            try:
                response = self.llm_client.generate_content(prompt)
                raw_text = response.text.strip()

                if ">>>" in raw_text:
                    final_text = raw_text.split(">>>")[-1].strip()
                else:
                    final_text = self.cleaner_regex.sub("", raw_text).strip()

                if "\n" in final_text:
                    final_text = " ".join([l.strip() for l in final_text.split('\n') if l.strip()])

                replacements = { "Anh/Chị": "Mình", "Quý khách": "Mình", "Anh": "Mình", "Chị": "Mình", "anh": "mình", "chị": "mình" }
                for old, new in replacements.items():
                    if old in final_text or old.lower() in final_text.lower():
                        final_text = final_text.replace(old, new)

                if not final_text: return self.CORE_MESSAGE.replace("\n", " ")
                return final_text
            except Exception as e:
                print(f" [ERROR] Competitor Strategy: {e}")
                return self.CORE_MESSAGE.replace("\n", " ")
        else:
            return "Lỗi: Chưa kết nối LLM Client."

    # --- [NEW] HÀM STREAMING ---
    async def execute_stream_gen(self, customer_id, complaint_text):
        print(f"   🌊 [Stream Competitor] ID {customer_id}")
        
        prompt = f"""
        Nhiệm vụ: Đóng vai nhân viên CSKH, nói lại nội dung sau với khách (Xưng Em - Mình).
        NỘI DUNG GỐC: "{self.CORE_MESSAGE}"
        YÊU CẦU:
        - Bắt đầu ngay lập tức bằng nội dung hội thoại.
        - KHÔNG có lời dẫn.
        BẮT ĐẦU TRẢ LỜI NGAY SAU DẤU MŨI TÊN:
        >>> """

        if self.llm_client and hasattr(self.llm_client, 'ai_service'):
            try:
                async for chunk in self.llm_client.ai_service.chat_gemini_stream(prompt):
                    if ">>>" in chunk:
                        chunk = chunk.replace(">>>", "")
                    yield chunk
            except Exception as e:
                print(f"Stream Error: {e}")
                yield self.CORE_MESSAGE
        else:
            yield self.CORE_MESSAGE