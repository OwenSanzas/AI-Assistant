import os
import uuid
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf_reader import PDFQuestionAnswering
from identify_intent import identify_intent
from web_search import handle_internet_search
from langchain_openai import ChatOpenAI
from normal_chat import default_chat

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_qa = PDFQuestionAnswering(use_claude=True)
UPLOAD_DIRECTORY = "./uploaded_pdfs"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

session_files = {}
session_histories = {}


@app.post("/upload_pdf")
async def upload_pdf(files: list[UploadFile] = File(...), question: str = Form(...)):
    session_id = str(uuid.uuid4())
    pdf_paths = []

    # 原始用户输入
    user_input = question

    question_base = f"\nGiven are {len(files)} texts of PDFs. Please answer the question by reading the text from the PDFs.\n"
    question = question_base + question + "\nNo explanation is needed. Just answer the question.\n"

    for file in files:
        file_path = os.path.join(UPLOAD_DIRECTORY, f"{session_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(await file.read())
        pdf_paths.append(file_path)

    session_files[session_id] = pdf_paths

    pdf_text = pdf_qa.extract_and_label_texts(pdf_paths)
    answer = pdf_qa.answer_question(pdf_paths, question)

    session_histories[session_id] = [
        {"sender": "System", "text": pdf_text},
        {"sender": "User", "text": user_input},
        {"sender": "AI", "text": answer}
    ]

    return JSONResponse(content={"session_id": session_id, "message": answer})


@app.post("/ask_question")
async def ask_question(session_id: str = Form(...), question: str = Form(...)):
    if session_id not in session_files:
        raise HTTPException(status_code=404, detail="Session not found")

    pdf_paths = session_files[session_id]

    user_input = question
    answer = pdf_qa.answer_question(pdf_paths, question)

    session_histories[session_id].append({"sender": "User", "text": user_input})
    session_histories[session_id].append({"sender": "AI", "text": answer})

    return JSONResponse(content={"message": answer})


@app.post("/process_input")
async def process_input(request: Request):
    data = await request.json()
    user_input = data.get("user_input")
    session_id = data.get("session_id") or str(uuid.uuid4())

    if session_id not in session_histories:
        session_histories[session_id] = []

    intent = identify_intent(user_input, session_histories[session_id])

    if intent == "send_email":
        session_histories[session_id] = []
        response = await handle_send_email(user_input)
    elif intent == "schedule_meeting":
        response = await handle_schedule_meeting(user_input)
    elif intent == "internet_search":
        response = await handle_internet_search(user_input, session_histories[session_id])
    else:
        response = await default_chat(user_input, session_histories[session_id])

    if "normal chat" in response:
        response = await default_chat(user_input, session_histories[session_id])

    # 存储到历史记录
    session_histories[session_id].append({"sender": "User", "text": user_input})
    session_histories[session_id].append({"sender": "AI", "text": response})

    return JSONResponse(content={"session_id": session_id, "message": response})



async def handle_send_email(user_input):
    return "Sending an email..."


async def handle_schedule_meeting(user_input):
    return "Scheduling a meeting..."


@app.get("/get_history")
async def get_history(session_id: str):
    if session_id not in session_histories:
        raise HTTPException(status_code=404, detail="Session not found")

    filtered_history = [
        message for message in session_histories[session_id]
        if message["sender"] in ["User", "AI"]
    ]

    return JSONResponse(content={"history": filtered_history})



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
