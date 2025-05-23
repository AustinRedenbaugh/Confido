from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from assistants.front_desk_assistant import FrontDeskAssistant

app = Flask(__name__)

# In-memory store for conversation state.
# For production, you'd use a database (e.g., Redis, PostgreSQL)
# Key: CallSid, Value: dictionary of conversation context
conversations_state = {}

@app.route("/incoming-call", methods=['POST'])
def incoming_call():
    """Handles the initial incoming calls from Twilio."""

    print("Incoming call received.")
    print(f"Request data: {request.values}")

    call_sid = request.values.get('CallSid')
    print(f"Incoming call from: {request.values.get('From')} - CallSid: {call_sid}")

    # Initialize conversation state for this call
    conversations_state[call_sid] = {
        "turn_count": 0,
        "history": []
    }

    response = VoiceResponse()
    response.say(FrontDeskAssistant.greeting)

    # Gather the first piece of input from the user
    gather = Gather(input='speech', action='/process-speech', method='POST', timeout=5, speechTimeout='auto')
    # You can add hints for better speech recognition if needed:
    # gather.add_hints(hints="reservations, support, sales")
    response.append(gather)

    # If the user doesn't say anything, redirect to gather again or say something else
    response.redirect('/handle-no-input', method='POST')

    return str(response)

@app.route("/process-speech", methods=['POST'])
def process_speech():
    """Processes the speech input gathered from the user."""
    call_sid = request.values.get('CallSid')
    speech_result = request.values.get('SpeechResult', '').lower()
    confidence = request.values.get('Confidence', 0.0)

    print(f"CallSid: {call_sid} - User said: '{speech_result}' with confidence: {confidence}")

    response = VoiceResponse()

    # Retrieve or initialize conversation state
    if call_sid not in conversations_state:
        # This should ideally not happen if incoming-call was hit first
        # But as a fallback, initialize
        conversations_state[call_sid] = {"turn_count": 0, "history": []}
        response.say("There was an issue retrieving our conversation. Let's start over.")
        gather = Gather(input='speech', action='/process-speech', method='POST')
        response.append(gather)
        response.redirect('/handle-no-input', method='POST')
        return str(response)

    current_state = conversations_state[call_sid]
    current_state["turn_count"] += 1
    current_state["history"].append({"user": speech_result})

    # --- Your AI/Logic to determine the response ---
    # This is where you'd integrate with your NLU, LLM, or business logic
    # For this example, let's do some simple conditional logic:

    ai_response_text = ""
    should_end_call = False

    if "hello" in speech_result or "hi" in speech_result:
        ai_response_text = "Hello to you too! What can I do for you?"
    elif "your name" in speech_result:
        ai_response_text = "I am a helpful voice assistant created by you."
    elif "how are you" in speech_result:
        ai_response_text = "I'm doing well, thank you for asking! How can I assist?"
    elif "bye" in speech_result or "goodbye" in speech_result:
        ai_response_text = "Goodbye! Have a great day."
        should_end_call = True
    elif not speech_result: # Handle cases where SpeechResult might be empty
        ai_response_text = "I didn't catch that. Could you please repeat?"
    else:
        ai_response_text = f"You said: {speech_result}. Is there anything else I can help with?"

    # --- End AI/Logic ---

    response.say(ai_response_text)
    current_state["history"].append({"assistant": ai_response_text})

    if should_end_call:
        response.hangup()
        # Clean up state for this call
        if call_sid in conversations_state:
            del conversations_state[call_sid]
            print(f"Cleaned up state for CallSid: {call_sid}")
    else:
        # Gather the next piece of input
        gather = Gather(input='speech', action='/process-speech', method='POST', timeout=5, speechTimeout='auto')
        response.append(gather)
        response.redirect('/handle-no-input', method='POST') # If user doesn't speak

    # Update the state
    conversations_state[call_sid] = current_state
    # print(f"Current state for {call_sid}: {conversations_state[call_sid]}")

    return str(response)

@app.route("/handle-no-input", methods=['POST'])
def handle_no_input():
    """Handles cases where Twilio's <Gather> times out without user input."""
    call_sid = request.values.get('CallSid')
    print(f"No input detected for CallSid: {call_sid}")

    response = VoiceResponse()

    if call_sid in conversations_state:
        # Example: Give one more chance or hang up
        if conversations_state[call_sid].get("no_input_attempts", 0) < 1:
            conversations_state[call_sid]["no_input_attempts"] = conversations_state[call_sid].get("no_input_attempts", 0) + 1
            response.say("I didn't hear anything. Could you please say that again?")
            gather = Gather(input='speech', action='/process-speech', method='POST', timeout=5, speechTimeout='auto')
            response.append(gather)
            response.redirect('/handle-no-input', method='POST') # Loop back here if still no input
        else:
            response.say("I still didn't hear anything. I'll hang up now. Goodbye.")
            response.hangup()
            if call_sid in conversations_state:
                del conversations_state[call_sid] # Clean up state
    else:
        # Should not happen if call started correctly
        response.say("It seems we're having trouble. Goodbye.")
        response.hangup()

    return str(response)

@app.route("/call-status", methods=['POST'])
def call_status():
    """Optional: Receives status updates about the call from Twilio."""
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    print(f"Call Status Update - CallSid: {call_sid}, Status: {call_status}")

    # If the call is completed or failed, clean up its state
    if call_status in ['completed', 'failed', 'canceled', 'busy', 'no-answer']:
        if call_sid in conversations_state:
            del conversations_state[call_sid]
            print(f"Call ended. Cleaned up state for CallSid: {call_sid}")

    return ('', 204) # Respond with 204 No Content or an empty TwiML <Response/>

if __name__ == "__main__":
    # For development, Flask's built-in server is fine.
    # For production, use a WSGI server like Gunicorn:
    # gunicorn --bind 0.0.0.0:5000 app:app
    # Gunicorn handles concurrent requests better.
    app.run(debug=True, port=5050)