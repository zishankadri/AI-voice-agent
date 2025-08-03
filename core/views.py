import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import google.generativeai as genai
from .models import Order, OrderItem, MenuItem  # update import path
from .agent import get_or_create_agent_session, ask_agent  # same here

from .logger import get_logger
log = get_logger()

load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash')

USER_ID = "CUSTOMER"
APP_NAME = "voice_agent"


# --- DB session logic ---
def get_or_create_db_session(call_sid):
    session = Order.objects.filter(call_sid=call_sid).first()
    if not session:
        session = Order(call_sid=call_sid)
        session.save()
    return session


# --- Twilio voice start ---
@csrf_exempt
def voice(request):
    log.info("Start")
    response = VoiceResponse()
    gather = Gather(
        input='speech',
        action='/process_speech/',
        method='POST',
        speech_timeout='auto'
    )
    response_text = "Hi! What would you like to order today?"
    gather.say(response_text, voice='man', language='en-US')
    log.info(f"[AI] {response_text}")

    response.append(gather)
    response.say("Sorry, I didn't catch that. Please try again.")
    return HttpResponse(str(response), content_type='text/xml')


# --- Process user input ---
@csrf_exempt
def process_speech(request):
    log.info("Processing speech...")

    call_id = request.POST.get("CallSid")
    transcript = request.POST.get("SpeechResult", "")

    log.info(f"👋 [User] {transcript}")

    get_or_create_db_session(call_id)
    get_or_create_agent_session(user_id=USER_ID, session_id=call_id)

    agent_response = ask_agent(
        session_id=call_id,
        user_id=USER_ID,
        text=transcript,
    )

    response = VoiceResponse()
    gather = Gather(
        input='speech',
        action='/process_speech/',
        method='POST',
        timeout=20,
        speech_timeout='auto'
    )
    gather.say(agent_response)
    response.append(gather)
    response.say("I can't hear you, goodbye.")
    return HttpResponse(str(response), content_type='text/xml')
