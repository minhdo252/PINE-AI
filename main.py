import uvicorn
import os
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- IMPORT MODULE CỦA BẠN ---
# Đảm bảo file logic_flow.py và database.py nằm cùng thư mục với main.py
try:
    from logic_flow import agent
    from database import db
except ImportError as e:
    print("❌ LỖI IMPORT: Không tìm thấy file logic_flow.py hoặc database.py")
    print(f"Chi tiết lỗi: {e}")
    # Tạo biến giả để server không bị crash khi test giao diện
    agent = None 
    class FakeDB:
        def get_all_calls(self): return []
        def update_call_rating(self, cid, s, n): pass
    db = FakeDB()

app = FastAPI()

# --- CẤU HÌNH TEMPLATE ---
# directory="." nghĩa là tìm file .html ngay tại thư mục hiện tại
templates = Jinja2Templates(directory=".")

# --- CẤU HÌNH CORS ---
# Cho phép truy cập từ mọi nguồn (quan trọng khi gọi từ Mobile hoặc Web khác)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class FeedbackModel(BaseModel):
    customer_id: str
    stars: int
    note: str = ""

# ============================================================
# PHẦN 1: GIAO DIỆN NGƯỜI DÙNG (FRONTEND)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Mặc định vào trang Dashboard"""
    # Bạn có thể đổi thành "chat.html" nếu muốn trang chủ là Chat
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def view_dashboard(request: Request):
    """Link: /dashboard -> Trả về file dashboard.html"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def view_chat(request: Request):
    """Link: /chat -> Trả về file chat.html"""
    return templates.TemplateResponse("chat.html", {"request": request})

# ============================================================
# PHẦN 2: API XỬ LÝ LOGIC (BACKEND)
# ============================================================

@app.get("/api/dashboard-stats")
async def get_dashboard_stats():
    """API lấy dữ liệu cho Dashboard (Tự động cập nhật)"""
    # Hàm này lấy dữ liệu từ database.py
    data = db.get_all_calls() 
    return {"status": "success", "data": data}

@app.post("/start-call")
async def start_call(customer_id: str = Form(...)):
    """API bắt đầu cuộc gọi (Text/Voice đều dùng được)"""
    if not agent: return {"error": "Chưa có logic_flow.py"}
    
    return StreamingResponse(
        agent.process_stream(customer_id, None), 
        media_type="application/x-ndjson"
    )

@app.post("/chat-voice")
async def chat_voice(customer_id: str = Form(...), file: UploadFile = File(...)):
    """API xử lý file ghi âm gửi lên"""
    if not agent: return {"error": "Chưa có logic_flow.py"}

    audio_bytes = await file.read()
    return StreamingResponse(
        agent.process_stream(customer_id, audio_bytes), 
        media_type="application/x-ndjson"
    )

@app.post("/submit-feedback")
async def submit_feedback(data: FeedbackModel):
    """API nhận đánh giá sao từ khách hàng"""
    db.update_call_rating(data.customer_id, data.stars, data.note)
    return {"status": "success", "message": "Feedback received"}

# ============================================================
# KHỞI CHẠY SERVER
# ============================================================
if __name__ == "__main__":
    print("🚀 PINE SERVER ĐANG CHẠY...")
    print("👉 Dashboard: http://localhost:8000/dashboard")
    print("👉 Chat App:  http://localhost:8000/chat")
    
    # reload=True giúp server tự khởi động lại khi bạn sửa code (Rất tiện lợi)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)