from multiprocessing.queues import Queue as MQueue
from kokoro import KPipeline
from numpy import ndarray

def _process_text_to_audio_samples(speech_queue: MQueue[str], audio_queue: MQueue[ndarray]):
    pipeline = KPipeline(
        lang_code='p',
        repo_id='hexgrad/Kokoro-82M',
    )

    def generator_speech(text: str):
        return pipeline(
            text=text,
            voice='pm_alex',
        )

    for _ in generator_speech('Olá meus amigos'):
        pass

    while True:
        speech = speech_queue.get()

        if speech is None:
            continue

        if not speech.strip():
            continue

        for chunk in generator_speech(speech):
            samples = chunk.output.audio.numpy()
            audio_queue.put(samples)
