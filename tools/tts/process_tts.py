import asyncio
import os
from multiprocessing.queues import Queue as MQueue
from kokoro_onnx import Kokoro
from numpy import ndarray
from decorators.profiling import profiling
import unicodedata


def clean_text(text: str) -> str:
    cleaned = ''.join(
        c for c in text
        if unicodedata.category(c) not in ('So', 'Cs', 'Co', 'Cn')
    )
    return cleaned.strip()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def _stream_to_queue(kokoro: Kokoro, text: str, audio_queue: MQueue[ndarray]):
    async for samples, _ in kokoro.create_stream(
        text=text, voice="pm_alex", speed=1.0, lang="pt-br"
    ):
        if samples is not None and len(samples) > 0:
            audio_queue.put(samples)


def process_text_to_audio_samples(speech_queue: MQueue[str], audio_queue: MQueue[ndarray]):
    kokoro = Kokoro(
        model_path=os.path.join(BASE_DIR, "kokoro/onnx/kokoro-v1.0.onnx"),
        voices_path=os.path.join(BASE_DIR, "kokoro/onnx/voices-v1.0.bin"),
    )

    # warmup
    asyncio.run(_stream_to_queue(kokoro, "olá", audio_queue))
    while not audio_queue.empty():
        audio_queue.get_nowait()

    while True:
        speech = speech_queue.get()
        speech = clean_text(speech)
        if not speech.strip():
            continue

        asyncio.run(_stream_to_queue(kokoro, speech, audio_queue))
