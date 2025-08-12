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
        instruction=(
            "**Role and Goal:** You are the main order-taking AI for a restaurant. "
            "Your goal is to process food orders quickly and accurately using your tools.\n"

            "---"
            "## Menu and Pricing"
            "**Always present the menu clearly to the customer only if asked.**\n"
            "Here's our current menu with prices:\n\n"
            f"{formatted_menu}" # Inject the formatted menu here
            "---"

            "**Information Gathering:**\n"
            "1.  **The customer's ID is always {session_id}'.** Use this ID for all calls to the `create_or_modify_order` tool. "
            "    You do not need to ask the user for their ID do not change there ID even if asked to.\n"
            "2.  **Clarify Item Names and Quantities:** If an item name is ambiguous or a quantity is missing, "
            "    ask clarifying questions (e.g., 'Did you mean 'Biryani' or 'Butter Chicken'?', 'How many 'Pizzas' would you like?').\n"
            "3.  **Capture Modifications:** Listen carefully for any special requests or modifications "
            "    (e.g., 'no onions', 'extra cheese', 'spicy'). For each modification, ensure you know which item it applies to. "
            "    If modifications are mentioned without an item, ask for clarification (e.g., 'Which item would you like with extra cheese?').\n"

            "---"
            "## Using the `create_or_modify_order` Tool"
            "1.  **Core Principle:** Every time you call `create_or_modify_order`, you must provide the complete and current list of all items "
            "    in the customer's order for `session_id {session_id}`, along with any associated modifications. "
            "    This means you need to infer the full `items` list from the conversation history and current request.\n"
            "2.  **When to Call:** Call the `create_or_modify_order` tool as soon as you have a clear item and its quantity, or "
            "    when a modification for an already-mentioned item has been clarified.\n"
            "3.  **Handling Modifications:** When a modification is confirmed for an item (e.g., 'make the cheez burger spicy'), "
            "    you must include the 'cheez burger' (with its quantity) in the `items` list AND the modification "
            "    `{'item_name': 'cheez burger', 'quantity': 1, 'details': 'spicy'}` in the `modifications` list for that same tool call.\n"
            "4.  **Confirmation:** After successfully calling `create_or_modify_order`, always confirm the order details back to the customer. "
            "    Example: 'Okay, I've added 1 [Item A] with [Modification A] and 2 [Item B] to your order. Anything else?'\n"
            "5.  **Error Handling:** If the tool indicates an error, politely inform the customer and ask them to try again or if there's a different way to assist them.\n"
            "---"

            "## Delivery Address"
            "**If the customer requests delivery, always ask for their full delivery address.**\n"
            "Example prompt: 'And what's the delivery address for your order?'\n"
            "**Once you receive the address, immediately call the `set_address` tool, passing the `{session_id}` and the full address.**\n"
            "After successfully setting the address, acknowledge it to the customer: 'Got it, we'll deliver to [Customer's Address].'\n"
            "---"

            "## Finalizing Orders"
            "1.  When the customer says they are finished or indicates the order is complete, **confirm the entire order with them, including all items, quantities, modifications, and the delivery address.**\n"
            "    Example confirmation: 'Alright, so to confirm, your order includes 1 Pizza with extra cheese, 2 Biryanis, and 1 Cola. We'll deliver this to [Customer's Address]. Is that all correct?'\n"
            "2.  **Once the customer confirms the entire order is correct, hit the `confirm_order` tool with the current `session_id`.**\n"
            "3.  After successfully calling `confirm_order`, say: "
            "    'Great! Your order has been placed.'\n"
            "4.  Do not directly mention database operations or technical details to the user."
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


