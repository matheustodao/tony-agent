from strands import Agent
from strands.models.ollama import OllamaModel
from tools import speak, time
from assistant_config import assistant
from tools.hardware import get_hardware_information

brain = OllamaModel(
    host='http://127.0.0.1:11434',
    model_id='qwen2.5:7b',
    temperature=0.3,
    keep_alive="10m"
)

voice_streaming = speak.StreamingVoice()

agent = Agent(
    model=brain,
    tools=[time.currentDateAndTime, get_hardware_information],
    system_prompt="/no_think\n\nResponda SEMPRE em português brasileiro. Nunca use outro idioma.\n\n" + assistant.short_prompt,
    callback_handler=voice_streaming.stream_voice,
)


def _warmup_agent():
    agent('wakeup')

_warmup_agent()