import sys
import json
import asyncio
import base64
import re
import time
import unicodedata 
import random
from services import AIServices
from database import db

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
            try: text = future.result(timeout=10)
            except Exception: text = "Dạ, em nghe rõ ạ."
            return type('obj', (object,), {'text': text})()
        else:
            return type('obj', (object,), {'text': "Dạ vâng ạ."})()

# --- CONTROLLER CHÍNH ---
class TelesalesAgent:
    def __init__(self):
        print("\n" + "="*40)
        print(" [SYSTEM] KHỞI ĐỘNG LOGIC v2.8 (FIX STATIC TIMING)")
        print(" [SYSTEM] Chế độ: Gửi Metrics trước Text ở mọi kịch bản")
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

        self.sentence_split_regex = re.compile(r'(?<=[.?!;])\s+')

    def _load_scripts(self):
        try:
            with open('final_voice_scripts.json', 'r', encoding='utf-8') as f:
                scripts = json.load(f)
                for item in scripts:
                    self.sales_data[str(item['customer_id'])] = item
        except: pass

    # --- HÀM HELPER ĐỂ GỬI METRICS NHANH ---
    def _create_metrics_payload(self, stt_latency, start_process_time, sentiment, intent):
        return json.dumps({
            "type": "metrics_update",
            "data": {
                "latency_stt": round(stt_latency, 2),
                "latency_logic": round(time.time() - start_process_time, 2),
                "sentiment": round(sentiment, 2),
                "intent": intent
            }
        }) + "\n"

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
                
            self.sessions[cid] = {
                'step': 1, 
                'history': [], 
                'pronoun': pronoun,
                'start_time': time.time(),
                'detected_intent': "General"
            }
            
            greeting = f"Dạ, em chào {pronoun} {cust_name}, em là nhân viên CSKH VNPT. Em thấy {pronoun.lower()} đang dùng dịch vụ bên em, không biết quá trình sử dụng có ổn định không ạ?"
            greeting = self._normalize_pronouns(greeting, pronoun)
            async for chunk in self._stream_text_and_audio(greeting): yield chunk
            return

        session = self.sessions[cid]
        step = session['step']
        current_pronoun = session.get('pronoun', 'Mình')
        detected_intent = session.get('detected_intent', 'General')
    
        # [FILLER] - Vẫn gửi trước khi có logic (Đồng hồ AI vẫn chạy)
        if user_audio:
            filler_options = [
                "Dạ, {p} chờ em một chút nhé.",
                "Dạ vâng, để em kiểm tra trên hệ thống giúp {p} ngay ạ.",
                "Dạ em nghe rõ rồi ạ, {p} đợi em xíu nhé.",
                "Vâng ạ, em đang tra cứu thông tin cho {p} đây ạ.",
                "Dạ, {p} giữ máy giúp em vài giây nhé."
            ]
            chosen_template = random.choice(filler_options)
            filler_text = chosen_template.format(p=current_pronoun.lower())
            async for chunk in self._stream_text_and_audio(filler_text): yield chunk

        # 2. STT
        start_stt = time.time()
        user_text = await self.ai_service.speech_to_text(user_audio)
        stt_latency = time.time() - start_stt

        if not user_text:
            async for chunk in self._stream_text_and_audio("Alo, em không nghe rõ, nói lại giúp em nhé?"): yield chunk
            return
        
        user_text = unicodedata.normalize('NFC', user_text)
        print(f" [USER] {user_text}")
        session['history'].append(f"User: {user_text}")
        yield json.dumps({"user_text": user_text}) + "\n"

        bot_reply_accumulated = ""
        end_of_mvp = False
        start_process = time.time()
        sentiment_score = 0.0
        
        # --- CORE LOGIC ---
        triggers_agree = ["đồng ý", "đăng ký", "ok", "chốt", "lấy gói này", "được đấy", "nhất trí"]
        is_agreed = False 
        
        if any(w in user_text.lower() for w in triggers_agree):
            is_agreed = True
            negation_patterns = [r"không\s+.*đăng\s+ký", r"không\s+.*đồng\s+ý", r"không\s+.*chốt", r"chưa\s+.*đăng\s+ký", r"không\s+cần", r"không\s+muốn"]
            for p in negation_patterns:
                if re.search(p, user_text.lower()): is_agreed = False; break

        # === NHÁNH 1: KHÁCH ĐỒNG Ý (CHỐT ĐƠN) ===
        if is_agreed:
            print(" [ACTION] Khách đồng ý -> Chốt đơn.")
            response_text = self.MSG_CLOSING.format(pronoun=current_pronoun)
            end_of_mvp = True; session['step'] = 0
            sentiment_score = 1.0
            
            # [FIX] Gửi Metrics TRƯỚC Text
            yield self._create_metrics_payload(stt_latency, start_process, sentiment_score, detected_intent)
            
            response_text = self._normalize_pronouns(response_text, current_pronoun)
            async for chunk in self._stream_text_and_audio(response_text): yield chunk
            bot_reply_accumulated = response_text

        else:
            sentiment_score, _ = self.analyzer.analyze_sentiment(user_text)
            toxic_keywords = ["lừa đảo", "mất dạy", "biến đi", "cút", "hủy ngay", "cắt ngay", "dẹp ngay", "hủy gói", "huỷ gói", "chán ngấy", "không thể chịu", "bực mình", "ức chế"]
            is_toxic_confirmed = False
            if any(kw in user_text.lower() for kw in toxic_keywords):
                print(f" [OVERRIDE] Phát hiện từ khóa TOXIC/HỦY -> Ép sentiment về -5.0.")
                sentiment_score = -5.0
                is_toxic_confirmed = True

            if not is_toxic_confirmed:
                sales_keywords = ["đắt", "giá", "cước", "tiền", "so sánh", "tốc độ", "dung lượng", "nhà mạng", "ưu đãi", "gói", "lý do"]
                if any(kw in user_text.lower() for kw in sales_keywords): sentiment_score = 0.5

            # === NHÁNH 2: TOXIC / HANDOVER ===
            if sentiment_score <= -0.8:
                print(f" [ALERT] Toxic/Huỷ -> Chuyển tư vấn viên.")
                response_text = f"Dạ, em thành thật xin lỗi vì trải nghiệm chưa tốt của {current_pronoun.lower()}. Vấn đề này vượt quá thẩm quyền của em, em sẽ nối máy ngay tới chuyên viên cấp cao để hỗ trợ {current_pronoun.lower()} xử lý yêu cầu ạ."
                detected_intent = "Angry/Handover"
                end_of_mvp = True; session['step'] = 0
                
                # [FIX] Gửi Metrics TRƯỚC Text
                yield self._create_metrics_payload(stt_latency, start_process, sentiment_score, detected_intent)

                response_text = self._normalize_pronouns(response_text, current_pronoun)
                async for chunk in self._stream_text_and_audio(response_text): yield chunk
                bot_reply_accumulated = response_text

            # === NHÁNH 3: TỪ CHỐI ===
            elif re.search(r"(không\s+cần|không\s+muốn|không\s+đăng\s+ký|thôi\s+em)", user_text.lower()):
                print(f" [INTENT] Khách từ chối -> Kết thúc.")
                response_text = f"Dạ vâng ạ, em cảm ơn {current_pronoun.lower()} đã dành thời gian trao đổi. Em chào {current_pronoun.lower()} ạ."
                end_of_mvp = True; session['step'] = 0
                
                # [FIX] Gửi Metrics TRƯỚC Text
                yield self._create_metrics_payload(stt_latency, start_process, sentiment_score, detected_intent)

                response_text = self._normalize_pronouns(response_text, current_pronoun)
                async for chunk in self._stream_text_and_audio(response_text): yield chunk
                bot_reply_accumulated = response_text

            else:
                detected = self.analyzer.classify_issue(user_text)
                issue = detected[0].split(" ('")[0] if detected else None
                
                if issue: 
                    detected_intent = issue
                    session['detected_intent'] = issue

                # === NHÁNH 4: STREAMING STRATEGY ===
                if issue and issue in self.strategies:
                    print(f" [PIPELINE] Kích hoạt Streaming Strategy: {issue}")
                    if step == 1: session['step'] = 2

                    stream_gen = self.strategies[issue].execute_stream_gen(cid, user_text)
                    buffer = ""
                    
                    # [OK] Gửi Metrics TRƯỚC Text (Đã có sẵn ở bản trước)
                    yield self._create_metrics_payload(stt_latency, start_process, sentiment_score, detected_intent)

                    async for chunk_text in stream_gen:
                        buffer += chunk_text
                        if " " in chunk_text or len(buffer) > 10:
                             yield json.dumps({"bot_text": chunk_text}) + "\n"

                        parts = self.sentence_split_regex.split(buffer)
                        if len(parts) > 1:
                            for i in range(len(parts) - 1):
                                sentence = parts[i].strip()
                                if sentence:
                                    sentence = self._normalize_pronouns(sentence, current_pronoun)
                                    bot_reply_accumulated += sentence + " "
                                    print(f"   🌊 [Flow] Gửi TTS câu: {sentence[:30]}...")
                                    async for audio_chunk in self._stream_audio_only(sentence): yield audio_chunk
                            buffer = parts[-1]

                    if buffer.strip():
                        buffer = self._normalize_pronouns(buffer, current_pronoun)
                        bot_reply_accumulated += buffer
                        print(f"   🌊 [Flow] Gửi TTS câu cuối: {buffer[:30]}...")
                        async for chunk in self._stream_audio_only(buffer): yield chunk

                # === NHÁNH 5: KỊCH BẢN TĨNH (SCRIPT GREETING) ===
                elif step == 2 and self.sales_data.get(cid):
                    response_text = self.sales_data.get(cid)['script_greeting']
                    
                    # [FIX] Gửi Metrics TRƯỚC Text
                    yield self._create_metrics_payload(stt_latency, start_process, sentiment_score, detected_intent)

                    response_text = self._normalize_pronouns(response_text, current_pronoun)
                    async for chunk in self._stream_text_and_audio(response_text): yield chunk
                    bot_reply_accumulated = response_text
                
                # === NHÁNH 6: FALLBACK / COMPETITOR (NON-STREAM) ===
                else:
                    if "đắt" in user_text.lower() or "giá" in user_text.lower():
                        response_text = await asyncio.to_thread(self.strategies["Đối thủ"].execute, cid, user_text)
                    else:
                        print(" [MVP] Out of scope -> Fallback Message.")
                        response_text = self.MSG_FALLBACK
                        detected_intent = "Fallback/Out of Scope"
                    
                    # [FIX] Gửi Metrics TRƯỚC Text
                    yield self._create_metrics_payload(stt_latency, start_process, sentiment_score, detected_intent)

                    response_text = self._normalize_pronouns(response_text, current_pronoun)
                    async for chunk in self._stream_text_and_audio(response_text): yield chunk
                    bot_reply_accumulated = response_text

        print(f" [BOT FINAL] {bot_reply_accumulated[:100]}...")

        # --- [QUAN TRỌNG] LƯU DỮ LIỆU VÀO DB ---
        if end_of_mvp:
            print(f" [DB] Đang lưu dữ liệu cuộc gọi cho ID {cid}...")
            
            session_start = session.get('start_time', time.time() - 5)
            duration = time.time() - session_start
            if duration < 1: duration = 1 

            is_ai_resolved = True if detected_intent != "Angry/Handover" else False
            is_upsell = True if is_agreed else False
            cost_vnd = int(1000 + (duration * 50))
            
            sent_label = "neutral"
            if sentiment_score >= 0.4: sent_label = "positive"
            elif sentiment_score <= -0.4: sent_label = "negative"
            csat_val = 5 if sent_label == "positive" else (2 if sent_label == "negative" else 4)

            intent_mapping = {
                "Mạng nghẽn": "network_issue",
                "Mạng yếu": "network_issue",
                "Ít data": "low_data",
                "Hết dung lượng": "low_data",
                "Dung lượng": "low_data",
                "Hủy gói": "cancel_package",
                "Đối thủ": "competitor",
                "Giá cao": "competitor",
                "Buying Signal": "network_issue", 
                "General": "network_issue",
                "Angry/Handover": "cancel_package"
            }
            final_intent = intent_mapping.get(detected_intent, "network_issue")

            try:
                db.add_call(
                    customer_id=cid,
                    duration=int(duration),
                    intent=final_intent, 
                    sentiment=sent_label,
                    ai_resolved=is_ai_resolved,
                    upsell=is_upsell,
                    cost={'value': cost_vnd, 'csat': csat_val}
                )
                print(f" [DB] Lưu thành công.")
            except Exception as e:
                print(f" [DB ERROR] {e}")

            print(f" [MVP END] Gửi thông báo màn hình: {self.MSG_MVP_END}")
            yield json.dumps({ "bot_text": self.MSG_MVP_END, "end_session": True }) + "\n"

    # ... (Các hàm helper giữ nguyên) ...
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

    async def _stream_text_and_audio(self, full_text):
        yield json.dumps({"bot_text": full_text}) + "\n"
        sentences = re.split(r'(?<=[.?!])\s+', full_text)
        buffer = ""
        for s in sentences:
            if not s.strip(): continue
            buffer += s + " "
            if len(buffer) > 10 or s == sentences[-1]:
                async for audio_chunk in self._stream_audio_only(buffer): yield audio_chunk
                buffer = ""

    async def _stream_audio_only(self, text):
        if not text.strip(): return
        try:
            audio_bytes = await self.ai_service.text_to_speech(text)
            if audio_bytes:
                b64 = base64.b64encode(audio_bytes).decode("utf-8")
                yield json.dumps({"audio_base64": b64}) + "\n"
        except: pass

agent = TelesalesAgent()