import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError("Missing GEMINI_API_KEY in environment variables")

genai.configure(api_key=API_KEY)

# Constants
MAX_TOKEN_LENGTH = 8000
CACHE_EXPIRY = 120  # 2 minutes in seconds
VERSION = "1.0.3"

# Define the root directory for storing files
ROOT_DIR = Path("src/data")

# List of required directories inside ROOT_DIR
REQUIRED_DIRS = [
    "resumes",
    "cover_letters",
    "cache",
    "qna_responses",
    "templates",
    "generated_resumes"
]

# Create necessary directories
for dir_name in REQUIRED_DIRS:
    (ROOT_DIR / dir_name).mkdir(parents=True, exist_ok=True)
