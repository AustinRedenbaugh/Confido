import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

class GPTAgent:
    def __init__(self, call_sid):
        self.call_sid = call_sid
        self.history = []

    def generate_reply(self, user_text):
        self.history.append({"role": "user", "content": user_text})
        completion = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a helpful assistant."}] + self.history,
            max_tokens=200,
        )
        reply = completion.choices[0].message.content
        self.history.append({"role": "assistant", "content": reply})
        return reply
