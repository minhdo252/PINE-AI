
# PINE AI - VNPT Smart Contact Center (MVP)

> **Trợ lý ảo Telesales thế hệ mới: Nghe hiểu cảm xúc, Phân tích ý định và Xử lý từ chối thông minh.**

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Status](https://img.shields.io/badge/Status-MVP-orange.svg)
![Backend](https://img.shields.io/badge/FastAPI-Uvicorn-green.svg)
![AI](https://img.shields.io/badge/LLM-Gemini_Powered-purple.svg)

---

## 1. Giới thiệu dự án

**PINE AI** là giải pháp Voice Bot dành cho Tổng đài thông minh (Smart Contact Center) của VNPT. Khác với chatbot truyền thống chỉ phản hồi theo từ khóa, PINE AI sở hữu "trí tuệ cảm xúc" giúp:
1.  **Phân biệt thái độ:** Nhận biết khách hàng đang giận dữ (Toxic) hay chỉ đang khó tính/mặc cả.
2.  **Bảo vệ cơ hội bán hàng:** Tự động phát hiện các câu chê giá/so sánh đối thủ để kích hoạt kịch bản thuyết phục thay vì cúp máy.
3.  **Real-time Metrics:** Hiển thị chỉ số cảm xúc và độ trễ ngay trên màn hình tư vấn viên.

---

## 2. Tính năng cốt lõi (Core Features)

### Bộ não phân tích kép (Dual Analysis Engine)
Hệ thống chạy song song 2 luồng phân tích ngay khi khách hàng dứt lời:
* **Sentiment Engine:** Chấm điểm cảm xúc từ `-1.0` (Rất tệ) đến `1.0` (Rất tốt).
* **Intent Classifier:** Phân loại vấn đề (Mạng nghẽn, Giá cước, Ít Data, So sánh đối thủ...).

### Cơ chế "Sales Guard" & "Toxic Filter" (Logic Ưu tiên)
Đây là điểm khác biệt lớn nhất của PINE AI, sử dụng cơ chế phễu lọc 4 tầng:

| Tầng ưu tiên | Loại khách hàng | Dấu hiệu nhận biết | Hành động của Bot |
| :--- | :--- | :--- | :--- |
| **1. Toxic/Churn** | Chửi bới, Hủy gay gắt | *"Lừa đảo", "Cút", "Hủy gói ngay"* | **Ngắt ngay lập tức**, chuyển nhân viên (Handover). |
| **2. Refusal** | Từ chối lịch sự | *"Không cần", "Thôi em"* | **Chào tạm biệt** lịch sự, kết thúc cuộc gọi. |
| **3. Objection** | Chê đắt, So sánh | *"Đắt quá", "Viettel rẻ hơn"* | **Bỏ qua điểm tiêu cực**, kích hoạt `CompetitorStrategy` để thuyết phục. |
| **4. Normal** | Hỏi thông thường | *"Gói này bao nhiêu tiền?"* | Trả lời theo kịch bản bán hàng chuẩn. |

### Dashboard UX Metrics Live
Giao diện hiển thị trực quan các chỉ số kỹ thuật:
* **Latency:** Đo độ trễ xử lý (STT + Logic) tính bằng mili giây.
* **Sentiment Bar:** Thanh cảm xúc chạy theo thời gian thực (Xanh/Vàng/Đỏ).
* **Intent Detected:** Hiển thị ý định vừa phát hiện.

---

## 3. Hướng dẫn Cài đặt & Triển khai

### Bước 1: Chuẩn bị môi trường
Yêu cầu máy tính đã cài:
* [Python 3.9+](https://www.python.org/downloads/)
* [Git](https://git-scm.com/)

### Bước 2: Clone dự án
```bash
git clone [https://github.com/YourUsername/vnpt-voice-bot.git](https://github.com/YourUsername/vnpt-voice-bot.git)
cd vnpt-voice-bot

```

### Bước 3: Tạo môi trường ảo (Virtual Environment)

Giúp cách ly thư viện dự án, tránh xung đột với hệ thống.

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# MacOS/Linux
python3 -m venv venv
source venv/bin/activate

```

### Bước 4: Cài đặt thư viện phụ thuộc

```bash
pip install -r requirements.txt

```

*(File `requirements.txt` bao gồm: `fastapi`, `uvicorn`, `websockets`, `python-dotenv`, `google-generativeai`, ...)*

### Bước 5: Cấu hình bảo mật (.env)

Tạo file `.env` tại thư mục gốc (ngang hàng với `main.py`) và điền API Key:

```env
# --- GEMINI CONFIG ---
GOOGLE_API_KEY=
GEMINI_MODEL_ID=gemini-3-flash-preview

# --- VNPT GENERAL ---
VNPT_BASE_URL=https://api.idg.vnpt.vn

# --- VNPT TTS CONFIG ---
VNPT_TTS_TOKEN_ID=
VNPT_TTS_TOKEN_KEY=
VNPT_TTS_ACCESS_TOKEN=

# --- VNPT SMARTBOT CONFIG ---
SMARTBOT_URL=https://assistant-stream.vnpt.vn/v1/conversation
SMARTBOT_ACCESS_TOKEN="
SMARTBOT_TOKEN_ID=
SMARTBOT_TOKEN_KEY=
SMARTBOT_BOT_ID=
```

> **Lưu ý:** File `.env` đã được thêm vào `.gitignore` để không bị lộ khi đẩy lên GitHub.

### Bước 6: Khởi chạy Server

```bash
# Chạy server với tính năng tự động reload khi sửa code
uvicorn main:app --reload

```

Sau khi chạy thành công, mở trình duyệt tại địa chỉ: `http://localhost:8000`.

---

##  4. Cấu trúc dự án

```
vnpt-voice-bot/
├── .env                 # Biến môi trường (Chứa API Key)
├── .gitignore           # Danh sách file bị Git bỏ qua (rác, log, env)
├── README.md            # Tài liệu hướng dẫn này
├── requirements.txt     # Danh sách thư viện cần cài
│
├── main.py              # Server Backend (FastAPI), xử lý WebSocket
├── logic_flow.py        # [CORE] Bộ não điều phối hội thoại & Logic ưu tiên
├── analyze.py           # [CORE] Bộ phân tích Cảm xúc & Từ khóa (Sentiment Engine)
├── services.py          # Các module vệ tinh (STT, TTS, LLM Connector)
├── data_engine.py       # Giả lập database khách hàng (CSV/JSON)
├── test_fr.html           # Giao diện Frontend (Dashboard + UX Metrics)
├── strategy_competitor.py  # Xử lý khi khách so sánh đối thủ
├── strategy_low_data.py    # Xử lý khi khách kêu hết data
└── strategy_network.py     # Xử lý khi khách kêu mạng lag

```

---

##  5. Hướng dẫn Git (Dành cho Dev)

Để đẩy code lên GitHub an toàn và sạch sẽ:

1. **Khởi tạo kho (nếu chưa có):**
```bash
git init

```


2. **Thêm file vào vùng chờ (Staging):**
*(Git sẽ tự động bỏ qua các file trong .gitignore)*
```bash
git add .

```


3. **Lưu phiên bản (Commit):**
```bash
git commit -m "Update logic: Sales Guard & Toxic Filter v2.2"

```


4. **Đẩy lên GitHub:**
```bash
git push origin main

```



---


