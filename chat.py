import streamlit as st
import requests
import string
import random
import json

BASE_URL = st.secrets["base_url"]


def run(conversation_sid):
    if conversation_sid:
        messages, user_id = get_conversation(conversation_sid)
        st.session_state.messages = messages
        st.session_state.user_id = user_id
    else:
        st.session_state.messages = []

    if not st.session_state.get("user_id"):
        st.session_state.user_id = create_user_id()

    show_chat_history()
    handle_user_input(prompt=st.chat_input("I'd like a ..."), conversation_sid=conversation_sid)


def show_chat_history():
    if not dev_mode:
        st.session_state.messages = [
            message for message in st.session_state.messages
            if message["role"] == "user" 
            or (message["role"] == "assistant" and not message["function_call"])
        ]

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

    # Capture edited content
    edited_content = st.text_input(
        label="Content", 
        value=message.get("content", ""), 
        key=f"content_{message['id']}",
        label_visibility="collapsed"
    )

    # If edited content differs from stored content, update it
    if edited_content != message["content"]:
        message["content"] = edited_content
        update_session_message(message['id'], 'content', edited_content)

    if message.get("function_call"):
        edited_function_call = st.text_input(
            label="Function Call",
            value=message.get("function_call", ""), 
            key=f"function_call_{message['id']}"
        )
        if edited_function_call != message["function_call"]:
            message["function_call"] = edited_function_call
            update_session_message(message['id'], 'function_call', edited_function_call)

    if message.get("name"):
        edited_name = st.text_input(
            label="Function Name", 
            value=message.get("name", ""), 
            key=f"name_{message['id']}"
        )
        if edited_name != message["name"]:
            message["name"] = edited_name
            update_session_message(message['id'], 'name', edited_name)


def update_session_message(message_id, key, value):
    """Update a specific message in session state by its ID."""
    for msg in st.session_state.messages:
        if msg['id'] == message_id:
            msg[key] = value
            break


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


def create_user_id():
    return "webuser-" + generate_random_string(12)


def generate_random_string(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_conversation(conversation_sid):
    response = requests.get(f"{BASE_URL}/conversation/{conversation_sid}/messages")
    data = response.json()
    return data.get('chat_history'), data.get('user_id')


def format_multiselect_options(messages):
    """Convert messages to multiselect options."""
    return[(msg["id"], msg["content"])for msg in messages]


def format_messages_for_download(selected_options):
    """Convert selected options to JSONL format."""
    selected_ids = [option[0] for option in selected_options]
    messages = [msg for msg in st.session_state.messages if msg["id"] in selected_ids]

    # for each message, return the role and content. If it has a name or function call, include those too
    formatted_messages = []
    for msg in messages:
        formatted_msg = {
            "role": msg["role"],
            "content": msg["content"],
        }
        if msg.get("name"):
            formatted_msg["name"] = msg["name"]
        if msg.get("function_call"):
            formatted_msg["function_call"] = msg["function_call"]
        formatted_messages.append(formatted_msg)
    
    jsonl = {"messages": formatted_messages}
    return jsonl


# INITIALIZE AND CONFIGURE APP

# Get query parameters
query_params = st.experimental_get_query_params()
account_id = query_params.get("account_id", [None])[0]
conversation_sid = query_params.get("conversation_sid", [None])[0]
dev_mode = query_params.get("dev_mode", [None])[0]

st.set_page_config(
    page_title="TextJoy Chat",
    page_icon="static/favicon-transparent.ico"
)
st.session_state.messages, st.session_state.user_id = get_conversation(conversation_sid)
st.session_state.selected_messages = []

st.title("Start an order")

# Create sidebar if dev_mode is enabled
if dev_mode:

    st.sidebar.title("Developer Mode")

    # Using multi-select for message selection
    options = format_multiselect_options(st.session_state.messages)
    selected_options = st.sidebar.multiselect(
        "Select Messages", options, format_func=lambda o: o[1]
    )
    print(selected_options)

    # Show count of selected messages
    st.sidebar.header(f"Selected messages ({len(selected_options)})")

    # Offer download for selected messages
    if selected_options:
        jsonl = format_messages_for_download(selected_options)
        st.sidebar.download_button(
            label="Download JSONL",
            data=json.dumps(jsonl),
            file_name=f"{conversation_sid}.jsonl",
            mime="application/jsonl"
        )

# RUN APP
if __name__ == "__main__":
    run(conversation_sid)
