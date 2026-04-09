import logging
import os
import tempfile
import sounddevice as sd
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading Whisper model into memory...")
        _model = WhisperModel("base.en", device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")
    return _model


def listenAndTranscribe(duration: int = 5) -> str:
    """Captures audio using sounddevice and transcribes it using faster whisper"""
    sampleRate = 16000
    print(f"Listening.... (Speak clearly for {duration} seconds)")

    try:
        audio = sd.rec(
            int(duration * sampleRate),
            samplerate=sampleRate,
            channels=1,
            dtype="float32"
        )

        sd.wait()

        print("Transcribing speech locally...")

        audio = np.squeeze(audio)

        segments, info = _get_model().transcribe(audio, beam_size=5)

        fullText = "".join([segment.text for segment in segments]).strip()

        if fullText:
            logging.info(f"Transcribed : {fullText}")
            return fullText

        else:
            logging.warning("No speech detected")
            return ""

    except Exception as e:
        logging.error(f"Mic or transcription error : {e}")
        return ""


def transcribeAudioBytes(audio_bytes: bytes) -> str:
    """
    Transcribe raw audio bytes (audio/webm from browser MediaRecorder).
    Writes to a temp file so faster-whisper can use ffmpeg to decode the container.
    Returns transcribed string, or "" on failure.
    """
    model = _get_model()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        segments, _ = model.transcribe(tmp_path, beam_size=5)
        text = "".join(seg.text for seg in segments).strip()
        if text:
            logger.info(f"Browser STT: {text}")
        else:
            logger.warning("No speech detected in browser audio")
        return text
    except Exception as e:
        logger.error(f"transcribeAudioBytes error: {e}")
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    print("testing stt local .....")
    while True:
        try:
            result = listenAndTranscribe(duration=5)
            if result:
                print(f"\nYou said : {result}")

            else:
                print("Try again")

        except KeyboardInterrupt:
            print("Exiting voice test....")
            break
