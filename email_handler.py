import os

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain.schema.output_parser import StrOutputParser
import json
from privacy_agent import PrivacyManager

privacy_manager = PrivacyManager()


async def handle_send_email(user_input: str):
    try:
        prompt_template = ChatPromptTemplate.from_template("""Extract email information from this request: "{input}"

        If there's an email address in quotes or otherwise clearly specified in the request, use that exact email.
        If there's just a name, extract that name as recipient_name.

        Create a professional email with appropriate subject and content.

        Return the result as a valid JSON object with the following format:
        {{
            "recipient_email": "<exact email if provided in the request, otherwise null>",
            "recipient_name": "<recipient name if no email provided>",
            "subject": "<appropriate subject line>",
            "content": "<email content without any closing phrase>"
        }}

        For example:
        For input "send an email to 'john@example.com' about project"
        The response should be like:
        {{
            "recipient_email": "john@example.com",
            "recipient_name": null,
            "subject": "Project Discussion",
            "content": "Dear colleague..."
        }}

        For input "send an email to John about project"
        The response should be like:
        {{
            "recipient_email": null,
            "recipient_name": "John",
            "subject": "Project Discussion",
            "content": "Dear John..."
        }}

        The email should be professional and appropriate for the context.
        Do not include any closing phrases or signatures.
        Just return the JSON object, No explanation needed.
        """)

        llama = privacy_manager.llm

        prompt_template_format = ChatPromptTemplate.from_template("""Extract email information from this request: "{input}"
        
        This is user's request of the email content. The email should be professional and appropriate for the context.
        
        // user_input "{user_input}"
        
        Return the result STRICTLY as a valid JSON object with the following format:
        {{
            "recipient_email": "<exact email if provided in the request, otherwise null>",
            "recipient_name": "<recipient name if no email provided>",
            "subject": "<appropriate subject line>",
            "content": "<email content without any closing phrase>"
        }}
        
        No explanation needed.
        """)

        claude = ChatAnthropic(
            model='claude-3-5-sonnet-20240620',
            temperature=0,
            max_tokens=8192,
            max_retries=2
        )

        email_chain = prompt_template | claude | StrOutputParser()
        email_format_chain = prompt_template_format | claude | StrOutputParser()

        result = email_chain.invoke({
            "input": user_input
        })

        result = email_format_chain.invoke({
            "input": result,
            "user_input": user_input
        })

        parsed_result = json.loads(result)

        if parsed_result.get("recipient_email"):
            recipient_email = parsed_result["recipient_email"]
            recipient_name = "Recipient"
        else:
            recipient_name = parsed_result["recipient_name"]
            recipient_email = await privacy_manager.get_email_address(recipient_name)
            if not recipient_email:
                return {
                    "type": "error",
                    "message": f"Couldn't find email address for {recipient_name}"
                }

        full_content = f"{parsed_result['content'].rstrip()}\n\n{privacy_manager.get_signature()}"

        email_data = {
            "type": "email_preview",
            "data": {
                "sender": f"{privacy_manager.get_sender_name()} <{privacy_manager.get_sender_email()}>",
                "recipient": f"{recipient_name} <{recipient_email}>",
                "subject": parsed_result["subject"],
                "content": full_content
            }
        }

        return email_data

    except Exception as e:
        print(f"Error in handle_send_email: {str(e)}")
        return {
            "type": "error",
            "message": "Failed to process email request. Please try again with a clearer instruction."
        }