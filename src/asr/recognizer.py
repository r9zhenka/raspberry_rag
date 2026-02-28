import json
import logging
import numpy as np
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)


class Recognizer:
    def __init__(self, model_path: str, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        logger.info(f"Loading Vosk model from {model_path}...")
        self.model = Model(model_path)
        logger.info("Vosk model loaded.")

    def recognize(self, audio: np.ndarray) -> str:
        """Recognize speech from int16 audio array. Returns text or empty string."""
        if len(audio) == 0:
            return ""

        rec = KaldiRecognizer(self.model, self.sample_rate)
        rec.SetWords(False)

        # Feed audio in chunks for streaming-like processing
        chunk_size = 4000
        audio_bytes = audio.astype(np.int16).tobytes()

        for i in range(0, len(audio_bytes), chunk_size * 2):
            chunk = audio_bytes[i : i + chunk_size * 2]
            rec.AcceptWaveform(chunk)

        result = json.loads(rec.FinalResult())
        text = result.get("text", "").strip()

        if text:
            logger.info(f"Recognized: {text}")
        else:
            logger.info("No speech recognized")

        return text
