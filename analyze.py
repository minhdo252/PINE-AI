import time

class VN_VoiceBot_Parallel:
    def __init__(self):
        # -------------------------------------------------------------
        # 1. BỘ TỪ KHÓA PHÂN LOẠI VẤN ĐỀ
        # -------------------------------------------------------------
        self.issue_lexicon = {
            "Mạng nghẽn": ["nghẽn", "lag", "chậm", "quay", "xoay", "yếu", "chập chờn", "load không nổi", "rùa bò", "không vào nổi"],
            "Đối thủ": ["viettel", "vinaphone", "fpt", "bên kia", "nhà mạng khác", "rẻ hơn", "gói khác", "ưu đãi hơn", "đắt", "so sánh", "giá", "cước", "cao quá"],
            "Ít data": ["hết data", "ít data", "dung lượng thấp", "không đủ dùng", "nhanh hết", "thêm gb", "ít quá", "hết sạch", "trừ tiền"]
        }

        # -------------------------------------------------------------
        # 2. BỘ TỪ ĐIỂN CẢM XÚC
        # -------------------------------------------------------------
        self.vn_sentiment_lexicon = {
            # === TÍCH CỰC ===
            "ngon": 0.8, "tốt": 0.8, "nhanh": 0.9, "mượt": 0.9, 
            "hài_lòng": 1.0, "tuyệt_vời": 1.0, "ổn": 0.5, "thích": 0.8, "ok": 0.5,

            # === OBJECTIONS (TRUNG TÍNH - ĐỂ TƯ VẤN) ===
            "đắt": 0.0, "đắt_hơn": 0.0, "không_hề_rẻ": 0.0,
            "so_sánh": 0.0, "bên_kia": 0.0, "nhà_mạng_khác": 0.0,
            "không_hơn": 0.0, "không_thay_đổi": 0.0,
            "lý_do_gì": 0.0, "tiếp_tục": 0.0,
            "không_thấy": 0.0, "giá_cao": 0.0,
            
            # === VẤN ĐỀ KỸ THUẬT (TIÊU CỰC NHẸ) ===
            "hết_sạch": -0.2, "ít_quá": -0.2, "chậm": -0.2, "lag": -0.2,
            "không_phù_hợp": -0.2, "thất_vọng": -0.3,

            # === TOXIC/CHURN (TIÊU CỰC NẶNG -> CẮT MÁY) ===
            "huỷ_gói": -5.0, "hủy_gói": -5.0,
            "cắt_mạng": -5.0, "dừng_dịch_vụ": -5.0,
            "lừa_đảo": -5.0, "mất_dạy": -5.0, "cút": -5.0,
            "không_muốn_nghe": -5.0, "lập_tức": -4.0, "ngay_lập_tức": -4.0,
            "chán_ngấy": -5.0, "bực_mình": -4.0, "điên": -5.0,
            "không_thể_chịu": -5.0, "không_chịu_được": -5.0,
            "chán": -3.0
        }

    def classify_issue(self, text):
        text = text.lower()
        found_issues = []
        for issue_code, keywords in self.issue_lexicon.items():
            for kw in keywords:
                if kw in text:
                    found_issues.append(f"{issue_code} ('{kw}')")
                    break
        return found_issues

    def analyze_sentiment(self, text):
        text = text.lower()
        total_score = 0.0
        word_count = 0
        detected_words = []

        for word, score in self.vn_sentiment_lexicon.items():
            search_term = word.replace("_", " ")
            if search_term in text:
                total_score += score
                word_count += 1
                detected_words.append(f"{search_term}({score})")

        if word_count > 0:
            avg_score = round(total_score / word_count, 2)
        else:
            avg_score = 0.0

        return avg_score, detected_words