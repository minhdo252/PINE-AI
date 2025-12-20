import os
import time
import asyncio
import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

class AIServices:
    def __init__(self):
        # Lấy base URL từ .env
        self.base_url = os.getenv("VNPT_BASE_URL", "https://api.idg.vnpt.vn")
        
        # Khởi tạo Gemini Client
        gemini_key = os.getenv("GOOGLE_API_KEY")
        self.model_id = os.getenv("GEMINI_MODEL_ID", "gemini-3-flash-preview")
        
        try:
            if gemini_key:
                self.client = genai.Client(api_key=gemini_key)
            else:
                print("⚠️ Cảnh báo: Chưa cấu hình GOOGLE_API_KEY trong file .env")
        except Exception as e: 
            print(f"❌ Lỗi khởi tạo Gemini: {e}")

    # --- 1. STT (GEMINI) ---
    async def speech_to_text(self, audio_content: bytes) -> str:
        print(f"🎤 [STT] Size: {len(audio_content)}")
        try:
            # PROMPT CHUYÊN DỤNG CHO VIỄN THÔNG VNPT
            system_prompt = (
                "Hãy đóng vai là một công cụ Speech-to-Text chính xác. "
                "Chỉ được nói về chủ đề viễn thông"
                "Nhiệm vụ của bạn là chuyển đổi file âm thanh này thành văn bản tiếng Việt. "
                "Chỉ trả về đúng nội dung văn bản khách hàng nói, không thêm bất kỳ lời dẫn, giải thích hay dấu câu dư thừa nào."
            )

            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_bytes(data=audio_content, mime_type="audio/webm"),
                    system_prompt
                ]
            )
            text = response.text.strip() if response.text else ""
            return text
        except Exception as e:
            print(f"❌ STT Error: {e}")
            return ""

    # --- 2. TTS (VNPT) ---
    async def text_to_speech(self, text: str) -> bytes:
        if not text: return None
        print(f"🔊 [VNPT TTS] Tạo: {text[:20]}...")
        
        # Lấy Key từ .env
        VNPT_ID = os.getenv("VNPT_TTS_TOKEN_ID")
        VNPT_KEY = os.getenv("VNPT_TTS_TOKEN_KEY")
        VNPT_ACCESS = os.getenv("VNPT_TTS_ACCESS_TOKEN")

        if not all([VNPT_ID, VNPT_KEY, VNPT_ACCESS]):
            print("❌ Lỗi: Thiếu cấu hình VNPT TTS trong file .env")
            return None

        url = f"{self.base_url}/tts-service/v1/standard"
        chk_url = f"{self.base_url}/tts-service/v1/check-status"
        headers = { "Authorization": VNPT_ACCESS, "Token-id": VNPT_ID, "Token-key": VNPT_KEY, "Content-Type": "application/json" }
        payload = {"text": text, "voice_code": "female_north", "speed": 0, "audio_format": "wav"}

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, headers=headers, json=payload, timeout=10.0)
                if res.status_code != 200:
                    print(f"❌ VNPT Error: {res.text}")
                    return None
                tid = res.json().get("object", {}).get("text_id")
                if not tid: return None

                for _ in range(25): # Tăng thời gian chờ
                    await asyncio.sleep(0.5) 
                    r = await client.post(chk_url, headers=headers, json={"text_id": tid}, timeout=10.0)
                    if r.status_code == 200:
                        d = r.json()
                        if d.get("object", {}).get("code") == "success":
                            link = d["object"]["playlist"][0]["audio_link"]
                            dl = await client.get(link, timeout=20.0)
                            return dl.content
            except Exception as e: print(f"❌ TTS Ex: {e}")
        return None

    # --- 3. SMARTBOT ---
    async def chat_smartbot(self, user_text: str, session_id: str = None) -> str:
        # Lấy Key từ .env
        SB_URL = os.getenv("SMARTBOT_URL")
        SB_TOK = os.getenv("SMARTBOT_ACCESS_TOKEN")
        SB_ID = os.getenv("SMARTBOT_TOKEN_ID")
        SB_KEY = os.getenv("SMARTBOT_TOKEN_KEY")
        SB_BOT = os.getenv("SMARTBOT_BOT_ID")

        if not all([SB_URL, SB_TOK, SB_ID, SB_KEY, SB_BOT]):
             print("❌ Lỗi: Thiếu cấu hình SmartBot trong file .env")
             return None

        headers = { "Authorization": SB_TOK, "Content-Type": "application/json", "Token-Id": SB_ID, "Token-Key": SB_KEY }
        # Nếu không có session_id thì tự tạo
        real_sid = session_id if session_id else f"s{int(time.time())}"
        
        payload = { "bot_id": SB_BOT, "text": user_text, "type": "text", "session_id": real_sid, "user_id": "guest" }
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(SB_URL, headers=headers, json=payload, timeout=10.0)
                if res.status_code == 200:
                    d = res.json()
                    if "data" in d and isinstance(d["data"], dict): return d["data"].get("text", "")
                    return d.get("answer", "") or d.get("text", "")
            except: pass
        return None

    # --- 4. FALLBACK GEMINI ---
    async def chat_gemini_fallback(self, prompt: str) -> str:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id, contents=prompt
            )
            return response.text.strip() if response.text else "Dạ em nghe ạ."
        except: return "Dạ em xin ghi nhận ạ."