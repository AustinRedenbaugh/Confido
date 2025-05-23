import json
from openai import OpenAI

class GPTAgent:
    def __init__(self, openai_client, model="gpt-4o-mini"):
        self.client = openai_client
        self.model = model
        self.sessions = {}  # You can inject this externally if needed
        self.available_functions = [
            {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"]
                }
            }
        ]

    def get_functions(self):
        return { "get_weather": self.get_weather }

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

    def get_weather(self, location):
        # Dummy function
        return {"temperature": "72F", "condition": "Sunny in " + location}
