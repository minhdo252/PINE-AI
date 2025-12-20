import time

class LowDataStrategy:
    def __init__(self, llm_client, data_engine):
        self.llm_client = llm_client
        self.data_engine = data_engine

    # --- KỊCH BẢN "VĂN NÓI" (HUMANIZED SCRIPT) ---
    # Nội dung gốc của bạn đã được chuyển sang giọng văn chia sẻ, thêm từ nối.
    CORE_MESSAGE = (
        "Dạ, em rất xin lỗi vì trải nghiệm mạng vừa qua chưa đáp ứng được nhu cầu công việc của mình."
        "Sau khi kiểm tra, em thấy gói cước hiện tại của mình tập trung nhiều ưu đãi miễn phí cho các mạng xã hội (Facebook, TikTok...), "
        "tuy nhiên dung lượng Data tốc độ cao chung để dùng cho việc họp online, check mail hay truy cập hệ thống thì lại hơi hạn chế.\n\n"
        "Với nhu cầu làm việc cần kết nối ổn định, bên em hiện có các gói chuyên biệt với dung lượng tốc độ cao lớn hơn hẳn, "
        "giúp đường truyền mượt mà ngay cả trong giờ cao điểm mà không bị giới hạn ứng dụng.\n\n"
        "Em xin phép giới thiệu sơ qua về quyền lợi gói này để mình xem thử có phù hợp hơn không ạ?"
    )

    def execute(self, customer_id, complaint_text):
        # 1. TRÍCH XUẤT DỮ LIỆU
        ctx = self.data_engine.get_full_context(customer_id)
        if not ctx: return "Lỗi: Không tìm thấy khách hàng."
        
        # Log kiểm tra
        print(f"   ⚡ [Strategy LowData] ID {customer_id}: Input: '{complaint_text}'")

        # 2. XÂY DỰNG PROMPT
        prompt = f"""
        VAI TRÒ: Bạn là nhân viên Kỹ thuật & CSKH tận tâm, giọng điệu nhẹ nhàng.
        
        DỮ LIỆU ĐẦU VÀO:
        - Phàn nàn của khách: "{complaint_text}"
        - Nội dung cốt lõi (CORE MESSAGE):
        '''
        {self.CORE_MESSAGE}
        '''

        NHIỆM VỤ:
        Phản hồi khách hàng dựa trên CORE MESSAGE.

        YÊU CẦU VỀ GIỌNG ĐIỆU (TONE & VOICE):
        1. **Mở đầu:** Đồng cảm ngay lập tức với sự bất tiện của khách.
        2. **Thân bài:** Sử dụng nội dung CORE MESSAGE.
           - Giữ nguyên các từ nối tạo nhịp điệu: "Thực sự", "Tuy nhiên", "Do đó", "Cứ để em".
           - Tránh giải thích kỹ thuật khô khan, hãy nói như đang chia sẻ mẹo vặt.
        
        QUY TẮC AN TOÀN (ANTI-HALLUCINATION):
        - Tuyệt đối KHÔNG tự bịa ra nguyên nhân khác (virus, hack...) ngoài những gì đã nêu.
        - Tuyệt đối KHÔNG hứa tặng cụ thể bao nhiêu GB (chỉ nói "hỗ trợ tặng data bổ sung" như kịch bản).
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
                    "chi phí phát sinh": "chi phí ngoài ý muốn" # Chuẩn hóa từ ngữ
                }
                for old, new in replacements.items():
                    final_text = final_text.replace(old, new)
                
                return final_text
            except Exception as e:
                # Fallback: Trả về kịch bản cứng nếu API lỗi
                return "Dạ, em rất tiếc về trải nghiệm này ạ. " + self.CORE_MESSAGE
        else:
            return "Lỗi: Chưa kết nối LLM Client."