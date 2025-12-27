import time
import re
import asyncio

class NetworkStrategy:
    def __init__(self, llm_client, data_engine):
        self.llm_client = llm_client
        self.data_engine = data_engine
        
        # [OPTIMIZATION 1] Pre-compile Regex
        self.cleaner_regex = re.compile(
            r"^(.*?>>>|dưới đây là.*?|sau đây là.*?|câu trả lời.*?|đoạn văn.*?|viết lại.*?|output:)", 
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

    # --- KỊCH BẢN GỐC (SOURCE OF TRUTH) ---
    CORE_MESSAGE = (
        "Thực sự em rất xin lỗi vì trải nghiệm vừa qua chưa tương xứng với mức phí mà mình đang sử dụng ạ. "
        "Bởi vì với gói cước hiện tại, đúng ra chất lượng đường truyền cần phải ổn định hơn. "
        "Em xin phép giải thích một số nguyên nhân khiến tốc độ mạng chưa ổn định như mong đợi. "
        "Thiết bị của mình có thể đang bật chế độ tiết kiệm pin hoặc tiết kiệm data. Hoặc có thể thiết bị của mình để nhiều ứng dụng chạy ngầm như mạng xã hội, email, sao lưu ảnh làm ảnh hưởng tốc độ. "
        "Gói hiện tại của mình đang ưu tiên data theo ứng dụng, nên khi phần data tốc độ cao sử dụng hết, hệ thống sẽ tự động chuyển sang data tốc độ thấp. "
        "Nếu nhu cầu của mình là dùng mạng ổn định cho công việc, học tập hoặc giải trí liên tục, mình có thể cân nhắc chuyển sang các gói data dung lượng cố định, tốc độ cao không giới hạn theo ứng dụng. "
        "Gói này sẽ giúp mình dùng ổn định cả ngày mà không lo chậm vào giờ cao điểm. "
        "Chi phí chênh lệch không nhiều nhưng trải nghiệm tốt hơn đáng kể đấy ạ. "
        "Mình có muốn nghe em tư vấn thêm về các gói cụ thể không ạ?"
    )

    # --- HÀM BLOCKING (Dùng cho Fallback hoặc Logic cũ) ---
    def execute(self, customer_id, complaint_text):
        ctx = self.data_engine.get_full_context(customer_id)
        if not ctx: return "Lỗi: Không tìm thấy khách hàng."
        
        print(f"   ⚡ [Strategy Network] ID {customer_id}: Input: '{complaint_text}'")

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
                
                # Cleaning Logic
                if ">>>" in raw_text:
                    final_text = raw_text.split(">>>")[-1].strip()
                else:
                    final_text = self.cleaner_regex.sub("", raw_text).strip()

                if "\n" in final_text:
                    final_text = " ".join([l.strip() for l in final_text.split('\n') if l.strip()])

                replacements = { "Anh/Chị": "Mình", "Quý khách": "Mình", "Anh": "Mình", "Chị": "Mình", "anh": "mình", "chị": "mình", "bạn": "mình" }
                for old, new in replacements.items():
                    if old in final_text or old.lower() in final_text.lower():
                         final_text = final_text.replace(old, new)

                if not final_text: return self.CORE_MESSAGE.replace("\n", " ")
                return final_text
            except Exception as e:
                print(f" [ERROR] Network Strategy: {e}")
                return self.CORE_MESSAGE.replace("\n", " ")
        else:
            return "Lỗi: Chưa kết nối LLM Client."

    # --- [NEW] HÀM STREAMING (Dùng cho Pipeline Gối đầu) ---
    async def execute_stream_gen(self, customer_id, complaint_text):
        print(f"   🌊 [Stream Network] ID {customer_id}")
        
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
                # Gọi thẳng vào Service để lấy Generator
                async for chunk in self.llm_client.ai_service.chat_gemini_stream(prompt):
                    # Lọc sơ bộ dấu >>> nếu nó xuất hiện trong stream
                    if ">>>" in chunk:
                        chunk = chunk.replace(">>>", "")
                    
                    # Yield từng mảnh để Logic Flow xử lý cắt câu
                    yield chunk
            except Exception as e:
                print(f"Stream Error: {e}")
                yield self.CORE_MESSAGE
        else:
            yield self.CORE_MESSAGE