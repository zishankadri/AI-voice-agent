from twilio.twiml.voice_response import VoiceResponse, Gather
import google.generativeai as genai
import json
import os
import re

import logging

# Create a specific logger for your app
app_logger = logging.getLogger('conversation')
app_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('conversation.log')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
file_handler.setFormatter(formatter)

app_logger.addHandler(file_handler)


from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, CallSession

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env into os.environ

# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
call_sessions = {}

# Function to extract order from user text using Gemini

def extract_order(text):
    prompt = f"""
    Extract the food order from this sentence: "{text}"
    Return **only** JSON in this format:
    {{
        "items": [
            {{
                "name": "item name",
                "qty": quantity (int),
                "modifiers": [optional list of modifiers]
            }}
        ]
    }}
    Do NOT include any explanation or extra text.
    """
    try:
        res = model.generate_content(prompt)
        content = res.text.strip()

        # Extract first JSON object using regex
        match = re.search(r'\{[\s\S]*\}', content)
        if not match:
            raise ValueError("No JSON object found in Gemini response")

        json_str = match.group(0)
        return json.loads(json_str)

    except Exception as e:
        print("Gemini Error:", e)
        return {"items": []}

def build_confirmation_text(order):
    items = order.get("items", [])
    if not items:
        return "Sorry, I couldn't understand your order."
    parts = []
    for item in items:
        qty = item.get("qty", 1)
        name = item.get("name", "item")
        mods = item.get("modifiers", [])
        if mods:
            parts.append(f"{qty} {name} with {', '.join(mods)}")
        else:
            parts.append(f"{qty} {name}")
    return "Did you say " + ", and ".join(parts) + "?"

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    response = VoiceResponse()
    gather = Gather(
        input='speech',
        action='/process_speech',
        method='POST',
        speech_timeout='auto'
    )
    response_text = "Hi! What would you like to order today?"
    gather.say(response_text, voice='man', language='en-US')
    app_logger.info(f"[AI] {response_text}")

    response.append(gather)
    response.say("Sorry, I didn't catch that. Please try again.")
    return Response(str(response), mimetype='text/xml')

@app.route("/process_speech", methods=['POST'])
def process_speech():
    call_id = request.form.get("CallSid")
    transcript = request.form.get('SpeechResult', '')
    # print("\n👋 User said:", transcript , end="\n\n")
    app_logger.info(f"[User] {transcript}")

    order = extract_order(transcript)

    # Save to DB
    existing = CallSession.query.filter_by(call_sid=call_id).first()
    if existing:
        existing.order_json = json.dumps(order)
    else:
        new = CallSession(call_sid=call_id, order_json=json.dumps(order))
        db.session.add(new)
    db.session.commit()


    # Confirm the order with the user
    confirmation = build_confirmation_text(order)
    response = VoiceResponse()
    gather = Gather(
        input='speech',
        action='/confirm_order',
        method='POST',
        timeout=5,
        speech_timeout='5',
        language='en-US',
        hints="pizza, sandwich, with cheese, coke, fries",
    )
    gather.say(confirmation, voice='man', language='en-US')
    response.append(gather)
    response.say("I didn’t catch that. Please say yes or no.")
    return Response(str(response), mimetype='text/xml')

@app.route("/confirm_order", methods=['POST'])
def confirm_order():
    answer = request.form.get('SpeechResult', '').lower()
    app_logger.info(f"[AI confirmation] {answer}")

    response = VoiceResponse()
    if "yes" in answer:
        response.say("Great! Your order has been placed. Thank you!", voice='man', language='en-US')

    elif "no" in answer:
        response.say("Okay, let's try again.", voice='man', language='en-US')
        response.redirect('/voice')
    else:
        gather = Gather(
            input='speech',
            action='/confirm_order',
            method='POST',
            speech_timeout='auto'
        )
        gather.say("Sorry, I didn’t understand that. Please say yes to confirm or no to try again.", voice='man', language='en-US')
        response.append(gather)
        response.say("Still didn’t catch that. Goodbye.")  # fallback

    return Response(str(response), mimetype='text/xml')

if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False)

