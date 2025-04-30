import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load Gemini API key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# List available models and their supported methods
print("Available Gemini Models and Supported Methods:")
print("=" * 50)
models = genai.list_models()
for m in models:
    print(f"Model Name: {m.name}")
    print(f"Supported Methods: {m.supported_generation_methods}")
    print("-" * 50)
