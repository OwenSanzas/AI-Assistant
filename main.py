import os
import uuid
import uvicorn
import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf_reader import PDFQuestionAnswering
from identify_intent import identify_intent
from web_search import handle_internet_search
from langchain_openai import ChatOpenAI
from normal_chat import default_chat
from email_handler import handle_send_email
from email_sender import EmailSender
from meeting_handler import handle_schedule_meeting, meeting_handler
from privacy_agent import PrivacyManager
from pydantic import BaseModel


email_sender = EmailSender()
app = FastAPI()

confidential_json_content = os.getenv("CONFIDENTIAL_JSON")

if confidential_json_content:
    print("Writing credentials to credentials.json")
    try:
        with open("credentials.json", "w") as json_file:
            json.dump(json.loads(confidential_json_content), json_file)
    except json.JSONDecodeError:
        print("Error decoding CONFIDENTIAL_JSON. Please check the JSON format.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://ai-assistant-web-3717ccad64aa.herokuapp.com"],
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

        session_histories[session_id].append({"sender": "User", "text": user_input})
        session_histories[session_id].append({
            "sender": "AI",
            "text": "I've prepared an email preview for you. Please review it."
        })
        return JSONResponse(content=response)

    elif intent == "schedule_meeting":
        response = await handle_schedule_meeting(user_input)
        return JSONResponse(content=response)
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

@app.get("/get_history")
async def get_history(session_id: str):
    if session_id not in session_histories:
        raise HTTPException(status_code=404, detail="Session not found")

    filtered_history = [
        message for message in session_histories[session_id]
        if message["sender"] in ["User", "AI"]
    ]

    return JSONResponse(content={"history": filtered_history})


@app.post("/send_email")
async def send_email(email_data: dict):
    result = await email_sender.send_email(email_data)
    if result["success"]:
        return JSONResponse(content={
            "status": "success",
            "message": "Email sent successfully"
        })
    else:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": result["message"]
            }
        )


@app.post("/confirm_meeting")
async def confirm_meeting(meeting_data: dict):
    required_fields = ["title", "description", "start_time", "end_time", "attendees"]
    if not all(field in meeting_data for field in required_fields):
        raise HTTPException(status_code=400, detail="Missing meeting information")

    try:
        meeting_result = await meeting_handler.create_meeting(meeting_data)

        if not meeting_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to create meeting")

        meeting_link = meeting_result["meeting_link"]
        privacy_manager = PrivacyManager()

        sender = f"{privacy_manager.get_sender_name()} <{privacy_manager.get_sender_email()}>"

        for attendee in meeting_data["attendees"]:
            email_data = {
                "sender": sender,
                "recipient": attendee,
                "subject": f"Meeting Invitation: {meeting_data['title']}",
                "content": (
                    f"You are invited to a meeting. Here are the details:\n\n"
                    f"Title: {meeting_data['title']}\n"
                    f"Time: {meeting_data['start_time']} to {meeting_data['end_time']}\n"
                    f"Description: {meeting_data['description']}\n"
                    f"Meeting Link: {meeting_link}\n\n"
                    f"{privacy_manager.get_signature()}"
                )
            }

            email_result = await email_sender.send_email(email_data)

            if not email_result["success"]:
                print(f"Failed to send email to {attendee}: {email_result['message']}")

        return JSONResponse(content={
            "status": "success",
            "meeting_link": meeting_link,
            "message": "Meeting confirmed and invites sent."
        })

    except Exception as e:
        print(f"Error in confirm_meeting: {str(e)}")
        raise HTTPException(status_code=500, detail="Error confirming meeting")


class EmailRequest(BaseModel):
    email: str
# await axios.post(`${backendUrl}/set_sender_email`, { email: userEmail });
@app.post("/set_sender_email")
async def set_sender_email(request: EmailRequest):
    if request.email != "osanzas1997@gmail.com":
        return JSONResponse(
            content={
                "status": "error",
                "message": "Please enter my creator's email address."
            }
        )
    return JSONResponse(
        content={
            "status": "success",
            "message": "Sender email set successfully"
        }
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
