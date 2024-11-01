import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Dict


class EmailSender:
    def __init__(self):
        self.email = os.getenv("EMAIL_ADDRESS")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    async def send_email(self, email_data: Dict) -> Dict:
        try:
            msg = MIMEMultipart()
            msg['From'] = email_data['sender']
            msg['To'] = email_data['recipient']
            msg['Subject'] = email_data['subject']

            msg.attach(MIMEText(email_data['content'], 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)

            return {
                "success": True,
                "message": "Email sent successfully"
            }
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}"
            }
