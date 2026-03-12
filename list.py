from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

print("\nAvailable Models:\n")

try:
    for model in client.models.list():
        print(model.name)
except Exception as e:
    print("Failed to fetch models:", e)