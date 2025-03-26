import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError("Missing GEMINI_API_KEY in environment variables")

genai.configure(api_key=API_KEY)

# Constants
MAX_TOKEN_LENGTH = 8000
CACHE_EXPIRY = 60  # 1 minute in seconds

# Create necessary directories
REQUIRED_DIRS = [
    "resumes",
    "cover_letters",
    "cache",
    "qna_responses",
    "templates",
    "generated_resumes"
]

for dir_name in REQUIRED_DIRS:
    os.makedirs(dir_name, exist_ok=True)