from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


def identify_intent(user_input, history):
    prompt = f"""
    You are an AI assistant with several functions:
    - "send_email": Write and send an email.
    - "schedule_meeting": Schedule a meeting.
    - "internet_search": Search the internet for information.
    
    Here is the history of the conversation:
    {history}
    
    
    Here is the user input: \n{user_input}\n.
    
    
    Please output the function name that best matches the user input.
    
    Think like this:
    1. Whether the user want to send an email? output "send_email" if yes.
    2. Whether the user want to schedule a meeting? output "schedule_meeting" if yes.
    3. Whether the user want to know somthing that you don't know from the history and you want to search the internet? output "internet_search" if yes.
    3. Else, output "None".
    
    if you are not sure, output "None".
    
    No explanation is needed. Just output the function name.
    """

    gpt_4o = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        max_tokens=16384,
        max_retries=2
    )

    gpt_4o_chain = gpt_4o | StrOutputParser()

    intent = gpt_4o_chain.invoke(prompt)

    print("Intent identified:", intent)

    if "send_email" in intent:
        return "send_email"
    elif "schedule_meeting" in intent:
        return "schedule_meeting"
    elif "internet_search" in intent:
        return "internet_search"
    else:
        return "normal_chat"
