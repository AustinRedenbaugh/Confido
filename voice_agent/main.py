import asyncio
import os
import uuid
import json
import uvicorn
import httpx
from zoneinfo import ZoneInfo
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from openai import OpenAI
from dotenv import load_dotenv
from starlette.responses import HTMLResponse
from datetime import datetime, timezone
from assistants.front_desk_assistant import FrontDeskAssistant
from twilio.rest import Client

# Initialize once at top level
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)


from dotenv import load_dotenv
load_dotenv()

# Initialize OpenAI client
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Store active sessions
sessions = {}

# Create FastAPI app
app = FastAPI()

@app.post("/incoming-call")
async def incoming_call():
    print("POST TwiML")
    service_url = os.environ.get("NGROK_URL")
    assert(service_url)
    if service_url.startswith("http"):
        from urllib.parse import urlparse
        service_url = urlparse(service_url).netloc
        print("service_url: ", service_url)
    tmpl = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <ConversationRelay url="wss://{service_url}/twilio-ws" welcomeGreeting="{greeting}" welcomeGreetingInterruptible="none" ttsProvider="ElevenLabs" voice="{voice_id}" hints="cigna" transcriptionProvider="Deepgram" speechModel ="nova-2-general" preemptible="true"></ConversationRelay>
  </Connect>
</Response>
    """
    return HTMLResponse(content=tmpl.format(service_url=service_url, greeting=FrontDeskAssistant.greeting, voice_id=os.getenv("ELEVENLABS_VOICE_ID")), media_type="application/xml")


@app.websocket("/twilio-ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    call_sid = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            print(f"Received message: {message}")
            
            if message["type"] == "setup":
                call_sid = message["callSid"]
                print(f"Setup for call: {call_sid}")
                websocket.call_sid = call_sid

                # Record call:
                account_sid = os.getenv("TWILIO_ACCOUNT_SID")
                auth_token = os.getenv("TWILIO_AUTH_TOKEN")
                auth = (account_sid, auth_token)
                url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}/Recordings.json"
                response = httpx.post(url, auth=auth)
                if response.status_code == 201:
                    print("Recording started successfully!")
                    print(response.json())
                else:
                    print("Failed to start recording:", response.text)

                # # 🟢 Start recording this call
                # try:
                #     twilio_client.calls(call_sid).update(record=True)
                #     print(f"Recording started for call {call_sid}")
                # except Exception as e:
                #     print(f"Failed to start recording for {call_sid}: {e}")
                
                now = datetime.now(ZoneInfo("America/New_York"))
                formatted_time = now.strftime("%A, %B %-d, %-I:%M%p").lower().replace("pm", "pm").replace("am", "am")
                # Capitalize the first letter manually
                formatted_time_nice = formatted_time[0].upper() + formatted_time[1:]

                full_system_prompt = (
                    FrontDeskAssistant.system_prompt +
                    f"\nAt the beginning of this call, the time and date was: {formatted_time_nice} | {formatted_time}"
                )
                sessions[call_sid] = [{"role": "system", "content": full_system_prompt}]

            elif message["type"] == "prompt":
                print(f"Processing prompt: {message['voicePrompt']}")
                print(f"Current sessions:\n\n {sessions}")
                conversation = sessions[websocket.call_sid]
                conversation.append({"role": "user", "content": message["voicePrompt"]})
                
                conversation, response = await gpt_agent.handle_response(websocket, conversation)
                conversation.append({"role": "assistant", "content": response})
                
                await websocket.send_text(
                    json.dumps({
                        "type": "text",
                        "token": response,
                        "last": True
                    })
                )
                print(f"Sent response: {response}")
                
            elif message["type"] == "interrupt":
                print("Handling interruption.")
                
            else:
                print(f"Unknown message type received: {message['type']}")
                
    except WebSocketDisconnect:
        print("WebSocket connection closed")
        if call_sid:
            sessions.pop(call_sid, None)



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5050, reload=True)