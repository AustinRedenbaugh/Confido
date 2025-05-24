import json
from openai import OpenAI
import os
import httpx
from dotenv import load_dotenv
load_dotenv()

POSTGRESQL_BASE_URL = os.getenv("POSTGRESQL_BASE_URL")

class GPTAgent:
    def __init__(self, openai_client, model="gpt-4o-mini"):
        self.client = openai_client
        self.model = model
        self.sessions = {}  # You can inject this externally if needed
        self.available_functions = [
            {
                "name": "fetch_insurance_status",
                "description": "Check if an insurance provider is accepted by the clinic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the insurance provider.",
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
            }
        ]


    def get_functions(self):
        return { "fetch_insurance_status": self.fetch_insurance_status }

    async def handle_response(self, call_sid, user_prompt):
        messages = self.sessions.setdefault(call_sid, [
            {"role": "system", "content": "You are a helpful assistant."}
        ])

        messages.append({"role": "user", "content": user_prompt})

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
            func_result = self.get_functions()[func_name](**func_args)

            messages.append({
                "role": "assistant",
                "function_call": dict(name=func_name, arguments=json.dumps(func_args))
            })

            messages.append({
                "role": "function",
                "name": func_name,
                "content": json.dumps(func_result)
            })

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

    async def fetch_insurance_status(name: str) -> bool:
        """Fetch whether an insurance is accepted based on its name."""
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
