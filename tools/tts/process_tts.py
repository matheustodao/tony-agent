import asyncio
import os
import os
import onnxruntime as ort
import torch
from multiprocessing.queues import Queue as MQueue
from kokoro_onnx import Kokoro
from numpy import ndarray
from decorators.profiling import profiling
import unicodedata
import re

sess_options = ort.SessionOptions()
sess_options.intra_op_num_threads = 4  # Ajuste para 2 ou 4 dependendo da sua CPU
sess_options.inter_op_num_threads = 4
sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

_KEEP = {'°'}
_DROP_CATS = {'So', 'Sk', 'Cs', 'Co', 'Cn', 'Cf', 'Mn', 'Me'}

def strip_emoji(text: str) -> str:
    return ''.join(
        c for c in text
        if c in _KEEP or unicodedata.category(c) not in _DROP_CATS
    )


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")

def clean_for_speech(text: str) -> str:
    text = strip_emoji(text)
    text = _MD_LINK.sub(r"\1", text)                       # [texto](url) -> texto
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)  # títulos
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)   # marcadores de lista
    text = _EMOJI.sub("", text)                            # emojis
    text = re.sub(r"[*_`~#>|]", "", text)                  # símbolos restantes
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r":$", ".", text)                        # ":" no fim vira pausa
    return text

# kokoro-onnx só resolve `str` pelo nome no voices-v1.0.bin; voz customizada tem de ser um ndarray.
VOICE = torch.load(os.path.join(BASE_DIR, "../../voices/pm_alex.pt"), weights_only=True).numpy()

async def _stream_to_queue(kokoro: Kokoro, text: str, audio_queue: MQueue[ndarray]):
    kokoroStream = kokoro.create_stream(
        text=text, voice=VOICE, speed=1.2, lang="pt-br"
    )

    async for samples, _ in kokoroStream:
        if samples is not None and len(samples) > 0:
            audio_queue.put(samples)


def process_text_to_audio_samples(speech_queue: MQueue[str], audio_queue: MQueue[ndarray]):
    session = ort.InferenceSession(
        os.path.join(BASE_DIR, "kokoro/onnx/kokoro-v1.0.onnx"),
        sess_options=sess_options,
        providers=["CPUExecutionProvider"],
    )

    kokoro = Kokoro.from_session(
        session,
        voices_path=os.path.join(BASE_DIR, "kokoro/onnx/voices-v1.0.bin"),
    )

    # warmup
    asyncio.run(_stream_to_queue(kokoro, "", audio_queue))
    while not audio_queue.empty():
        audio_queue.get_nowait()

    while True:
        speech = speech_queue.get()
        speech = clean_for_speech(speech)
        if not speech.strip() or not re.search(r"\w", speech):
            continue

        asyncio.run(_stream_to_queue(kokoro, speech, audio_queue))
