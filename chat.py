import streamlit as st
import requests, string, random

def create_user_id():
    ''' Create fake number and conversation sid '''
    user_id = "webuser-" + generate_random_string(12)
    return user_id

def call_web_handler(account_id, user_id, prompt, conversation_sid=None):
    base_url = "https://25b9-76-209-99-94.ngrok-free.app"
    path = base_url + "/conversation/webhook/web"

    payload = {
        'account_id': account_id,
        'user_id': user_id,
        'prompt': prompt,
        'conversation_sid': conversation_sid
    }

    # Make the POST request
    response = requests.post(path, json=payload)
    data = response.json()
    reply = data.get('reply')
    conversation_sid = data.get('conversation_sid')
    
    return reply, conversation_sid


def generate_random_string(length=12):
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choice(characters) for _ in range(length))


# LOAD CHAT CONTENTS

# Get account_id from URL query parameters
query_params = st.experimental_get_query_params()
account_id = query_params.get("account_id", [None])[0]
conversation_sid = query_params.get("conversation_sid", [None])[0]

# Set page title
st.title("Start an order")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.user_id = create_user_id()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("I'd like a ..."):

    # Add user message to chat history
    with st.chat_message("user"):
        st.markdown(prompt)

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown("...")
        reply, conversation_sid = call_web_handler(account_id, st.session_state.user_id, prompt, conversation_sid)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.conversation_sid = conversation_sid
