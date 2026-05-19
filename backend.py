from langgraph.graph import StateGraph, START,END
from typing import TypedDict,Annotated
from langchain_google_genai import GoogleGenerativeAI, ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field 
from langchain_protocol import Literal
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import sqlite3



load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)


class ChatState(TypedDict):
    messages:Annotated[list[BaseMessage], add_messages]


def chat_node(state:ChatState):
    messages = state['messages']

    response = llm.invoke(messages)

    return {'messages':[response]}


#-----Checkpoint and Database Setup --------
conn = sqlite3.connect(database='chatbot.db', check_same_thread = False)

checkpointer = SqliteSaver(conn=conn)



graph = StateGraph(ChatState)

graph.add_node('chat_node',chat_node)
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)


conn.execute("""
    CREATE TABLE IF NOT EXISTS thread_titles (
        thread_id TEXT PRIMARY KEY, 
        title TEXT
    )
""")
conn.commit()


def save_thread_title(thread_id, title):
    conn.execute(
        "INSERT OR REPLACE INTO thread_titles (thread_id, title) VALUES (?, ?)",
        (str(thread_id), title)
    )
    conn.commit()

def get_all_thread_titles():
    cursor = conn.execute("SELECT thread_id, title FROM thread_titles")
    return {row[0]: row[1] for row in cursor.fetchall()}


