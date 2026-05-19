import streamlit as st
from backend import (
    chatbot, llm, retrieve_all_threads,
    get_all_thread_titles, save_thread_title
)
from langchain_core.messages import HumanMessage
import uuid


# CUSTOM CSS

def inject_custom_css():
    st.markdown("""
    <style>
        .chat-row { display: flex; margin: 0 auto 24px auto; width: 100%; max-width: 800px; }
        .row-user { justify-content: flex-end; }
        .row-bot { justify-content: flex-start; }
        .chat-bubble { font-family: sans-serif; line-height: 1.6; font-size: 16px; }
        .bubble-user { background-color: #f4f4f4; color: #0d0d0d; padding: 10px 20px; border-radius: 24px; max-width: 75%; }
        .bubble-bot { background-color: transparent; color: inherit; padding: 4px 0px; max-width: 100%; width: 100%; }
        [data-testid="stSidebar"] .stButton > button {
            width: 100% !important; text-align: left !important; justify-content: flex-start !important;
            background-color: transparent !important; border: none !important; padding: 10px 15px !important;
            border-radius: 8px !important; transition: background 0.2s;
        }
        [data-testid="stSidebar"] .stButton > button:hover { background-color: #f0f0f0; }
        [data-testid="stSidebar"] .stButton > button p {
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

def render_chat_bubble(text, role):
    is_user = (role == 'user')
    html = f"""<div class="chat-row {'row-user' if is_user else 'row-bot'}">
               <div class="chat-bubble {'bubble-user' if is_user else 'bubble-bot'}">{text}</div></div>"""
    st.markdown(html, unsafe_allow_html=True)

inject_custom_css()


# UTILITY FUNCTIONS

def generate_thread_id(): return str(uuid.uuid4())

def add_thread(thread_id):
    thread_id = str(thread_id)
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)
        st.session_state['title_chats'][thread_id] = 'New Chat'

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(thread_id)
    st.session_state['message_history'] = []

def generate_chat_title_llm(first_message, llm):
    return llm.invoke(f"Summarise this query into 6-8 words title. No quotes or punctuation. Query: {first_message}").content.strip()

def load_chat(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': str(thread_id)}})
    return state.values.get('messages', [])


# SESSION SETUP

if 'message_history' not in st.session_state: st.session_state.message_history = []
if 'thread_id' not in st.session_state: st.session_state['thread_id'] = generate_thread_id()
if 'chat_threads' not in st.session_state: st.session_state['chat_threads'] = retrieve_all_threads()
if 'title_chats' not in st.session_state: st.session_state['title_chats'] = get_all_thread_titles()

add_thread(st.session_state['thread_id'])


# SIDEBAR UI

st.sidebar.title('ChatDKT')
if st.sidebar.button('➕ New Chat', use_container_width=True):
    reset_chat()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header('My Chats')

unique_threads = list(dict.fromkeys([str(t) for t in st.session_state['chat_threads']]))[::-1]

for thread_id in unique_threads:
    title = st.session_state['title_chats'].get(thread_id, "New Chat")
    if st.sidebar.button(title, key=f"sidebar_{thread_id}", use_container_width=True):
        st.session_state['thread_id'] = thread_id
        messages = load_chat(thread_id)
        temp_messages = []
        for msg in messages:
            role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
            temp_messages.append({'role': role, 'content': msg.content})
        st.session_state['message_history'] = temp_messages
        st.rerun()


# CHAT DISPLAY

for message in st.session_state.message_history:
    render_chat_bubble(message['content'], message['role'])

user_input = st.chat_input('Type here...')

if user_input:
    current_tid = str(st.session_state['thread_id'])
    is_first_message = len(st.session_state.message_history) == 0 or st.session_state['title_chats'].get(current_tid) == "New Chat"

    st.session_state.message_history.append({'role': 'user', 'content': user_input})
    render_chat_bubble(user_input, 'user')

    CONFIG = {'configurable': {'thread_id': current_tid}}
    message_placeholder = st.empty()
    full_response = ""

    for message_chunk, metadata in chatbot.stream({'messages': [HumanMessage(content=user_input)]}, config=CONFIG, stream_mode='messages'):
        full_response += message_chunk.content
        message_placeholder.markdown(f'<div class="chat-row row-bot"><div class="chat-bubble bubble-bot">{full_response}▌</div></div>', unsafe_allow_html=True)

    message_placeholder.markdown(f'<div class="chat-row row-bot"><div class="chat-bubble bubble-bot">{full_response}</div></div>', unsafe_allow_html=True)

    st.session_state.message_history.append({'role': 'assistant', 'content': full_response})

    if is_first_message:
        new_title = generate_chat_title_llm(user_input, llm)
        save_thread_title(current_tid, new_title)
        st.session_state['title_chats'][current_tid] = new_title
        st.rerun()