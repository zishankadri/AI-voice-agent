from .myinst import INSTRUCTIONS

from .logger import get_logger
log = get_logger()

import uuid # Used to generate a unique session ID
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService # in-memory service that stores user data
from google.adk.runners  import Runner # connects the session and the agent together
from google.genai import types # tools to define user messages

from .agent_tools import *

from dotenv import load_dotenv

load_dotenv() # Loading our API keys


SESSION_ID  = str(uuid.uuid4()) #  Generates a unique session ID
USER_ID = "CUSTOMER"
APP_NAME = "voice_agent"



chef = Agent(
    name=APP_NAME,
    model="gemini-2.0-flash", # Use a suitable Gemini model
    instruction=(INSTRUCTIONS),
    tools=[
        get_menu,
        set_or_modify_items,
        set_address,
        confirm_order,
        set_table_booking,
        set_pick_up_branch,
        set_order_type,
        transfer_to_human,
        call_back,
    ]
)



service = InMemorySessionService() # A session backend that stores conversational state in memory

def get_or_create_agent_session(user_id: str, session_id: str, phone_number: str):
    """
    Returns an existing session if a session with the session_id already exists,
    otherwise creates a new session.
    """
    existing_session = service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if existing_session:
        print(f"Session with ID '{session_id}' already exists. Returning existing session.")

    if not existing_session:
        print(f"Session with ID '{session_id}' not found Creating a new session.")
        service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={
                "session_id": session_id,
                "phone_number": phone_number,
            },
        )

runner = Runner(agent=chef, session_service=service, app_name=APP_NAME)

# function to call the agent
def ask_agent(session_id: str, user_id: str, text: str, phone: str): # for improved efficiency
    msg = types.Content(role="user", parts=[types.Part(text=text)])

    for ev in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=msg
    ):
        # Only print the assistant's text part, ignore warnings about non-text parts
        if ev.is_final_response() and ev.content and ev.content.parts:
            # Only print text parts
            for part in ev.content.parts:
                if hasattr(part, 'text') and part.text:
                    # log.info(f"🤖 [AI] {part.text}")
                    return part.text


def main():
    get_or_create_agent_session(USER_ID, SESSION_ID, "1234567890") # Create a new session for the user

    print("Welcome to the AI Voice Agent!")

    print("\nHabit Tracker ready (type 'quit' to exit)\n")
    while True:
        q = input("You: ")
        if q.lower() in ("quit", "exit"):
            print("Session saved. Bye!")
            break

        ask_agent(SESSION_ID, USER_ID, q, runner)


if __name__ == "__main__":
    # main()
    
    runner = get_or_create_agent_session(USER_ID, SESSION_ID) # Create a new session for the user
    res = ask_agent(SESSION_ID, USER_ID, "hi", runner)
    print(res)

    # # We now manually fetch the session from memory so we can inspect its state. 
    # session = service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

    # # 6️⃣ Print updated state
    # print("\n📘 Final session state:")
    # for key, value in session.state.items():
    #     print(f"{key}: {value}")


