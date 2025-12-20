import time

class CompetitorStrategy:
    def __init__(self, llm_client, data_engine):
        self.llm_client = llm_client
        self.data_engine = data_engine

    # --- KỊCH BẢN CHUẨN (SOURCE OF TRUTH) ---
    # Đây là nội dung an toàn tuyệt đối mà bạn đã duyệt. 
    # AI sẽ sử dụng nội dung này làm xương sống, không được tự bịa thêm.
    CORE_MESSAGE = (
        "Thực sự thì việc mình cân nhắc tìm phương án tiết kiệm hơn là điều rất dễ hiểu và hợp lý thôi ạ.\n\n"
        "Tuy nhiên, em cũng xin phép chia sẻ thêm một chút là mỗi nhà mạng sẽ có thế mạnh riêng về vùng phủ sóng "
        "hay độ ổn định, nên trải nghiệm thực tế đôi khi sẽ khác nhau. "
        "Bởi vì nhiều khi, việc giữ được đường truyền ổn định để mình làm việc, giải trí "
        "lại quan trọng hơn là một chút chênh lệch nhỏ về giá cả.\n\n"
        "Do đó, trước khi mình đưa ra quyết định cuối cùng, mình cứ để em kiểm tra lại xem hiện tại "
        "có chương trình ưu đãi nào tốt hơn để 'tối ưu chi phí' cho mình không nhé?\n\n"
        "Còn nếu sau khi cân nhắc mà mình vẫn muốn ngưng sử dụng, thì chắc chắn bên em sẽ hỗ trợ mình "
        "theo đúng quy trình, nhanh chóng và minh bạch ạ."
    )

    def execute(self, customer_id, complaint_text):
        # 1. TRÍCH XUẤT DỮ LIỆU
        ctx = self.data_engine.get_full_context(customer_id)
        if not ctx: return "Lỗi: Không tìm thấy khách hàng."
        
        # Log kiểm tra
        cust = ctx.get('customer', {})
        print(f"   ⚡ [Strategy Competitor] ID {customer_id}: Xử lý khiếu nại giá/đối thủ. Input: '{complaint_text}'")

        # 2. XÂY DỰNG PROMPT (GROUNDED GENERATION)
        # Kỹ thuật: In-Context Learning với Ràng buộc âm (Negative Constraints)
        
        prompt = f"""
        VAI TRÒ: Bạn là người bạn đồng hành tin cậy của khách hàng (CSKH).
        
        DỮ LIỆU ĐẦU VÀO:
        - Lời khách hàng: "{complaint_text}"
        - Nội dung chính (CORE MESSAGE):
        '''
        {self.CORE_MESSAGE}
        '''

        NHIỆM VỤ:
        Hãy tạo ra câu trả lời hoàn chỉnh.
        
        BƯỚC 1: MỞ ĐẦU (Đồng cảm & Thân thiện)
        - Viết một câu mở đầu thể hiện sự thấu hiểu.
        - BẮT BUỘC dùng từ: "hợp lý" (thay cho chính đáng), "chia sẻ với mình".
        - Ví dụ: "Dạ, em hoàn toàn chia sẻ với mình về vấn đề chi phí ạ. Em hiểu việc mình cân nhắc phương án tiết kiệm hơn là điều rất hợp lý."

        BƯỚC 2: THÂN BÀI (Giải pháp)
        - Nối tiếp bằng nội dung trong phần "CORE MESSAGE" ở trên.
        - Giữ nguyên các từ khóa: "tối ưu chi phí", "cam kết hỗ trợ", "minh bạch".
        
        QUY TẮC AN TOÀN (ANTI-HALLUCINATION):
        - Tuyệt đối KHÔNG sáng tạo thêm gói cước hay cam kết nào ngoài Core Message.
        - Xưng hô: Chỉ dùng "Mình" và "Em".

        OUTPUT: Trả về câu trả lời trọn vẹn, giọng điệu nhẹ nhàng, chân thành.
        Hãy trả lời theo một đoạn văn bản hoàn chỉnh. Hãy đảm bảo sẵn sàng để có thể đọc liền mạch bởi text to speech. Ngoài ra đoạn văn cần có tiết tấu chậm, dễ nghe.
        """

        # 3. GỌI LLM
        if self.llm_client:
            try:
                # Gọi API (Giả lập)
                response = self.llm_client.generate_content(prompt)
                
                # Double-check (Lớp bảo vệ cuối cùng bằng code)
                # Nếu AI lỡ miệng dùng "Anh/Chị", ta cưỡng chế replace ngay lập tức
                final_text = response.text.replace("Anh", "Mình").replace("Chị", "Mình").replace("Quý khách", "Mình").replace("bạn", "mình")
                
                return final_text
            except Exception as e:
                # Fallback an toàn nếu AI sập: Trả về nguyên văn kịch bản gốc
                return self.CORE_MESSAGE
        else:
            return "Lỗi: Chưa kết nối LLM Client."