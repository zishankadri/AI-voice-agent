from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
# text-3xl-fluid

app = Flask(__name__)

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    print("Hit Newest")
    response = VoiceResponse()

    gather = Gather(
        input='speech',
        action='https://101723816170.ngrok-free.app/process_speech',  # full URL!
        method='POST',
        speech_timeout='auto'
    )
    gather.say("Hi! What would you like to order today?", voice='man', language='en-US')
    response.append(gather)

    # Fallback if no speech is detected
    response.say("Sorry, I didn't catch that. Please try again.")

    return Response(str(response), mimetype='text/xml')


@app.route("/process_speech", methods=['POST'])
def process_speech():
    transcript = request.form.get('SpeechResult', 'None')
    print("User said:", transcript)

    response = VoiceResponse()
    response.say(f"You said: {transcript}. Thanks, we are processing your order.", voice="man", language="en-US")
    return Response(str(response), mimetype='text/xml')


if __name__ == "__main__":
    app.run(port=5000)
