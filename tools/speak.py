import dataclasses

from kokoro import KPipeline
import sounddevice as sd
import regex as re
from numpy import ndarray
# import torch
from strands import tool
import queue
import threading

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

    # Threads
    _speech_queue: queue.Queue[str] = queue.Queue()
    _speaking_thread: None | threading.Thread = None

    _audio_queue: queue.Queue[ndarray] = queue.Queue()
    _audio_thread: None | threading.Thread = None

    _MAX_WORD_COUNTER: int = 75
    _SAMPLE_RATE: int = 24_000
    _REGEX_STRONG: str = r"([.!?\n])"  # pausa forte  → fala imediato
    _REGEX_WEAK: str = r"[,;:]"  # pausa fraca  → acumula até MAX

    def __post_init__(self):
        if self._speech_queue is None:
            self._speech_queue = queue.Queue()

        if self._speaking_thread is None:
            self._speaking_thread = threading.Thread(
                target=self.speaking_worker,
                daemon=True
            )
            self._speaking_thread.start()

        if self._audio_thread is None:
            self._audio_thread = threading.Thread(
                target=self.audio_worker,
                daemon=True
            )
            self._audio_thread.start()

    def stream_voice(self, **kwargs):
        print('LIFECYCLE', kwargs)
        if 'start_event_loop' in kwargs and kwargs['start_event_loop'] is True:
            with self._speech_queue.mutex:
                self._speech_queue.queue.clear()
                self._speech_queue.unfinished_tasks = 0
                self._speech_queue.all_tasks_done.notify_all()

        if 'event' in kwargs and 'messageStop' in kwargs['event']:
            if self.speech_buffer.strip():
                self._speech_queue.put(self.speech_buffer.strip())
            self._clear_buffer(_force=True)

        if not 'data' in kwargs:
            return

        chunk = kwargs.get('data')

        self._manipulate_buffer(chunk)

        if self._can_talk():
            self._speech_queue.put(self.speech_buffer)
            self._clear_buffer(_force=True)

    def _manipulate_buffer(self, chunk: str | None):
        if chunk is None:
            return

        self.speech_buffer += chunk

        parts = re.split(self._REGEX_STRONG, self.speech_buffer, maxsplit=1)

        if len(parts) > 1:
            phrase: str = (parts[0] + parts[1]).strip()

            if phrase:
                self._speech_queue.put(phrase)

            self.speech_buffer = parts[2].lstrip()

        self.word_counter = len([word.strip() for word in self.speech_buffer.split(' ')])

    def _can_talk(self) -> bool:
        if re.search(self._REGEX_WEAK, self.speech_buffer):
            return True

        return (
            self.word_counter >= self._MAX_WORD_COUNTER or
            re.search(self._REGEX_WEAK, self.speech_buffer)
        )

    def _clear_buffer(self, _force: bool = False):
        if _force or self._can_talk():
            self.speech_buffer = ""
            self.word_counter = 0
            return

    def speak(self, text: str) -> None:
        if not text.strip():
            return

        for chunk in _generate_speech(text.strip()):
            self._audio_queue.put(chunk.output.audio.numpy())

    def speaking_worker(self):
        while True:
            speech = self._speech_queue.get()

            if not speech or speech is None:
                continue

            self.speak(text=speech)

    def audio_worker(self):
        while True:
            audio = self._audio_queue.get()

            if audio is None:
                continue

            sd.play(data=audio, samplerate=self._SAMPLE_RATE)
            sd.wait(ignore_errors=True)