import sys
import json
import asyncio
import base64
import re
import time
import unicodedata 
from services import AIServices

# --- IMPORT MODULE VỆ TINH ---
try:
    from analyze import VN_VoiceBot_Parallel
    from data_engine import DataEngine
    from strategy_competitor import CompetitorStrategy
    from strategy_low_data import LowDataStrategy
    from strategy_network import NetworkStrategy
except ImportError as e:
    print(f" Thiếu file vệ tinh: {e}")
    sys.exit(1)
    
# --- ADAPTER (GIỮ NGUYÊN) ---
class GeminiAdapter:
    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.main_loop = None
    
    def set_main_loop(self, loop):
        self.main_loop = loop

    def generate_content(self, prompt):
        if self.main_loop and self.main_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self.ai_service.chat_gemini_fallback(prompt), 
                self.main_loop
            )
            try:
                text = future.result(timeout=10)
            except Exception:
                text = "Dạ, em nghe rõ ạ."
            return type('obj', (object,), {'text': text})()
        else:
            return type('obj', (object,), {'text': "Dạ vâng ạ."})()

# --- CONTROLLER CHÍNH ---
class TelesalesAgent:
    def __init__(self):
        print("\n" + "="*40)
        print(" [SYSTEM] KHỞI ĐỘNG LOGIC SALES MỚI v2.2")
        print(" [SYSTEM] Chế độ: Ưu tiên phát hiện tiêu cực (Toxic First)")
        print("="*40 + "\n")
        
        self.ai_service = AIServices()
        self.analyzer = VN_VoiceBot_Parallel()
        self.data_engine = DataEngine("test_customer.csv", "product_collection.json")
        self.adapter = GeminiAdapter(self.ai_service)
        
        self.strategies = {
            "Đối thủ": CompetitorStrategy(self.adapter, self.data_engine),
            "Ít data": LowDataStrategy(self.adapter, self.data_engine),
            "Mạng nghẽn": NetworkStrategy(self.adapter, self.data_engine)
        }
        
        self.sales_data = {}
        self._load_scripts()
        self.sessions = {} 
        
        self.MSG_FALLBACK = "Xin lỗi khách hàng nhưng trường hợp này chưa được tích hợp trong MVP. Xin hãy sử dụng những tình huống có trong kịch bản cung cấp."
        self.MSG_CLOSING = "Cảm ơn vì đã dành thời gian để nghe tư vấn, đội kỹ thuật sẽ liên hệ với {pronoun} để tích hợp gói cước sau ạ."
        self.MSG_MVP_END = "Đây là toàn bộ phần MVP của \"Quarter Zip.\""

    def _load_scripts(self):
        try:
            with open('final_voice_scripts.json', 'r', encoding='utf-8') as f:
                scripts = json.load(f)
                for item in scripts:
                    self.sales_data[str(item['customer_id'])] = item
        except: pass

    # --- HÀM XỬ LÝ CHÍNH ---
    async def process_stream(self, customer_id_str, user_audio):
        cid = str(customer_id_str)
        current_loop = asyncio.get_running_loop()
        self.adapter.set_main_loop(current_loop)

        # 1. INIT SESSION
        if cid not in self.sessions or user_audio is None:
            print(f"\n--- NEW SESSION: {cid} ---")
            ctx = self.data_engine.get_full_context(cid)
            cust_data = ctx['customer'] if ctx else {}
            cust_name = cust_data.get('Display_Name', 'Quý khách')
            
            gender_raw = cust_data.get('Gender', '').lower().strip()
            if gender_raw in ['nam', 'male', 'trai', 'mr', 'anh']: pronoun = "Anh"
            elif gender_raw in ['nu', 'nữ', 'female', 'gái', 'ms', 'mrs', 'chị']: pronoun = "Chị"
            else: pronoun = "Mình"
                
            self.sessions[cid] = {'step': 1, 'history': [], 'pronoun': pronoun}
            
            greeting = f"Dạ, em chào {pronoun} {cust_name}, em là nhân viên CSKH VNPT. Em thấy {pronoun.lower()} đang dùng dịch vụ bên em, không biết quá trình sử dụng có ổn định không ạ?"
            
            greeting = self._normalize_pronouns(greeting, pronoun)
            async for chunk in self._stream_response(greeting):
                yield chunk
            return

        session = self.sessions[cid]
        step = session['step']
        current_pronoun = session.get('pronoun', 'Mình')
        
        # 2. STT
        start_stt = time.time()
        user_text = await self.ai_service.speech_to_text(user_audio)
        stt_latency = time.time() - start_stt

        if not user_text:
            async for chunk in self._stream_response("Alo, em không nghe rõ, nói lại giúp em nhé?"):
                yield chunk
            return
        
        user_text = unicodedata.normalize('NFC', user_text)
        print(f" [USER] {user_text}")
        session['history'].append(f"User: {user_text}")
        yield json.dumps({"user_text": user_text}) + "\n"

        bot_reply = ""
        end_of_mvp = False
        start_process = time.time()
        sentiment_score = 0.0
        detected_intent = "General"

        # --- LOGIC XỬ LÝ ---
        triggers_agree = ["đồng ý", "đăng ký", "ok", "chốt", "lấy gói này", "được đấy", "nhất trí"]
        
        # [CHECK 1] LOGIC MUA HÀNG + PHỦ ĐỊNH
        is_agreed = False
        if any(w in user_text.lower() for w in triggers_agree):
            is_agreed = True
            negation_patterns = [
                r"không\s+.*đăng\s+ký", r"không\s+.*đồng\s+ý", r"không\s+.*chốt",
                r"chưa\s+.*đăng\s+ký", r"không\s+cần", r"không\s+muốn"
            ]
            for p in negation_patterns:
                if re.search(p, user_text.lower()):
                    is_agreed = False; break

        if is_agreed:
            print(" [ACTION] Khách đồng ý -> Chốt đơn.")
            bot_reply = self.MSG_CLOSING.format(pronoun=current_pronoun)
            end_of_mvp = True; session['step'] = 0
            detected_intent = "Buying Signal"; sentiment_score = 1.0
        else:
            # 1. Tính điểm cảm xúc gốc (từ analyze.py)
            sentiment_score, _ = self.analyzer.analyze_sentiment(user_text)
            
            # --- [FIX QUAN TRỌNG] ƯU TIÊN KIỂM TRA TOXIC/HỦY TRƯỚC ---
            toxic_keywords = [
                "lừa đảo", "mất dạy", "biến đi", "cút", "hủy ngay", "cắt ngay", 
                "dẹp ngay", "hủy gói", "huỷ gói", "chán ngấy", "không thể chịu", 
                "bực mình", "ức chế"
            ]
            
            # Nếu phát hiện Toxic -> Ép điểm Âm Nặng -> Khóa biến is_toxic
            is_toxic_confirmed = False
            if any(kw in user_text.lower() for kw in toxic_keywords):
                print(f" [OVERRIDE] Phát hiện từ khóa TOXIC/HỦY -> Ép sentiment về -5.0.")
                sentiment_score = -5.0
                is_toxic_confirmed = True

            # --- SAU ĐÓ MỚI KIỂM TRA SALES GUARD (NẾU KHÔNG TOXIC) ---
            # Chỉ kích hoạt chế độ "Sales Guard" (ép điểm dương) khi KHÔNG có từ khóa toxic
            if not is_toxic_confirmed:
                sales_keywords = ["đắt", "giá", "cước", "tiền", "so sánh", "tốc độ", "dung lượng", "nhà mạng", "ưu đãi", "gói", "lý do"]
                if any(kw in user_text.lower() for kw in sales_keywords):
                    print(f" [SALES GUARD] Objection an toàn -> Cưỡng chế sentiment = 0.5")
                    sentiment_score = 0.5

            # --- QUYẾT ĐỊNH CUỐI CÙNG ---
            if sentiment_score <= -0.8:
                print(f" [ALERT] Khách hàng Toxic/Huỷ (Score: {sentiment_score}) -> Chuyển tư vấn viên.")
                bot_reply = f"Dạ, em thành thật xin lỗi vì trải nghiệm chưa tốt của {current_pronoun.lower()}. Vấn đề này vượt quá thẩm quyền của em, em sẽ nối máy ngay tới chuyên viên cấp cao để hỗ trợ {current_pronoun.lower()} xử lý yêu cầu ạ."
                detected_intent = "Angry/Handover"
                end_of_mvp = True; session['step'] = 0
            
            # Xử lý từ chối lịch sự
            elif re.search(r"(không\s+cần|không\s+muốn|không\s+đăng\s+ký|thôi\s+em)", user_text.lower()):
                print(f" [INTENT] Khách từ chối dịch vụ -> Kết thúc.")
                bot_reply = f"Dạ vâng ạ, em cảm ơn {current_pronoun.lower()} đã dành thời gian trao đổi. Em chào {current_pronoun.lower()} ạ."
                detected_intent = "Refusal/Closing"
                end_of_mvp = True; session['step'] = 0

            # Xử lý theo kịch bản (Strategies)
            else:
                detected = self.analyzer.classify_issue(user_text)
                issue = detected[0].split(" ('")[0] if detected else None
                if issue: detected_intent = issue

                if issue and issue in self.strategies:
                    print(f" [EXECUTE] Chạy chiến thuật: {issue}")
                    bot_reply = await asyncio.to_thread(self.strategies[issue].execute, cid, user_text)
                    if step == 1: session['step'] = 2
                
                elif step == 2 and self.sales_data.get(cid):
                    bot_reply = self.sales_data.get(cid)['script_greeting']
                
                else:
                    # Fallback (Phòng hờ)
                    if "đắt" in user_text.lower() or "giá" in user_text.lower():
                         bot_reply = await asyncio.to_thread(self.strategies["Đối thủ"].execute, cid, user_text)
                    else:
                        print(" [MVP] Out of scope -> Fallback Message.")
                        bot_reply = self.MSG_FALLBACK
                        detected_intent = "Fallback/Out of Scope"

        # [METRIC]
        process_latency = time.time() - start_process
        total_latency = stt_latency + process_latency
        
        metrics_payload = {
            "type": "metrics_update",
            "data": {
                "latency_stt": round(stt_latency, 2),
                "latency_logic": round(process_latency, 2),
                "latency_total": round(total_latency, 2),
                "sentiment": round(sentiment_score, 2),
                "intent": detected_intent
            }
        }
        yield json.dumps(metrics_payload) + "\n"

        # --- OUTPUT ---
        bot_reply = self._normalize_pronouns(bot_reply, current_pronoun)
        print(f" [BOT] {bot_reply}")
        
        async for chunk in self._stream_response(bot_reply):
            yield chunk

        if end_of_mvp:
            print(f" [MVP END] Gửi thông báo màn hình: {self.MSG_MVP_END}")
            yield json.dumps({"bot_text": self.MSG_MVP_END}) + "\n"

    # ==========================================================================
    def _normalize_pronouns(self, text, target_pronoun):
        candidates = ["quý khách", "bạn", "mình", "anh", "chị", "các bạn", "khách hàng", "khách"]
        for word in candidates:
            if word.lower() == target_pronoun.lower(): continue
            pattern = r'\b' + re.escape(word) + r'\b'
            text = re.sub(pattern, target_pronoun, text, flags=re.IGNORECASE)

        for _ in range(3):
            pattern = r'(?i)\b' + re.escape(target_pronoun) + r'\s*(?:[.,;]\s*)?' + re.escape(target_pronoun) + r'\b'
            text = re.sub(pattern, target_pronoun, text)

        text = text.strip()
        if text and text.lower().startswith(target_pronoun.lower()):
            text = target_pronoun.capitalize() + text[len(target_pronoun):]
        return text

    async def _stream_response(self, full_text, customer_text=None):
        yield json.dumps({"bot_text": full_text}) + "\n"
        sentences = re.split(r'(?<=[.?!])\s+', full_text)
        buffer_text = ""
        for sentence in sentences:
            if not sentence.strip(): continue
            buffer_text += sentence + " "
            if len(buffer_text) > 10 or sentence == sentences[-1]:
                try:
                    audio_bytes = await self.ai_service.text_to_speech(buffer_text)
                    if audio_bytes:
                        b64 = base64.b64encode(audio_bytes).decode("utf-8")
                        yield json.dumps({"audio_base64": b64}) + "\n"
                except: pass
                buffer_text = ""

agent = TelesalesAgent()