# config.py
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["GROQ_API_KEY3"]  # fails fast if missing
