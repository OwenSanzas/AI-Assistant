import os
import uvicorn

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pdf_reader import PDFQuestionAnswering
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许访问的前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# load agents
pdf_qa = PDFQuestionAnswering(use_claude=True)
UPLOAD_DIRECTORY = "./uploaded_pdfs"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


@app.post("/upload_pdf")
async def upload_pdf(files: list[UploadFile] = File(...), question: str = Form(...)):
    pdf_paths = []

    print("a file has been uploaded")

    question_base = f"\nGiven are {len(files)} texts of PDFs. Please answer the question by reading the text from the PDFs.\n"

    question = question_base + question

    question += "\nNo explanation is needed. Just answer the question.\n"

    for file in files:
        file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        pdf_paths.append(file_path)

    answer = pdf_qa.answer_question(pdf_paths, question)

    print ("answer: ", answer)
    return JSONResponse(content={"message": answer})


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
