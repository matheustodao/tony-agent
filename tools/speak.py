import dataclasses

from kokoro import KPipeline
import sounddevice as sd
import regex as re
# import torch
from strands import tool
import codecs

pipeline = KPipeline(
    lang_code='p',
    repo_id='hexgrad/Kokoro-82M',
)

# voice = torch.load(
#     '../voices/pm_alex.pt',
#     weights_only=True
# )

def _generate_speech(text: str):
    generator = pipeline(
        text=text,
        voice='pm_alex',
        speed=1,
        split_pattern='\\n'
    )

    return generator

def _warmup_speech():
    _generate_speech(text="""
    Claro! Aqui estão dez animais: cachorro, gato, macaco, leão, elefante, girafa, flamingo, rato, papagaio e tartaruga. Você gostaria de saber mais sobre algum deles?'}], 'metadata': {'usage': {'inputTokens': 155, 'outputTokens': 55, 'totalTokens': 210}, 'metrics': {'latencyMs': 32064, 'timeToFirstByteMs': 18}}}, metrics=EventLoopMetrics(cycle_count=1, tool_metrics={}, cycle_durations=[58.317513942718506], agent_invocations=[AgentInvocation(cycles=[EventLoopCycleMetric(event_loop_cycle_id='653ce843-a2f4-47b8-90fd-ac544861348f', usage={'inputTokens': 155, 'outputTokens': 55, 'totalTokens': 210})], usage={'inputTokens': 155, 'outputTokens': 55, 'totalTokens': 210})], traces=[<strands.telemetry.metrics.Trace object at 0x749e5c171280>], accumulated_usage={'inputTokens': 155, 'outputTokens': 55, 'totalTokens': 210}, accumulated_metrics={'latencyMs': 32064}), state={}, interrupts=None, structured_output=None, checkpoint=None)}
Claro! Aqui estão dez animais: cachorro, gato, macaco, leão, elefante, girafa, flamingo, rato, papagaio e tartaruga. Você gostaria de saber mais sobre algum deles?
    """)

_warmup_speech()

@dataclasses.dataclass
class StreamingVoice:
    speech_buffer: str = ''
    word_counter: int = 0
    _MAX_WORD_COUNTER = 75
    _REGEX_PONTING = r"[,.!?:]"
    _SAMPLE_RATE = 24_000

    def stream_voice(self, **kwargs):
        print('LIFECYCLE', kwargs)
        # if 'message' in kwargs:
        #     message = kwargs.get('message')
        #     content = message.get('content')
        #     feedback = content[0].get('toolUse')
        #     if feedback:
        #         input = feedback.get('input')
        #         inputMessage = input.get('message')
        #         self.speech_buffer += codecs.decode(inputMessage)
        #         self.speak()
        #         return
        #     return

        if 'event' in kwargs and 'messageStop' in kwargs['event']:
            self.speak()

        if not 'data' in kwargs:
            return

        chunk = kwargs.get('data')

        self._manipulate_buffer(chunk)

        if self._can_talk():
            self.speak()

    def _manipulate_buffer(self, chunk: str | None):
        if chunk is None:
            return

        self.speech_buffer += chunk
        self.word_counter = len([word.strip() for word in self.speech_buffer.split(' ')])

    def _can_talk(self) -> bool:
        return (
            self.word_counter >= self._MAX_WORD_COUNTER or
            self._has_pointing(self.speech_buffer)
        )

    def _clear_buffer(self, _force: bool = False):
        if _force or self._can_talk():
            self.speech_buffer = ""
            self.word_counter = 0
            return

    def _has_pointing(self, text: str):
        return bool(re.search(self._REGEX_PONTING, text))

    @tool
    def speak(self):
        if self.speech_buffer.strip():
            for chunk in _generate_speech(self.speech_buffer.strip()):
                sd.play(data=chunk.output.audio.numpy(), samplerate=self._SAMPLE_RATE)
                sd.wait(ignore_errors=True)

        self._clear_buffer(_force=True)
