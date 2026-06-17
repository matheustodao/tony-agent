import dataclasses

import sounddevice as sd
import regex as re
from numpy import ndarray
import threading
from tools.process_tts import _process_text_to_audio_samples
from multiprocessing.queues import Queue as MQueue
from multiprocessing import Process, Queue

@dataclasses.dataclass
class StreamingVoice:
    speech_buffer: str = ''
    word_counter: int = 0

    # Threads
    _speech_queue: MQueue[str] = Queue()
    _speaking_thread: None | Process = None

    _audio_queue: MQueue[ndarray] = Queue()
    _audio_thread: None | threading.Thread = None

    _MAX_WORD_COUNTER: int = 10
    _SAMPLE_RATE: int = 24_000
    _REGEX_STRONG: str = r"([.!?\n])"  # pausa forte  → fala imediato
    _REGEX_WEAK: str = r"[,;:]"  # pausa fraca  → acumula até MAX

    def __post_init__(self):
        if self._speech_queue is None:
            self._speech_queue = Queue()

        if self._speaking_thread is None:
            self._speaking_thread = Process(
                target=_process_text_to_audio_samples,
                args=(self._speech_queue, self._audio_queue),
                #kwargs={ 'speech_queue': self._speech_queue, 'audio_queue': self._audio_queue },
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
            self._clear_queue_speech()

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

    def audio_worker(self):
        while True:
            audio = self._audio_queue.get()

            if audio is None:
                continue

            sd.play(data=audio, samplerate=self._SAMPLE_RATE)
            sd.wait(ignore_errors=True)

    def _clear_queue_speech(self):
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
            except None:
                break