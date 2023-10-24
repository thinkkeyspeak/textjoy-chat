import streamlit as st
import requests
import string
import random
import json

BASE_URL = st.secrets["base_url"]


def run(conversation_sid):
    if conversation_sid:
        all_messages, user_id = get_conversation(conversation_sid)
        filtered_messages = [
            message for message in all_messages 
            if message["role"] == "user" 
            or (message["role"] == "assistant" and not message["function_call"])
        ]
        st.session_state.messages = filtered_messages
        st.session_state.user_id = user_id
    else:
        st.session_state.messages = []

    if not st.session_state.get("user_id"):
        st.session_state.user_id = create_user_id()

    handle_chat_history()
    handle_user_input(prompt=st.chat_input("I'd like a ..."), conversation_sid=conversation_sid)


def create_user_id():
    return "webuser-" + generate_random_string(12)


def handle_chat_history():
    for message in st.session_state.messages:
        avatars = {
            "assistant": "static/logo-icon-yellow.jpg",
            "function": "🛠️",
            "system": "⚙️"
        }

        with st.chat_message(name=message["role"], avatar=avatars.get(message["role"])):
            if dev_mode:
                manage_message_in_dev_mode(message)
            else:
                st.markdown(message["content"])


def manage_message_in_dev_mode(message):
    
    message["content"] = st.text_input(
        label="Content", 
        value=message.get("content", ""), 
        key=f"content_{message['id']}",
        label_visibility="collapsed"
    )

    if message.get("function_call"):
        message["function_call"] = st.text_input(
            label="Function Call",
            value=message.get("function_call", ""), 
            key=f"function_call_{message['id']}"
        )

    if message.get("name"):
        message["name"] = st.text_input(
            label="Function Name", 
            value=message.get("name", ""), 
            key=f"name_{message['id']}"
        )


def handle_user_input(prompt, conversation_sid):
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message(name="assistant"):
            with st.spinner("Thinking..."):
                reply, conversation_sid = call_web_handler(
                    account_id, 
                    st.session_state.user_id, 
                    prompt, 
                    conversation_sid
                )
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.conversation_sid = conversation_sid


def call_web_handler(account_id, user_id, prompt, conversation_sid=None):
    response = requests.post(
        f"{BASE_URL}/conversation/webhook/web", 
        json={
            'account_id': account_id,
            'user_id': user_id,
            'prompt': prompt,
            'conversation_sid': conversation_sid
        }
    )
    data = response.json()
    return data.get('reply'), data.get('conversation_sid')


def generate_random_string(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_conversation(conversation_sid):
    response = requests.get(f"{BASE_URL}/conversation/{conversation_sid}/messages")
    data = response.json()
    return data.get('chat_history'), data.get('user_id')

def get_selectable_messages(messages):
    """Convert messages to a format suitable for multi-select."""
    return [msg["content"] for msg in messages]

def filter_selected_messages(messages, selected_messages_content):
    """Filter messages based on selected content."""
    return [msg for msg in messages if msg["content"] in selected_messages_content]

# Initialization and configuration
query_params = st.experimental_get_query_params()
account_id = query_params.get("account_id", [None])[0]
conversation_sid = query_params.get("conversation_sid", [None])[0]
dev_mode = query_params.get("dev_mode", [None])[0]

st.set_page_config(
    page_title="TextJoy Chat",
    page_icon="static/favicon-transparent.ico"
)
st.session_state.messages, st.session_state.user_id = get_conversation(conversation_sid)
st.title("Start an order")

if not st.session_state.get("selected_messages"):
    st.session_state.selected_messages = []

if dev_mode:

    # Create sidebar
    st.sidebar.title("Developer Mode")

    # Using multi-select for message selection
    selectable_messages = get_selectable_messages(st.session_state.messages)
    selected_messages_content = st.sidebar.multiselect(
        "Select Messages", selectable_messages, default=[]
    )

    # Show count of selected messages
    st.sidebar.header(f"Selected messages ({len(selected_messages_content)})")

    # Offer download for selected messages
    if selected_messages_content:
        selected_msgs = filter_selected_messages(st.session_state.messages, selected_messages_content)
        st.sidebar.download_button(
            label="Download JSONL",
            data=json.dumps(selected_msgs),
            file_name="selected_messages.jsonl",
            mime="application/jsonl"
        )

# App execution
if __name__ == "__main__":
    run(conversation_sid)
