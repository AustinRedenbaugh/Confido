import json
from openai import OpenAI
import os
import random
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

POSTGRESQL_BASE_URL = os.getenv("POSTGRESQL_BASE_URL")

class GPTAgent:
    def __init__(self, openai_client, model="gpt-4o-mini"):
        self.client = openai_client
        self.model = model

        now = datetime.now(ZoneInfo("America/New_York"))
        formatted_time = now.strftime("%A, %B %-d, %Y, %-I:%M%p").lower().replace("pm", "pm").replace("am", "am")
        formatted_time_nice = formatted_time[0].upper() + formatted_time[1:]

        self.time_nice = formatted_time_nice
        self.time = formatted_time

    def get_available_functions(self):
        available_functions = [
            {
                "name": "fetch_insurance_status",
                "description": "IF the customer wants to know if a specific insurance provider is accepted AND there is no fetch_insurance_status function call in the conversation, THEN Run this function.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": (
                                "The name of the insurance provider. "
                                "If the customer specified an insurance provider name, then reference the enum values to determine if you misheard them. "
                                "Assume the customer asked about one of the insurance providers in the enum.\n"
                                "If the customer mentions an insurance provider and it closely matches a value in the ENUM, assume they meant the ENUM value and call fetch_insurance_status to check if it's accepted."
                            ),
                            "enum": [
                                "BlueCross BlueShield",
                                "UnitedHealthcare",
                                "Aetna",
                                "Cigna",
                                "Humana",
                                "Kaiser Permanente"
                            ]
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "check_appt_slots",
                "description": (
                    "If the customer wants to know what appointment slots are available between two times, "
                    "use this function to return available appointment times."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": f"The start of the time window (ISO 8601 format, e.g., YYYY-MM-DDTHH:MM:SS) For reference, it is currently {self.time} | {self.time_nice}"
                        },
                        "end_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": f"The end of the time window (ISO 8601 format, e.g., YYYY-MM-DDTHH:MM:SS) For reference, it is currently {self.time} | {self.time_nice}"
                        }
                    },
                    "required": ["start_time", "end_time"]
                }
            }
        ]

    def get_functions(self):
        return {
            "fetch_insurance_status": self.fetch_insurance_status,
            "check_appt_slots": self.check_appt_slots
        }

    async def handle_response(self, websocket, conversation):
        
        messages = conversation.copy()

        ## PRUNE CONVERSATION HERE ##
        # For example, Limit the number of messages to the system message + the last 8 messages
        if len(messages) > 9:
            messages = [messages[0]] + messages[-8:]


        # Initial completion request
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            functions=self.available_functions,
            function_call="auto"
        )

        choice = response.choices[0].message

        if choice.function_call:
            func_name = choice.function_call.name
            func_args = json.loads(choice.function_call.arguments)
            func = self.get_functions()[func_name]
            func_result = await func(**func_args)
            formatted_string = get_formatted_string(func_name, func_args, func_result)

            messages.append({
                "role": "assistant",
                "function_call": dict(name=func_name, arguments=json.dumps(func_args))
            })

            messages.append({
                "role": "function",
                "name": func_name,
                "content": formatted_string
            })
            conversation.append({
                "role": "function",
                "name": func_name,
                "content": formatted_string
            })

            idx = random.randint(1, 10)  # inclusive
            url = f"{POSTGRESQL_BASE_URL}/static/keyboard-typing-{idx}.mp3"
            print(f"Sending audio URL: {url}")
            await websocket.send_text(json.dumps({
                "type": "play_audio",
                "url": url
            }))

            # GPT continues after receiving function result
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            assistant_reply = final_response.choices[0].message.content
            messages.append({"role": "assistant", "content": assistant_reply})
            return assistant_reply

        else:
            messages.append({"role": "assistant", "content": choice.content})
            return choice.content

    async def fetch_insurance_status(self, name: str) -> bool:
        """Fetch whether an insurance is accepted based on its name."""
        print(f"Fetching insurance status for: {name}")
        url = f"{POSTGRESQL_BASE_URL}/get_insurance_status"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params={"name": name})
                response.raise_for_status()
                data = response.json()
                print(f"Insurance status for {name}: {data}")
                return data["accepted"]
        except httpx.HTTPStatusError as e:
            print(f"HTTP error while fetching insurance status: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
        
    async def check_appt_slots(self, start_time: str, end_time: str) -> list:
        """Fetch available appointment slots between two ISO8601 timestamps."""
        print(f"Checking appointment slots from {start_time} to {end_time}")
        url = f"{POSTGRESQL_BASE_URL}/check_appt_slots"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params={"start_time": start_time, "end_time": end_time})
                response.raise_for_status()
                data = response.json()
                print(f"Available slots: {data}")
                return data["slots"]
        except httpx.HTTPStatusError as e:
            print(f"HTTP error while checking appointment slots: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []

def get_formatted_string(func_name, func_args, func_result):
    """
    Function to get the formatted string for the function call.
    """

    if func_name == "fetch_insurance_status":
        accepted = func_result
        provider = func_args.get("name", "that provider")

        formatted_string = ""
        if accepted:
            formatted_string = f"Good news, we do accept {provider} insurance."
        else:
            formatted_string = f"Unfortunately, we do not carry or accept {provider} insurance."

        return formatted_string
    
    elif func_name == "check_appt_slots":
        
        slots = func_result
        if not slots:
            return "I'm sorry, there are no available appointment slots during that time range."

        # Convert to TZ-4 (e.g., New York)
        eastern = ZoneInfo("America/New_York")
        formatted_times = []

        for slot in slots:
            # Parse ISO string, convert to local TZ, and format
            dt = datetime.fromisoformat(slot["start_time"]).astimezone(eastern)
            formatted = dt.strftime("%m-%d %I:%M%p").lstrip("0").replace(" 0", " ")
            formatted_times.append(formatted)

        times_list = ", ".join(formatted_times)
        return f"Here are the corresponding available appointment times: [{times_list}]"
