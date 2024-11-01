import openai
import fitz  # PyMuPDF

from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


class PDFQuestionAnswering:
    def __init__(self, model_name="gpt-4o", use_claude=False):
        self.use_claude = use_claude

        if self.use_claude:
            self.model = ChatAnthropic(
                model='claude-3-5-sonnet-20240620',
                temperature=0,
                max_tokens=8192,
                max_retries=2
            )
        else:
            self.model = ChatOpenAI(
                model=model_name,
                temperature=0,
                max_tokens=16384,
                max_retries=2
            )

        self.chain = self.model | StrOutputParser()

    def extract_and_label_texts(self, pdf_paths):
        labeled_text = ""
        for idx, pdf_path in enumerate(pdf_paths, start=1):
            doc = fitz.open(pdf_path)
            text = f"// pdf {idx}:\n"
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += page.get_text()
            labeled_text += text + "\n\n"
            doc.close()
        return labeled_text

    def answer_question(self, pdf_paths, question):
        pdf_text = self.extract_and_label_texts(pdf_paths)
        prompt = f"""
        Given the following text, answer the question:

        {pdf_text}

        Question: {question}
        """
        answer = self.chain.invoke(prompt)
        return answer  # 返回答案和PDF文本


if __name__ == "__main__":
    pdf_qa = PDFQuestionAnswering(use_claude=True)

    pdf_path = ["test1.pdf", "test2.pdf"]
    pdf_num = len(pdf_path)

    question = f"\nGiven are {pdf_num} PDFs. Please answer the question by reading the text from the PDFs.\n"
    question += "Summarize the main areas of the PDFs."
    question += "\nNo explanation is needed. Just answerthe question.\n"
    answer = pdf_qa.answer_question(pdf_path, question)
    print("Answer:", answer)
