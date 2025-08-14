import asyncio
from asgiref.sync import sync_to_async
from difflib import get_close_matches
from typing import Callable, Any, Dict
import functools
import json

from .logger import get_logger
log = get_logger()

from .models import (
    Restaurant,
    Order,
    Category,
    OrderItem,
    MenuItem,
    StatusEnum,
)

# ------------------ 🤝 Helpers ------------------ 
def get_or_create_order(call_sid: str) -> Order:
    order, _ = Order.objects.get_or_create(call_sid=call_sid)
    return order


def find_menu_item_by_name(name: str) -> MenuItem | None:
    all_names = MenuItem.objects.values_list('name', flat=True)
    print("\n\nall_names\n: ", all_names)
    matches = get_close_matches(name, all_names, n=1, cutoff=0.8)
    if matches:
        return MenuItem.objects.filter(name=matches[0]).first()
    return None

def to_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Fetches the menu from the database for a restaurant identified by its phone number.

    Args:
        phone_number (str): The phone number of the restaurant.

    Returns:
        str: A formatted string of the menu, grouped by category, with each item and its price.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await sync_to_async(func)(*args, **kwargs)
    return wrapper

# ------------------ 🛠️ Tools ------------------ 


def format_menu_for_instructions(menu_dict):
    log.info(type(menu_dict))
    log.info(menu_dict)
    menu_string = ""
    for category, items in menu_dict.items():
        menu_string += f"**{category}:**\n"
        for item, price in items.items():
            menu_string += f"- {item}: ${price:.2f}\n"
        menu_string += "\n" # Add a newline for separation between categories
    return menu_string

@to_async
def get_menu(phone_number: str) -> Dict[str, Dict[str, Any]]:
    """
    Fetches the menu from the database for a restaurant identified by its phone number.

    This function is designed to be called from an asynchronous agent. The
    @to_async decorator handles running the synchronous database queries
    on a background thread.

    Args:
        phone_number (str): The phone number of the restaurant.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary representing the menu,
                                    grouped by category, with each item and its price.
    """
    menu_dict = {}
    print(phone_number)
    log.info(f"Fetching restaurant for phone number: '{phone_number}'")
    restaurant = Restaurant.objects.get(phone_number=phone_number)
    print(f"{restaurant = }")
    
    categories = Category.objects.filter(menuitem__restaurant=restaurant).distinct()
    log.info(f"categories: {categories}")

    for category in categories:
        items = MenuItem.objects.filter(restaurant=restaurant, category=category)
        if items.exists():
            menu_dict[category.name] = {item.name: item.price for item in items}

    print(menu_dict)
    log.info(menu_dict)
    return menu_dict

# @transaction.atomic
@to_async
def set_or_modify_items(
    session_id: str,
    items: list[dict[str, Any]],
    modifications: list[dict[str, Any]] = []
) -> dict[str, Any]:
    """
    Creates a new order for a specific person or modifies an existing order for that person.

    Args:
        session_id (str): A unique identifier for the order.
        items (List[Dict[str, Any]]): A list of dictionaries, where each dictionary represents an item
                                      with at least 'name' (str) and 'quantity' (int) keys.
                                      Example: [{'name': 'Laptop', 'quantity': 1}, {'name': 'Mouse', 'quantity': 2}]
        modifications (List[Dict[str, Any]]): A list of dictionaries, where each dictionary
                                                        specifies extra modifications for items.
                                                        Each dictionary should have an 'item_name' (str) key
                                                        and a 'details' (str) key.

    Returns:
        Dict[str, Any]: A dictionary indicating the success or failure of the operation,
                        and potentially details about the order.
    """
    log.info(f"[items] {items}")
    log.info(f"[modifications] {modifications}")
    log.info(f"[session_id] {session_id}")

    try:
        order = get_or_create_order(session_id)
        processed_items = []

        for item in items:
            item_name = item.get("name")
            quantity = item.get("quantity")

            if not item_name or quantity is None:
                return {"status": "error", "message": "Each item must have 'name' and 'quantity'."}

            item_modifications = [
                mod.get("details") for mod in modifications if mod.get("item_name") == item_name
            ]
            modifications_str = json.dumps(item_modifications) if item_modifications else None

            menu_item = find_menu_item_by_name(item_name)
            if not menu_item:
                return {"status": "error", "message": f"Item '{item_name}' not found in menu."}

            existing_item = OrderItem.objects.filter(
                order=order, menu_item=menu_item
            ).first()

            if existing_item:
                existing_item.quantity = quantity
                existing_item.modifications = modifications_str
                existing_item.save()
            else:
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    modifications=modifications_str
                )

            processed_items.append({
                "name": item_name,
                "quantity": quantity,
                "modifications": item_modifications
            })
        order.conversation += f"\t✅ [set_or_modify_items] 200 Success\n"
        order.save()
        log.info(f"[set_or_modify_items] 200 {session_id}")
        return {
            "status": "success",
            "message": "Order created or modified successfully.",
            "ordered_items": processed_items
        }

    except Exception as e:
        order.conversation += f"\t❌ [set_or_modify_items] 402 Exception {e} {session_id}\n"
        order.save()
        # log.exception(f"[set_or_modify_items] 402 Exception {e} {session_id}")
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


@to_async
def confirm_order(session_id: str) -> dict[str, Any]:
    """Mark an order as cofirmed so that the kichen team can start prepairing.

    Args:
        session_id (str): A unique identifier for the order.
                         This will serve as the primary key for the order.
    Returns:
        Dict[str, Any]: A dictionary indicating the success or failure of the operation,
                        and potentially details about the order.
    """
    try:
        order = get_or_create_order(session_id)
        if not order:
            return {"status": "error", "message": "Order not found."}

        order.status = StatusEnum.CONFIRMED  # assuming you have a `confirmed` field

        order.conversation += f"\t✅ [confirm_order] 200 Success\n"
        order.save()
        log.info(f"[confirm_order] 200 {session_id}")
        return {"status": "success", "message": "Order confirmed."}
    except Exception as e:
        order.conversation += f"\t❌ [confirm_order] error {e}\n"
        order.save()
        # log.exception(f"[confirm_order] error {e}")
        return {"status": "error", "message": f"Could not confirm order: {e}"}

@to_async
def set_order_type(session_id: str, order_type: str) -> dict[str, Any]:
    """Set the type of the order (e.g., 'delivery', 'pickup', 'table booking').

    Args:
        session_id (str): A unique identifier for the order.
                         This will serve as the primary key for the order.
        order_type (str): The type of the order, 'delivery', 'pickup' or 'table booking' nothing else is allowed.
    Returns:
        Dict[str, Any]: A dictionary indicating the success or failure of the operation,
                        and potentially details about the order.
    """
    try:
        order = get_or_create_order(session_id)
        if not order:
            return {"status": "error", "message": "Order not found."}

        order.order_type = order_type  # assuming you have an `order_type` field

        order.conversation += f"\t✅ [set_order_type] 200 Success\n"
        order.save()
        # log.info(f"[set_order_type] 200 {session_id}")
        return {"status": "success", "message": "Order type set successfully."}
    except Exception as e:
        order.conversation += f"\t❌ [set_order_type] error {e}\n"
        order.save()
        # log.exception(f"[set_order_type] error {e}")
        return {"status": "error", "message": f"Could not set order type: {e}"}


@to_async
def set_address(session_id: str, address: str) -> dict[str, Any]:
    """Set address for an order with order type 'delivery'.

    Args:
        session_id (str): A unique identifier for the order.
                         This will serve as the primary key for the order.
        address (str): The full delivery address for the order.
    Returns:
        Dict[str, Any]: A dictionary indicating the success or failure of the operation,
    """
    try:
        order = get_or_create_order(session_id)
        if not order:
            return {"status": "error", "message": "Order not found."}

        order.address = address  # assuming you have an `address` field

        order.conversation += f"\t✅ [set_address] 200 Success\n"
        order.save()
        # log.info(f"[set_address] 200 {session_id}")
        return {"status": "success", "message": "Address set successfully."}
    except Exception as e:
        order.conversation += f"\t❌ [set_address] error {e}\n"
        order.save()
        # log.exception(f"[set_address] error {e}")
        return {"status": "error", "message": f"Could not set address: {e}"}

@to_async
def set_table_booking(session_id: str, no_of_people: int, time: str) -> dict[str, Any]:
    """
    Sets a table booking for a specific order session.

    Args:
        session_id (str): Unique identifier for the order session.
        no_of_people (int): Number of people for the table booking.
        time (str): The booking time.

    Returns:
        dict[str, Any]: A dictionary indicating success or failure of setting the booking,
                        including relevant messages.
    """
    try:
        order = get_or_create_order(session_id)
        if not order:
            return {"status": "error", "message": "Order not found."}

        order.order_type = 'table_booking'
        order.no_of_people = no_of_people  # make sure field exists
        order.booking_time = time          # make sure field exists (DateTimeField preferred, parse time accordingly)

        order.conversation += f"\t✅ [set_table_booking] 200 Success\n"
        order.save()
        log.info(f"[set_table_booking] 200 {session_id}")
        return {"status": "success", "message": "Table booking set successfully."}
    except Exception as e:
        order.conversation += f"\t❌ [set_table_booking] error {e}\n"
        order.save()
        log.exception(f"[set_table_booking] error {e}")
        return {"status": "error", "message": f"Could not set table booking: {e}"}


@to_async
def set_pick_up_branch(session_id: str, branch_name: str, time: str) -> dict[str, Any]:
    """
    Sets the pickup branch and pickup time for an order.

    Args:
        session_id (str): Unique identifier for the order session.
        branch_name (str): Name of the pickup branch chosen by the customer.
        time (str): The pickup time whatever the user said.

    Returns:
        dict[str, Any]: A dictionary indicating success or failure of setting pickup details,
                        including relevant messages.
    """
    try:
        order = get_or_create_order(session_id)
        if not order:
            return {"status": "error", "message": "Order not found."}

        order.order_type = 'pickup'
        order.pickup_branch = branch_name  # ensure this field exists
        order.pickup_time = time            # parse to DateTime if needed

        order.conversation += f"\t✅ [set_pick_up_branch] 200 Success\n"
        order.save()
        log.info(f"[set_pick_up_branch] 200 {session_id}")
        return {"status": "success", "message": "Pickup branch and time set successfully."}
    except Exception as e:
        order.conversation += f"\t❌ [set_pick_up_branch] error {e}\n"
        order.save()
        log.exception(f"[set_pick_up_branch] error {e}")
        return {"status": "error", "message": f"Could not set pickup branch: {e}"}

@to_async
def transfer_to_human(session_id: str) -> dict[str, Any]:
    """
    Transfers the current conversation to a human agent for further assistance.

    Args:
        session_id (str): A unique identifier for the current session.

    Returns:
        Dict[str, Any]: A dictionary indicating the success or failure of the transfer request.
    """
    pass

@to_async
def call_back(session_id: str) -> dict[str, Any]:
    """
    Flags the current order/session as requiring a callback from the restaurant.

    Args:
        session_id (str): Unique identifier for the order session.

    Returns:
        dict[str, Any]: A dictionary indicating success or failure of the callback request,
                        including relevant messages.
    """
    try:
        order = get_or_create_order(session_id)
        if not order:
            return {"status": "error", "message": "Order not found."}

        order.status = StatusEnum.CALL_BACK_REQUESTED  # You need to define this enum value
        order.conversation += f"\t✅ [call_back] 200 Success\n"
        order.save()
        log.info(f"[call_back] 200 {session_id}")
        return {"status": "success", "message": "Callback requested."}
    except Exception as e:
        order.conversation += f"\t❌ [call_back] error {e}\n"
        order.save()
        log.exception(f"[call_back] error {e}")
        return {"status": "error", "message": f"Could not request callback: {e}"}