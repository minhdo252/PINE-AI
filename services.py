import os
import time
import asyncio
import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

class AIServices:
    def __init__(self):
        self.base_url = os.getenv("VNPT_BASE_URL", "https://api.idg.vnpt.vn")
        
        gemini_key = os.getenv("GOOGLE_API_KEY")
        self.model_id = os.getenv("GEMINI_MODEL_ID", "gemini-3.0-flash-exp") 
        
        try:
            if gemini_key:
                self.client = genai.Client(api_key=gemini_key)
            else:
                print("⚠️ Cảnh báo: Chưa cấu hình GOOGLE_API_KEY")
        except Exception as e: 
            print(f"❌ Lỗi khởi tạo Gemini: {e}")

    # --- 1. STT (GEMINI) ---
    async def speech_to_text(self, audio_content: bytes) -> str:
        if not audio_content or len(audio_content) < 1000: return ""
        print(f"🎤 [STT] Size: {len(audio_content)}")
        try:
            system_prompt = (
                "Bạn là công cụ Speech-to-Text chính xác cho viễn thông VNPT. "
                "Nhiệm vụ: Chuyển đổi âm thanh thành văn bản tiếng Việt. "
                "YÊU CẦU QUAN TRỌNG: "
                "1. Chỉ trả về văn bản khách hàng nói. "
                "2. Nếu âm thanh chỉ là tiếng ồn, tiếng thở, khoảng lặng hoặc không rõ lời: HÃY TRẢ VỀ CHUỖI RỖNG (EMPTY STRING). "
                "3. Tuyệt đối KHÔNG tự bịa ra câu hỏi hoặc nội dung nếu không nghe thấy gì."
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

    # --- 2. TTS (VNPT - TỐI ƯU SMART POLLING) ---
    async def text_to_speech(self, text: str) -> bytes:
        if not text: return None
        # Log ngắn gọn
        print(f"🔊 [VNPT TTS] Request: {text[:30]}...")
        
        VNPT_ID = os.getenv("VNPT_TTS_TOKEN_ID")
        VNPT_KEY = os.getenv("VNPT_TTS_TOKEN_KEY")
        VNPT_ACCESS = os.getenv("VNPT_TTS_ACCESS_TOKEN")

        if not all([VNPT_ID, VNPT_KEY, VNPT_ACCESS]):
            print("❌ Thiếu cấu hình VNPT TTS")
            return None

        url = f"{self.base_url}/tts-service/v1/standard"
        chk_url = f"{self.base_url}/tts-service/v1/check-status"
        headers = { "Authorization": VNPT_ACCESS, "Token-id": VNPT_ID, "Token-key": VNPT_KEY, "Content-Type": "application/json" }
        payload = {"text": text, "voice_code": "female_north", "speed": 0, "audio_format": "wav"}

        async with httpx.AsyncClient() as client:
            try:
                # 1. Gửi request tạo file (Timeout ngắn 5s để fail fast)
                res = await client.post(url, headers=headers, json=payload, timeout=5.0)
                if res.status_code != 200:
                    print(f"❌ VNPT Error: {res.text}")
                    return None
                tid = res.json().get("object", {}).get("text_id")
                if not tid: return None

                # 2. SMART POLLING (Check nhanh cho câu ngắn để giảm độ trễ)
                # Câu ngắn (< 30 ký tự) -> check mỗi 0.1s
                # Câu dài -> check mỗi 0.3s
                sleep_time = 0.1 if len(text) < 30 else 0.3
                
                # Loop tối đa 30 lần (khoảng 3-9s tùy độ dài)
                for _ in range(30): 
                    await asyncio.sleep(sleep_time) 
                    
                    r = await client.post(chk_url, headers=headers, json={"text_id": tid}, timeout=5.0)
                    if r.status_code == 200:
                        d = r.json()
                        status = d.get("object", {}).get("status", "")
                        
                        # Thành công -> Tải file
                        if d.get("object", {}).get("code") == "success":
                            link = d["object"]["playlist"][0]["audio_link"]
                            dl = await client.get(link, timeout=15.0)
                            return dl.content
                        
                        # Thất bại -> Dừng ngay
                        if status == "failed": break
                            
            except Exception as e: print(f"❌ TTS Ex: {e}")
        return None

    # --- 3. SMARTBOT ---
    async def chat_smartbot(self, user_text: str, session_id: str = None) -> str:
        SB_URL = os.getenv("SMARTBOT_URL")
        SB_TOK = os.getenv("SMARTBOT_ACCESS_TOKEN")
        SB_ID = os.getenv("SMARTBOT_TOKEN_ID")
        SB_KEY = os.getenv("SMARTBOT_TOKEN_KEY")
        SB_BOT = os.getenv("SMARTBOT_BOT_ID")

        if not all([SB_URL, SB_TOK, SB_ID, SB_KEY, SB_BOT]): return None

        headers = { "Authorization": SB_TOK, "Content-Type": "application/json", "Token-Id": SB_ID, "Token-Key": SB_KEY }
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

    # --- 4. FALLBACK GEMINI (BLOCKING) ---
    async def chat_gemini_fallback(self, prompt: str) -> str:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id, contents=prompt
            )
            return response.text.strip() if response.text else "Dạ em nghe ạ."
        except: return "Dạ em xin ghi nhận ạ."

    # --- [QUAN TRỌNG] 5. GEMINI STREAMING (CHO PIPELINE) ---
    # Hàm này bắt buộc phải có để Logic Flow gọi được
    async def chat_gemini_stream(self, prompt: str):
        try:
            # Dùng generate_content_stream để trả về Generator
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.model_id,
                contents=prompt
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"❌ Gemini Stream Error: {e}")
            yield ""