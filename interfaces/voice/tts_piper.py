import re
import subprocess
import logging

logger = logging.getLogger(__name__)


def _sanitize(text: str) -> str:
    text = re.sub(r'[*_`#]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def speak(text: str) -> None:
    """Speak text via espeak-ng (non-blocking). Strips markdown before speaking."""
    if not text or not text.strip():
        return
    clean = _sanitize(text)
    try:
        subprocess.Popen(
            ["espeak-ng", "-s", "155", "-p", "50", "-a", "180", clean],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        logger.warning("espeak-ng not found. Install: sudo dnf install espeak-ng")
    except Exception as e:
        logger.error(f"TTS error: {e}")
