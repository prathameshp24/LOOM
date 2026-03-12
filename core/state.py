import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class LoomState:
    """Holds the global state and memory for L.O.O.M."""
    def __init__(self):
        self.client = genai.Client()
        self.orchestratorChat = None
        self.desktopChat = None
        logging.info("L.O.O.M. Global state initialized")
        

globalState = LoomState()