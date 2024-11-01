from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


async def default_chat(user_input, history):
    # 创建 ChatOpenAI 实例和链
    gpt_4o = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        max_tokens=16384,
        max_retries=2
    )
    gpt_4o_chain = gpt_4o | StrOutputParser()

    messages = "\n".join([f"{msg['sender']}: {msg['text']}" for msg in history])
    messages += f"\nUser: {user_input}"

    response = gpt_4o_chain.invoke(messages)

    print(history, user_input)
    return response
