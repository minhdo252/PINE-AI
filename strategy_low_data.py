import time
import re
import asyncio

class LowDataStrategy:
    def __init__(self, llm_client, data_engine):
        self.llm_client = llm_client
        self.data_engine = data_engine

        self.cleaner_regex = re.compile(
            r"^(.*?>>>|dưới đây là.*?|sau đây là.*?|câu trả lời.*?|đoạn văn.*?|viết lại.*?|output:)", 
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

    CORE_MESSAGE = (
        "Dạ, em rất xin lỗi vì trải nghiệm mạng vừa qua chưa đáp ứng được nhu cầu công việc của mình. "
        "Sau khi kiểm tra, em thấy gói cước hiện tại của mình tập trung nhiều ưu đãi miễn phí cho các mạng xã hội như Facebook hay TikTok, "
        "tuy nhiên dung lượng Data tốc độ cao chung để dùng cho việc họp online, check mail hay truy cập hệ thống thì lại hơi hạn chế. "
        "Với nhu cầu làm việc cần kết nối ổn định, bên em hiện có các gói chuyên biệt với dung lượng tốc độ cao lớn hơn hẳn, "
        "giúp đường truyền mượt mà ngay cả trong giờ cao điểm mà không bị giới hạn ứng dụng. "
        "Em xin phép giới thiệu sơ qua về quyền lợi gói này để mình xem thử có phù hợp hơn không ạ?"
    )

    def execute(self, customer_id, complaint_text):
        ctx = self.data_engine.get_full_context(customer_id)
        if not ctx: return "Lỗi: Không tìm thấy khách hàng."
        
        print(f"   ⚡ [Strategy LowData] ID {customer_id}: Input: '{complaint_text}'")

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

                replacements = { "Anh/Chị": "Mình", "Quý khách": "Mình", "Anh": "Mình", "Chị": "Mình", "anh": "mình", "chị": "mình", "chi phí phát sinh": "chi phí ngoài ý muốn" }
                for old, new in replacements.items():
                    if old in final_text or old.lower() in final_text.lower():
                        final_text = final_text.replace(old, new)

                if not final_text: return self.CORE_MESSAGE.replace("\n", " ")
                return final_text
            except Exception as e:
                print(f" [ERROR] LowData Strategy: {e}")
                return self.CORE_MESSAGE.replace("\n", " ")
        else:
            return "Lỗi: Chưa kết nối LLM Client."

    # --- [NEW] HÀM STREAMING ---
    async def execute_stream_gen(self, customer_id, complaint_text):
        print(f"   🌊 [Stream LowData] ID {customer_id}")
        
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