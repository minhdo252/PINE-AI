from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from logic_flow import agent

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/start-call")
async def start_call(customer_id: str = Form(...)):
    # Stream câu chào
    return StreamingResponse(agent.process_stream(customer_id, None), media_type="application/x-ndjson")

@app.post("/chat-voice")
async def chat_voice(customer_id: str = Form(...), file: UploadFile = File(...)):
    audio_bytes = await file.read()
    # Stream câu trả lời
    return StreamingResponse(agent.process_stream(customer_id, audio_bytes), media_type="application/x-ndjson")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)