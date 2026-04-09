import logging
from google import genai
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

CLOUD_ORCHESTRATOR_MODEL = "arcee-ai/trinity-large-preview:free"
CLOUD_DESKTOP_MODEL      = "nvidia/nemotron-3-nano-30b-a3b:free"
LOCAL_MODEL              = "qwen3:4b"

class LoomState:
    """Holds the global state and memory for L.O.O.M."""
    def __init__(self):
        self.geminiClient = genai.Client()

        self.openrouterClient = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.ollamaClient = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",         # Ollama ignores the key but the SDK requires one
            default_headers={"X-Ollama-Think": "false"},  # belt-and-suspenders hint
        )

        self.mode = "cloud"           # "cloud" | "local"
        self.voiceMode: bool = False
        self.wakeWordActive: bool = False

        self.orchestratorChat = []
        self.desktopChat = []
        self.browserChat = []
        logging.info("L.O.O.M. Global state initialized")

    # --- transparent routing helpers ---

    @property
    def activeClient(self) -> OpenAI:
        return self.ollamaClient if self.mode == "local" else self.openrouterClient

    @property
    def orchestratorModel(self) -> str:
        return LOCAL_MODEL if self.mode == "local" else CLOUD_ORCHESTRATOR_MODEL

    @property
    def desktopModel(self) -> str:
        return LOCAL_MODEL if self.mode == "local" else CLOUD_DESKTOP_MODEL

    def switchMode(self, mode: str):
        """Switch backend and wipe shared context so histories don't cross-contaminate."""
        if mode not in ("cloud", "local"):
            raise ValueError(f"Unknown mode: {mode}")
        self.mode = mode
        self.orchestratorChat = []
        self.desktopChat = []
        self.browserChat = []
        logging.info(f"🔀 Switched to {mode.upper()} mode — context cleared")


globalState = LoomState()