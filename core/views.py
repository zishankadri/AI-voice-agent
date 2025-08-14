import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import google.generativeai as genai

from .logger import get_logger
log = get_logger()

load_dotenv()
DEVELOPMENT = os.getenv("development", "false").lower() == "true"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash')

from .models import Order, Restaurant, AdminSetting, StatusEnum  # update import path
from .agent import get_or_create_agent_session, ask_agent  # same here

USER_ID = "CUSTOMER"
APP_NAME = "voice_agent"


# ------------------ 🤝 Helpers ------------------ 
def get_or_create_order(call_sid: str, phone_number: str) -> Order:
    restaurant = Restaurant.objects.get(phone_number=phone_number)
    order, _ = Order.objects.get_or_create(
        call_sid=call_sid,
        restaurant=restaurant,
    )
    return order


# --- Twilio voice start ---
@csrf_exempt
def voice(request):
    log.info("Start")
    response = VoiceResponse()
    gather = Gather(
        input='speech',
        action='/process_speech/',
        method='POST',
        timeout=15,
        speech_timeout='auto'
    )
    # Fetch greeting
    greeting = AdminSetting.objects.get(key="GREETING")
    # response_text = "Hi! What would you like to order today?"
    response_text = greeting.value
    
    gather.say(response_text, voice='man', language='en-US')
    log.info(f"[AI] {response_text}")

    response.append(gather)
    response.say("Sorry, I didn't catch that. Please try again.")
    return HttpResponse(str(response), content_type='text/xml')



# --- Process user input ---
@csrf_exempt
def process_speech(request):
    """
    Runs in a loop
    """

    call_id = request.POST.get("CallSid")
    log.info(f"Processing speech...{call_id = }")

    # Our Twillio phone number
    if DEVELOPMENT: 
        print("DEVELOPMENT")
        to_number = request.POST.get("From")
    else: to_number = request.POST.get("To")

    transcript = request.POST.get("SpeechResult", "")

    order = get_or_create_order(call_sid=call_id, phone_number=to_number)

    if order:
        order.conversation += f"👋 [User]: \n\t {transcript}\n🤖 [Agent]: \n"
        order.save()

    # TODO: 
    get_or_create_agent_session(user_id=USER_ID, session_id=call_id, phone_number=to_number)

    agent_response = ask_agent(
        session_id=call_id,
        user_id=USER_ID,
        text=transcript,
        phone=to_number,
    )
    log.info(f"success {agent_response}")
    # Re-fetch to get the latest order state in case it was modified by a tool.
    order = get_or_create_order(call_sid=call_id, phone_number=to_number)  
    order.conversation += f"\t{agent_response}\n"  # 🤖 [Agent] response
    order.save()

    response = VoiceResponse()

    if order.status == StatusEnum.CONFIRMED:
        # Say agent response then hang up immediately
        response.say(agent_response, voice='man', language='en-US')
        response.hangup()
    else:
        gather = Gather(
            input='speech',
            action='/process_speech/',
            method='POST',
            timeout=20,
            speech_timeout='auto'
        )
        gather.say(agent_response, voice='man', language='en-US')
        response.append(gather)
        response.say("I can't hear you, goodbye.")
    return HttpResponse(str(response), content_type='text/xml')
