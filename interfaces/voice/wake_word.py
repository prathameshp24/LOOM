import logging
import threading
import time
import numpy as np

logger = logging.getLogger(__name__)

_thread = None
_running = False
_detecting = True   # False while a voice command is being processed

WAKE_WORD_MODEL    = "hey_jarvis"   # built-in openwakeword model (say "Hey Jarvis" to trigger)
DETECTION_THRESHOLD = 0.5
CHUNK_SIZE          = 1280          # 80ms at 16 kHz — required by openwakeword
SAMPLE_RATE         = 16000


def _process_command():
    """Record and handle a voice command after wake word fires."""
    global _detecting
    try:
        from interfaces.voice.tts_piper import speak
        from interfaces.voice.stt_whisper import listenAndTranscribe
        from core.orchestrator import processUserRequest

        speak("Yes?")
        time.sleep(0.4)   # let TTS finish before mic opens

        text = listenAndTranscribe(duration=6)

        if text and text.strip():
            logger.info(f"🎙️  Wake command: {text}")

            def emit(msg: str):
                if not msg.startswith("__status__") and msg.strip():
                    speak(msg)

            processUserRequest(text, emit=emit)
        else:
            speak("I didn't catch that.")

    except Exception as e:
        logger.error(f"Wake word command error: {e}")
    finally:
        _detecting = True
        logger.info("🎙️  Resuming wake word detection")


def _wake_loop():
    global _running, _detecting
    try:
        import sounddevice as sd
        from openwakeword.model import Model

        logger.info(f"Loading wake word model '{WAKE_WORD_MODEL}'...")
        oww = Model(wakeword_models=[WAKE_WORD_MODEL], inference_framework="onnx")
        logger.info("✅ Wake word ready — say 'Hey Jarvis' to activate LOOM")

        audio_queue: list[np.ndarray] = []
        lock = threading.Lock()

        def audio_callback(indata, frames, time_info, status):
            if not _detecting:
                return
            chunk = (indata[:, 0] * 32767).astype(np.int16)
            with lock:
                audio_queue.append(chunk)

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            callback=audio_callback,
        ):
            while _running:
                chunk = None
                with lock:
                    if audio_queue:
                        chunk = audio_queue.pop(0)

                if chunk is not None and _detecting:
                    prediction = oww.predict(chunk)
                    for score in prediction.values():
                        if score > DETECTION_THRESHOLD:
                            logger.info(f"🎙️  Wake word detected! (score={score:.2f})")
                            _detecting = False
                            oww.reset()
                            with lock:
                                audio_queue.clear()
                            threading.Thread(target=_process_command, daemon=True).start()
                            break
                else:
                    time.sleep(0.005)

    except ImportError:
        logger.error("openwakeword not installed. Run: pip install openwakeword")
        _running = False
    except Exception as e:
        logger.error(f"Wake word loop error: {e}")
        _running = False


def start():
    global _thread, _running
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_wake_loop, daemon=True)
    _thread.start()
    logger.info("🎙️  Wake word detection started")


def stop():
    global _running
    _running = False
    logger.info("🎙️  Wake word detection stopped")


def is_running() -> bool:
    return _running
