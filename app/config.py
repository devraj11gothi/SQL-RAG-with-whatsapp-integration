import os

from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.environ["MYSQL_HOST"]
MYSQL_PORT = int(os.environ["MYSQL_PORT"])
MYSQL_USER = os.environ["MYSQL_USER"]
MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
MYSQL_DB = os.environ["MYSQL_DB"]

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "lmstudio")  # "lmstudio" or "gemini"

LMSTUDIO_BASE_URL = os.environ["LMSTUDIO_BASE_URL"]
LMSTUDIO_MODEL = os.environ["LMSTUDIO_MODEL"]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = os.environ.get(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
)

LLM_TIMEOUT_S = int(os.environ["LLM_TIMEOUT_S"])

MAX_ROW_LIMIT = int(os.environ["MAX_ROW_LIMIT"])
