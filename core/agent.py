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


from .models import Restaurant, MenuItem, Category
def format_menu_for_instructions(menu_dict):
    menu_string = ""
    for category, items in menu_dict.items():
        menu_string += f"**{category}:**\n"
        for item, price in items.items():
            menu_string += f"- {item}: ${price:.2f}\n"
        menu_string += "\n" # Add a newline for separation between categories
    return menu_string

def get_menu_dict_by_phone(phone_number):
    """
    Fetches menu items from the database for the restaurant with the given phone number.
    Returns a dictionary in the format:
    {
        "Category Name": {
            "Item Name": price,
            ...
        },
        ...
    }
    """
    menu_dict = {}
    print(phone_number)
    log.info(f"Fetching restaurant for phone number: '{phone_number}'")
    restaurant = Restaurant.objects.get(phone_number=phone_number)
    
    categories = Category.objects.filter(menuitem__restaurant=restaurant).distinct()
    log.info(f"categories: {categories}")

    for category in categories:
        items = MenuItem.objects.filter(restaurant=restaurant, category=category)
        if items.exists():
            menu_dict[category.name] = {item.name: item.price for item in items}

    return menu_dict


AGENT_CACHE = {}
def get_chef(phone_number):
    """
    Fetches the chef agent for the restaurant with the given phone number.
    Returns an Agent instance configured with the restaurant's menu.
    """

    if phone_number in AGENT_CACHE:
        return AGENT_CACHE[phone_number]
    # Fetch the menu items for the restaurant
    menu_dict = get_menu_dict_by_phone(phone_number)
    formatted_menu = format_menu_for_instructions(menu_dict)

    chef = Agent(
        name=APP_NAME,
        model="gemini-2.0-flash", # Use a suitable Gemini model
        instruction=("""Role & Goal:
            You are a restaurant order-taking AI. Your primary job is to take orders, modify them, and finalize them accurately and efficiently. Use the tools provided strictly to update the order state and never expose internal or technical details to the customer.

            Core Principles for Tool Usage
            Session ID Management:

            Always use the provided {session_id} from the customer’s session for all tool calls.

            Never ask or change the session ID. Treat it as the unique identifier of the customer order.

            create_or_modify_order Tool:

            Use this tool whenever you have any new or updated item or modification to add to the order.

            Always send the complete and current list of all ordered items with quantities AND any modifications.

            Do NOT send incremental changes only — send the full order snapshot every time.

            Ask clarifying questions if item names or quantities are unclear before calling this tool.

            Confirm back to the user the successful addition or modification of items.

            If the tool returns an error, politely notify the user and offer to retry or clarify.

            set_address Tool:

            Use this tool as soon as the customer provides a delivery address for an order with delivery type.

            Prompt the customer for their full delivery address explicitly if delivery is requested but no address yet provided.

            Confirm the address back to the user after successfully setting it.

            confirm_order Tool:

            Use this tool only when the customer explicitly indicates the order is complete and ready to be placed.

            Before confirming, repeat the full order summary including all items, quantities, modifications, and delivery details.

            After confirmation, tell the customer the order has been successfully placed.

            set_order_type Tool:

            Use this tool to set the order type to one of: 'delivery', 'pickup', or 'table booking'.

            Ask the customer what kind of order they want before placing items.

            Use the order type to decide which other tools to call (e.g., delivery needs set_address).

            set_table_booking Tool:

            Use this when the customer wants to book a table.

            Collect the number of people and booking time before calling.

            Confirm the booking details to the user.

            set_pick_up_branch Tool:

            Use this when the customer opts for pickup.

            Ask for pickup branch location and time, then call this tool.

            Confirm pickup details after success.

            transfer_to_human Tool:

            Call this tool when the customer explicitly requests to talk to a human or if you cannot handle the request.

            Inform the user that you are connecting them to a human agent.

            call_back Tool:

            Use this when the customer asks for a callback from the restaurant.

            Confirm the callback request to the user.

            Conversation & Clarification Best Practices
            Always clarify ambiguous or missing information about items, quantities, or modifications before calling any tools.

            Never guess or assume — ask questions like:

            “Did you mean ‘Chicken Biryani’ or ‘Veg Biryani’?”

            “How many of that would you like?”

            “Which item would you like with extra cheese?”

            Repeat important details back to the user to confirm understanding before calling tools.

            Error Handling
            If any tool call returns an error, notify the user with a polite message:
            “Sorry, I had trouble processing that. Could you please rephrase or try again?”

            If errors persist, offer to connect to a human by calling transfer_to_human.

            What NOT to Do
            Do NOT expose tool names, code, or database operations to the customer.

            Do NOT change or ask for session IDs.

            Do NOT finalize or confirm orders without explicit customer approval.

            Do NOT move forward without necessary info like quantities, delivery addresses, or booking details.

            """
        ),
        tools=[
            create_or_modify_order,
            set_address,
            confirm_order,
            set_table_booking,
            set_pick_up_branch,
            set_order_type,
            transfer_to_human,
            call_back,
        ]
    )

    AGENT_CACHE[phone_number] = chef
    return chef


service = InMemorySessionService() # A session backend that stores conversational state in memory

def get_or_create_agent_session(user_id: str, session_id: str):
    """
    Returns an existing session if a session with the session_id already exists,
    otherwise creates a new session.
    """
    existing_session = service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )
    if existing_session:
        print(f"Session with ID '{session_id}' already exists. Returning existing session.")

    if not existing_session:
        print(f"Session with ID '{session_id}' not found Creating a new session.")
        service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={"session_id": session_id}
        )

def get_runner_for_phone(phone_number):
    agent = get_chef(phone_number)
    return Runner(agent=agent, session_service=service, app_name=APP_NAME)

# function to call the agent
def ask_agent(session_id: str, user_id: str, text: str, phone: str): # for improved efficiency
    msg = types.Content(role="user", parts=[types.Part(text=text)])
    runner = get_runner_for_phone(phone)

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
    get_or_create_agent_session(USER_ID, SESSION_ID) # Create a new session for the user

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


