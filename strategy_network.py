import time

class NetworkStrategy:
    def __init__(self, llm_client, data_engine):
        self.llm_client = llm_client
        self.data_engine = data_engine

    # --- KỊCH BẢN "VĂN NÓI" (HUMANIZED SCRIPT) ---
    # Chuyển đổi từ mẫu gốc sang văn phong chia sẻ, thêm từ nối:
    # "Thực sự", "Bởi vì", "Do đó", "Cứ để em", "Thực sự xứng đáng".
    CORE_MESSAGE = (
        "Thực sự em rất xin lỗi vì trải nghiệm vừa qua chưa tương xứng với mức phí mà mình đang sử dụng ạ.\n\n"
        "Bởi vì với gói cước hiện tại, đúng ra chất lượng đường truyền cần phải ổn định hơn, "
        "Em xin phép giải thích một số nguyên nhân khiến tốc độ mạng chưa ổn định như mong đợi.\n\n"
        "Thiết độ của mình có thể đang bật chế độ tiết kiệm pin hoặc tiết kiệm data.Hoặc có thể thiết bị của mình để nhiều ứng dụng chạy ngầm (mạng xã hội, email, sao lưu ảnh,...) "
        "Gói hiện tại của hình hiện tại đang ưu tiên data theo ứng dụng. Khi phần data tốc độ cao sử dụng hết, hệ thống sẽ tự động chuyển sang data tốc độ thấp hoặc data miễn phí cho mạng xã hội. "
        "Nếu nhu cầu của anh chị là dùng mạng ổn định cho công việc, học tập hoặc giải trí liên tục, anh chị có thể cân nhắc chuyển sang các gói data dung lượng cố định, tốc độ cao không giới hạn theo ứng dụng. "
        "Gói này sẽ giúp các anh chị dùng ổn định cả ngày mà không lo chậm vào giờ cao điểm.\n\n"
        "Chi phí chênh lệch không nhiều nhưng trải nghiệm tốt hơn đáng kể đấy ạ. "
        " Anh chị có muốn nghe tư vấn thêm về các gói cụ thể không ạ?"
    )

    def execute(self, customer_id, complaint_text):
        # 1. TRÍCH XUẤT DỮ LIỆU
        ctx = self.data_engine.get_full_context(customer_id)
        if not ctx: return "Lỗi: Không tìm thấy khách hàng."
        
        # Log kiểm tra
        print(f"   ⚡ [Strategy Network] ID {customer_id}: Input: '{complaint_text}'")

        # 2. XÂY DỰNG PROMPT
        prompt = f"""
        VAI TRÒ: Bạn là Chuyên viên Kỹ thuật & CSKH tận tâm, biết lắng nghe.
        
        DỮ LIỆU ĐẦU VÀO:
        - Phàn nàn của khách: "{complaint_text}"
        - Nội dung cốt lõi (CORE MESSAGE):
        '''
        {self.CORE_MESSAGE}
        '''

        NHIỆM VỤ:
        Phản hồi khách hàng dựa trên CORE MESSAGE.

        YÊU CẦU VỀ GIỌNG ĐIỆU (TONE & VOICE):
        1. **Mở đầu:** Nhận lỗi chân thành về việc "Tiền nào của nấy" (Giá cao mà mạng lag).
        2. **Thân bài:** Sử dụng nguyên văn CORE MESSAGE để đảm bảo đúng quy trình kỹ thuật.
           - Giữ các từ đệm: "Thực sự", "Bởi vì", "Do đó", "Cứ để em".
        
        QUY TẮC AN TOÀN (ANTI-HALLUCINATION):
        - Tuyệt đối KHÔNG bịa đặt nguyên nhân kỹ thuật (cá mập cắn cáp, đứt cáp quang biển...) nếu hệ thống không báo.
        - Tuyệt đối KHÔNG hứa đền bù tiền mặt.
        - Xưng hô: BẮT BUỘC dùng "Mình" và "Em".

        OUTPUT: 
        Trả về đoạn hội thoại hoàn chỉnh.
        """

        # 3. GỌI LLM
        if self.llm_client:
            try:
                response = self.llm_client.generate_content(prompt)
                
                # Hậu xử lý: Lớp bảo vệ cuối cùng cho xưng hô
                final_text = response.text
                replacements = {
                    "Anh": "Mình", "Chị": "Mình", "Quý khách": "Mình",
                    "anh": "mình", "chị": "mình",
                    "khu vực sử dụng": "khu vực nhà mình", # Làm cho câu văn ấm áp hơn
                    "chi phí đã bỏ ra": "chi phí mình đã bỏ ra"
                }
                for old, new in replacements.items():
                    final_text = final_text.replace(old, new)
                
                return final_text
            except Exception as e:
                # Fallback: Trả về kịch bản cứng nếu API lỗi
                return self.CORE_MESSAGE
        else:
            return "Lỗi: Chưa kết nối LLM Client."
