import os
import requests
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in .env")

# Request available voices
headers = {
    "sk_82b234639936677a4d2004aebbd99f25109fced741a2ef47": ELEVENLABS_API_KEY
}

response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
if response.status_code != 200:
    print("Failed to fetch voices:", response.text)
    exit(1)

voices = response.json().get("voices", [])
print("Available ElevenLabs Voices:")
print("-" * 40)
for voice in voices:
    print(f"Name     : {voice['name']}")
    print(f"Voice ID : {voice['voice_id']}")
    print("-" * 40)
