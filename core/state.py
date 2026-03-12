import logging
from google import genai
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class LoomState:
    """Holds the global state and memory for L.O.O.M."""
    def __init__(self):
        self.geminiClient = genai.Client()
        self.openrouterClient = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )


        self.orchestratorChat = []
        self.desktopChat = None
        logging.info("L.O.O.M. Global state initialized")
        

globalState = LoomState()