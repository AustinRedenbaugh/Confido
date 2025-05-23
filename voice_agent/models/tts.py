from abc import ABC, abstractmethod
from twilio.twiml.voice_response import VoiceResponse, Say, Play
from assistants.front_desk_assistant import FrontDeskAssistant


class TTSStrategy(ABC):
    @abstractmethod
    def speak(self, response: VoiceResponse, text: str):
        pass


class TwilioCheapStrategy(TTSStrategy):
    def speak(self, response: VoiceResponse, text: str):
        response.say(text)


class TwilioGoogleStrategy(TTSStrategy):
    # Replace with actual Google TTS logic
    def speak(self, response: VoiceResponse, text: str):
        response.say(text, voice="Google.en-US-Wavenet-D", language="en-US")


class ElevenLabsStrategy(TTSStrategy):
    # Simulated audio URL generation — replace with real ElevenLabs logic
    def speak(self, response: VoiceResponse, text: str):
        audio_url = f"https://yourdomain.com/polly/{hash(text)}.mp3"
        response.play(audio_url)


# Mapping for strategy lookup
STRATEGY_MAP = {
    'twilio': TwilioCheapStrategy(),
    'twilio-google': TwilioGoogleStrategy(),
    '11labs': ElevenLabsStrategy()
}


def handle_tts(response: VoiceResponse, text: str):
    model_key = FrontDeskAssistant.config.get('tts_model', 'twilio')
    strategy = STRATEGY_MAP.get(model_key, TwilioCheapStrategy())
    strategy.speak(response, text)
