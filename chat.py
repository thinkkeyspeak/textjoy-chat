import streamlit as st
import requests
import string
import random
import json

# Configure App
BASE_URL = st.secrets["base_url"]

st.set_page_config(
    page_title="TextJoy Chat",
    page_icon="static/favicon-transparent.ico"
)

def run():
    """This is the main function. It runs everytime a user interacts with widgets in the app"""

    # Get query parameters
    query_params = st.experimental_get_query_params()
    st.session_state.account_id = query_params.get("account", [None])[0]
    conversation_sid = query_params.get("conversation", [None])[0]

    if conversation_sid:
        st.session_state.conversation_sid = conversation_sid

    if st.session_state.get('conversation_sid'):
        st.session_state.messages, st.session_state.user_id = get_conversation(st.session_state.conversation_sid)
    else:
        st.session_state.conversation_sid = None
        st.session_state.messages = []
        st.session_state.user_id = generate_phone_number()

    if not st.session_state.account_id:
        st.error("No account ID provided. Please add ?account=YOUR_ACCOUNT_ID to the URL.")
        return

    st.session_state.dev_mode = st.toggle("Dev Mode")
    st.title("Start an order")

    show_chat_history()
    handle_user_input(st.chat_input("I'd like a ..."), st.session_state.conversation_sid, st.session_state.account_id)
    
    # Setup sidebar
    if st.session_state.dev_mode:
        setup_sidebar()

def setup_sidebar():
    if st.session_state.dev_mode:

        # Show conversation and user ID
        st.sidebar.markdown(f'<a href="{BASE_URL}/conversations" target="_self">Conversations /</a>', unsafe_allow_html=True)
        st.sidebar.header(st.session_state.conversation_sid)

        st.sidebar.header("User ID")
        st.sidebar.write(st.session_state.user_id)

        st.sidebar.download_button(
            label="Download Conversation",
            data =json.dumps(format_messages_for_download(st.session_state.messages)),
            file_name=f"{st.session_state.conversation_sid}.jsonl",
            mime="application/jsonl",
            type="primary"
        )

        if st.sidebar.button("Delete Conversation", type="secondary"):
            delete_conversation()
            st.markdown(f'<meta http-equiv="refresh" content="0; URL={BASE_URL}/conversations">', unsafe_allow_html=True)
        

def show_chat_history():

    if not st.session_state.dev_mode:
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
            if st.session_state.dev_mode:
                msg = format_message(message)
                st.write(msg)
            else:
                st.write(message["content"])
        

def handle_user_input(prompt, conversation_sid, account_id):
    if prompt:
        with st.chat_message("user"):
            st.write(prompt)

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message(name="assistant"):
            with st.spinner("Thinking..."):
                reply, conversation_sid = call_web_handler(
                    account_id, 
                    st.session_state.user_id, 
                    prompt, 
                    conversation_sid
                )
            st.write(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.experimental_set_query_params(
            account=account_id,
            conversation=conversation_sid,
            dev_mode=st.session_state.dev_mode
        )


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


def generate_phone_number():
    """Generate a random phone number. Must start with +1313 and include 7 digits after"""
    # The first number of the area code and the exchange code cannot be 0 or 1.
    area_code = 313
    exchange_code = random.randint(200, 999)
    subscriber_number = random.randint(0, 9999)

    # Format the phone number to the desired format (XXX) XXX-XXXX.
    phone_number = f"+1{area_code}{exchange_code}{subscriber_number:04d}"
    return phone_number


def get_conversation(conversation_sid):
    response = requests.get(f"{BASE_URL}/conversation/{conversation_sid}/messages")
    data = response.json()
    return data.get('chat_history'), data.get('user_id')


def format_message(message):
    """Format a message to only include fields that can be ingested for training."""
    formatted_msg = {
            "role": message["role"],
        }
    if message.get("name"):
        formatted_msg["name"] = message["name"]
    if message.get("content"):
        formatted_msg["content"] = message["content"]
    if message.get("function_call"):
        formatted_msg["function_call"] = message["function_call"]

    return formatted_msg


def format_messages_for_download(messages: list):
    """Convert selected options to JSONL format."""
    
    formatted_messages = []
    for msg in messages:
        formatted_msg = format_message(msg)
        formatted_messages.append(formatted_msg)
    
    jsonl = {"messages": formatted_messages}
    return jsonl


def delete_conversation():
    """Delete the current conversation."""
    requests.delete(f"{BASE_URL}/conversation/{st.session_state.conversation_sid}/delete")

# RUN APP
if __name__ == "__main__":
    run()