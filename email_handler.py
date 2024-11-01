import os
from typing import Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from pydantic import BaseModel
import openai

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


class EmailContent(BaseModel):
    sender: str
    recipient: str
    subject: str
    content: str


def generate_email_content(user_input: str) -> Dict[str, str]:
    """使用LLM生成邮件内容"""
    prompt = f"""Based on the following user request, generate an email with appropriate subject, content, and determine the recipient.
    User request: {user_input}

    Please format your response as a clear email with:
    - A clear subject line
    - Professional greeting
    - Well-structured content
    - Appropriate closing

    Response should be natural and contextually appropriate."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant helping to draft professional emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # 解析LLM的回复，提取邮件组件
        generated_content = response.choices[0].message.content

        # 基本的邮件结构解析（你可能需要根据实际的LLM输出格式调整这个解析逻辑）
        subject = generated_content.split("\n")[0].replace("Subject:", "").strip()
        content = "\n".join(generated_content.split("\n")[1:])

        return {
            "subject": subject,
            "content": content
        }
    except Exception as e:
        print(f"Error generating email content: {str(e)}")
        return {
            "subject": "Re: Your Request",
            "content": "I apologize, but I encountered an error while generating the email content."
        }


def send_email(email_data: EmailContent) -> Dict[str, str]:
    """发送邮件并返回结果"""
    try:
        msg = MIMEMultipart()
        msg['From'] = email_data.sender
        msg['To'] = email_data.recipient
        msg['Subject'] = email_data.subject

        msg.attach(MIMEText(email_data.content, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}


async def process_email_request(user_input: str) -> Dict[str, str]:
    """处理邮件请求的主函数"""
    try:
        # 生成邮件内容
        generated_email = generate_email_content(user_input)

        # 创建邮件数据对象
        email_data = EmailContent(
            sender=SMTP_USERNAME,
            recipient="recipient@example.com",  # 这里可以从LLM结果或用户输入中获取
            subject=generated_email["subject"],
            content=generated_email["content"]
        )

        # 返回生成的邮件预览
        return {
            "status": "preview",
            "email_data": {
                "sender": email_data.sender,
                "recipient": email_data.recipient,
                "subject": email_data.subject,
                "content": email_data.content
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"Error processing email request: {str(e)}"}