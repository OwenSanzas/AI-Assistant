from typing import Dict, Optional
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain.schema.output_parser import StrOutputParser
import json
import os


class PrivacyManager:
    def __init__(self):
        if os.getenv("ENV") == "prod":
            self.llm = ChatAnthropic(
                model='claude-3-5-sonnet-20240620',
                temperature=0,
                max_tokens=8192,
                max_retries=2
            )

        else:
            self.llm = Ollama(model="llama3.1:8b", temperature=0)

        self.contacts = self._load_contacts()
        self.personal_info = self._load_personal_info()

    def _load_contacts(self) -> Dict[str, str]:
        try:
            with open("private/contacts.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            contacts = {
                "Jeff": "jeff@tamu.edu",
            }
            self._save_contacts(contacts)
            return contacts

    def _load_personal_info(self) -> Dict[str, str]:
        try:
            with open("private/personal_info.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            personal_info = {
                "name": "Ze Sheng",
                "email": "osanzas1997@gmail.com",
                "signature": "Best regards,\nZe Sheng"
            }
            self._save_personal_info(personal_info)
            return personal_info

    def _save_contacts(self, contacts: Dict[str, str]):
        os.makedirs("private", exist_ok=True)
        with open("private/contacts.json", "w") as f:
            json.dump(contacts, f, indent=2)

    def _save_personal_info(self, info: Dict[str, str]):
        os.makedirs("private", exist_ok=True)
        with open("private/personal_info.json", "w") as f:
            json.dump(info, f, indent=2)

    async def get_email_address(self, name: str) -> Optional[str]:
        while True:
            prompt = ChatPromptTemplate.from_template("""
            Based on this contact name: {name}
            And this contacts database: {contacts}
    
            If the name matches (including partial matches or nicknames) anyone in the contacts,
            return ONLY their email address.
            If no match is found, return "UNKNOWN".
    
            Format your response as just the email address or "UNKNOWN", nothing else.
            
            No code block should be included in the response.
            """)

            chain = (
                    prompt
                    | self.llm
                    | StrOutputParser()
            )

            result = await chain.ainvoke({
                "name": name,
                "contacts": json.dumps(self.contacts)
            })

            if len(result) > 50:
                continue

            break

        print("results", result)

        return result.strip() if result.strip() != "UNKNOWN" else None

    def get_sender_email(self) -> str:
        return self.personal_info["email"]

    def get_signature(self) -> str:
        return self.personal_info["signature"]

    def get_sender_name(self) -> str:
        return self.personal_info["name"]

    async def add_contact(self, name: str, email: str):
        self.contacts[name] = email
        self._save_contacts(self.contacts)
