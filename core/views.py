import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from pydantic_ai import ModelRequest, ModelResponse, TextPart, UserPromptPart
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import google.generativeai as genai

from .logger import get_logger

log = get_logger()

load_dotenv()

DEVELOPMENT = os.getenv("DEVELOPMENT", "false").lower() == "true"

# model = genai.GenerativeModel("gemini-2.0-flash")

from .models import Order, Restaurant, AdminSetting, StatusEnum  # update import path
from .agent import get_or_create_agent_session, ask_agent  # same here
from .tools import agent, OrderDeps, format_menu_for_instructions  # and here

# USER_ID = "CUSTOMER"
# APP_NAME = "voice_agent"


# ------------------ 🤝 Helpers ------------------
def get_or_create_order(call_sid: str, phone_number: str, customer_phone) -> Order:
    restaurant = Restaurant.objects.get(phone_number=phone_number)
    order, created = Order.objects.get_or_create(
        call_sid=call_sid,
        restaurant=restaurant,
        customer_phone=customer_phone,
    )
    return order


# ------------------ Twilio voice ------------------
@csrf_exempt
def voice(request):
    log.info("Start")
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/process_speech/",
        method="POST",
        timeout=15,
        speech_timeout="auto",
    )
    # Fetch greeting
    greeting = AdminSetting.objects.get(key="GREETING")
    # response_text = "Hi! What would you like to order today?"
    response_text = greeting.value

    gather.say(response_text, voice="man", language="en-US")
    log.info(f"[AI] {response_text}")

    response.append(gather)
    response.say("Sorry, I didn't catch that. Please try again.")
    return HttpResponse(str(response), content_type="text/xml")


# ------------------ Process user input ------------------
@csrf_exempt
def process_speech(request):
    """
    Runs in a loop
    """
    call_id = request.POST.get("CallSid")
    log.info(f"Processing speech...{call_id = }")
    user_speech = request.POST.get("SpeechResult", "")

    if DEVELOPMENT:
        to_number = request.POST.get("From")
        from_number = request.POST.get("To")
    else:
        to_number = request.POST.get("To")
        from_number = request.POST.get("From")
    print(f"{from_number = }\n{to_number = }")

    # order, _ = Order.objects.get_or_create(call_sid=call_id)
    order = get_or_create_order(
        call_sid=call_id, phone_number=to_number, customer_phone=from_number
    )
    conversation = order.conversation
    conversation.append({"role": "user", "text": user_speech})

    pydantic_messages = []
    for msg in conversation[:-1]:
        if msg["role"] == "user":
            pydantic_messages.append(
                ModelRequest(parts=[UserPromptPart(content=msg["text"])])
            )
        elif msg["role"] == "agent":
            pydantic_messages.append(
                ModelResponse(parts=[TextPart(content=msg["text"])])
            )

    # Main ==================================================================
    deps = OrderDeps(session_id=call_id, phone_number=to_number)
    agent_response = agent.run_sync(
        user_speech,
        message_history=pydantic_messages,
        deps=deps,
    )
    ai_reply = agent_response.output.strip()
    conversation.append({"role": "agent", "text": ai_reply})
    log.info(f"success {ai_reply}")

    # Re-fetch to get the latest order state in case it was modified by a tool.
    # order, _ = Order.objects.get_or_create(call_sid=call_id)
    order = get_or_create_order(
        call_sid=call_id, phone_number=to_number, customer_phone=from_number
    )
    response = VoiceResponse()

    if order.status == StatusEnum.CONFIRMED:
        response.say(ai_reply, voice="man", language="en-US")
        response.hangup()
    elif order.status == StatusEnum.CALL_BACK_REQUESTED:
        response.say(ai_reply, voice="man", language="en-US")
        response.hangup()
    else:
        gather = Gather(
            input="speech",
            action="/process_speech/",
            method="POST",
            timeout=20,
            speech_timeout="auto",
        )
        gather.say(ai_reply, voice="man", language="en-US")
        response.append(gather)
        response.say("I can't hear you, goodbye.")

    order.conversation = conversation
    order.save()

    return HttpResponse(str(response), content_type="text/xml")
