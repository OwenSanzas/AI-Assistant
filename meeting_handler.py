from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pickle
import os
from typing import Dict
import json
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain.schema.output_parser import StrOutputParser
from privacy_agent import PrivacyManager

privacy_manager = PrivacyManager()


class MeetingHandler:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        self.creds = self.get_credentials()
        self.service = build('calendar', 'v3', credentials=self.creds)

    def get_credentials(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return creds

    async def create_meeting(self, meeting_data: Dict) -> Dict:
        try:
            event = {
                'summary': meeting_data['title'],
                'description': meeting_data['description'],
                'start': {
                    'dateTime': meeting_data['start_time'],
                    'timeZone': 'America/Chicago',
                },
                'end': {
                    'dateTime': meeting_data['end_time'],
                    'timeZone': 'America/Chicago',
                },
                'attendees': [{'email': email} for email in meeting_data['attendees']],
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                }
            }

            event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1
            ).execute()

            return {
                "success": True,
                "meeting_link": event.get('hangoutLink'),
                "event_id": event['id']
            }

        except Exception as e:
            print(f"Error creating meeting: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


meeting_handler = MeetingHandler()


async def handle_schedule_meeting(user_input: str):
    try:
        current_date = datetime.now().strftime('%Y-%m-%d')

        prompt_template = ChatPromptTemplate.from_template("""
        Based on this user request: "{input}"
        
        today: {current_date}

        Extract meeting details or assume defaults as follows:
        - title: "Meeting with [contact_name]" if not specified
        - description: "Add your description" if not specified
        - duration_minutes: 45 if not specified
        - suggested_time: today + 7 days at 9:00 AM
        - attendees_name: "<contact_name>, <contact_name2>"

        Return the result in JSON format:
        {{
            "title": "<meeting title>",
            "description": "<meeting description>",
            "attendees_name": "<contact_name>",
            "duration_minutes": <duration in minutes>,
            "suggested_time": "<YYYY-MM-DDTHH:MM:SS>"
        }}
        
        Make sure you extract the contact name (attendee) correctly.

        ONLY return the JSON object, no explanations, no code block.
        """)

        prompt_template_refine = ChatPromptTemplate.from_template("""
        Based on this user request: "{input}"
        
        And raw data processed as follows:
        {result}
        
        current date: {current_date}
        
        Refine the meeting details as follows:
        
        1. If no title is provided, use your knowledge to set a title.
        2. If no description is provided, set it to some project meeting content.
        3. If no duration is provided, set it to 45 minutes.
        4. Calculate the date carefully, ignore holidays and weekends. i.e. tomorrow = current date + 1 day.
        5. If no time is provided, set it to 9:00 AM.
        6. If you are still not sure, set a proper future date and time.
        7. Make sure you extract the contact name (attendee) correctly, it should be names but not explanation or code blocks.
        
        if 
        
        
        Make sure the time is correct calculated from the current date. If no exact time is provided, set to 9:00 AM.
        
        current date: {current_date}
        
        You are my assistant, so you should set date and time if I don't give you one. IGNORE the holidays and weekends.
        
        {{
            "title": "<meeting title>",
            "description": "<meeting description>",
            "attendees_name": "<contact_name>",
            "duration_minutes": <duration in minutes>,
            "suggested_time": "<YYYY-MM-DDTHH:MM:SS>"
        }}
        
        Return the result in JSON format. Make sure you json is structured correctly.
        
        ONLY return the JSON object, no explanations or code block.
        
        """)

        claude = ChatAnthropic(
            model='claude-3-5-sonnet-20240620',
            temperature=0,
            max_tokens=8192,
            max_retries=2
        )

        meeting_chain = prompt_template | claude | StrOutputParser()
        result = await meeting_chain.ainvoke({"input": user_input, "current_date": current_date})

        meeting_chain_refine = prompt_template_refine | claude | StrOutputParser()
        result = await meeting_chain_refine.ainvoke({"input": user_input, "result": result, "current_date": current_date})

        parsed_result = json.loads(result)
        contact_name = parsed_result["attendees_name"]

        print("contact name:", contact_name)

        start_time = datetime.fromisoformat(parsed_result["suggested_time"])

        attendee_email = await privacy_manager.get_email_address(contact_name)

        if attendee_email:
            attendee_email = attendee_email.replace('"', '')
            attendees = [privacy_manager.get_sender_email(), attendee_email]
        else:
            attendees = [privacy_manager.get_sender_email(), "unknown@email.com"]

        title = parsed_result.get("title", f"Meeting with {contact_name}")
        description = parsed_result.get("description", "Add your description")
        duration_minutes = parsed_result.get("duration_minutes", 45)
        end_time = start_time + timedelta(minutes=duration_minutes)

        meeting_data = {
            "type": "meeting_scheduled",
            "data": {
                "title": title,
                "time": start_time.strftime("%Y-%m-%d %H:%M"),
                "duration": f"{duration_minutes} minutes",
                "attendees": attendees,
                "description": description,
            }
        }

        print("formatted meeting data:", meeting_data)

        return meeting_data



    except Exception as e:
        print(f"Error in handle_schedule_meeting: {str(e)}")
        return {
            "type": "error",
            "message": "Failed to process meeting request. Please try again."
        }
