import datetime
from dotenv import load_dotenv
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import BingSearchAPIWrapper
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic


load_dotenv()

os.environ["BING_SEARCH_URL"] = "https://api.bing.microsoft.com/v7.0/search"


async def handle_internet_search(user_input, history):
    gpt_4o = ChatOpenAI(model="gpt-4o", temperature=0, max_tokens=16384, max_retries=2)
    chain = gpt_4o | StrOutputParser()

    claude = ChatAnthropic(model='claude-3-5-sonnet-20240620', temperature=0, max_tokens=8192, max_retries=2)
    claude_chain = claude | StrOutputParser()

    prompt = f"""
    Given is the history of the conversation and a user input which is asking for information.
    
    If this user input is asking for existing information in the history, ONLY output "normal chat" in plain text.
    
    If this user input is asking for some information which is not in the history, and you need to search the web, output "web search" in plain text.
    
    ONLY output the text, no explanation.
    
    // History:
    {history}
    
    // User input:
    {user_input}
    
    """

    response = claude_chain.invoke(prompt)

    if "normal chat" in response:
        return "normal chat"


    bing_search = BingSearchAPIWrapper(k=5)  # 获取 5 个结果

    today = datetime.datetime.today().strftime("%Y-%m-%d")

    prompt = f"""
    You are an AI assistant with web search capabilities.

    Given is a user input which is asking for information.

    You need to reformat the input into a query. Only output the query with no explanation.

    Today's date is: {today}, use this information ONLY for TODAY's QUERY, FOR future query, do not add it.

    // user input:
    """

    query = chain.invoke(prompt + user_input)

    print("Today's date is:", today)

    results = bing_search.results(query, 5)
    response_text = "\n".join([f"{res['title']}: {res['link']}\nSnippet: {res['snippet']}" for res in results])

    prompt = f"""
        You are an AI assistant with web search capabilities.

        Given is a search results.

        You need to reformat the results into a readable format based on user's requirement. 

        Today's date is: {today}, use this information ONLY for TODAY's QUERY, FOR future query, do not use it.
        
        IF you cannot find any information, output "No information found".
        
        Requirement: {user_input}
        
        Formatted Query: {query}

        // Search Results:
        
    """

    response_text = chain.invoke(prompt + response_text)

    return response_text
