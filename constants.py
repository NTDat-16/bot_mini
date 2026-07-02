from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
LOGS_DIR = BASE_DIR / "logs"
STATE_PATH = LOGS_DIR / "state.json"
LAST_RUN_PATH = LOGS_DIR / "last_run.json"

BASE_URL = "https://support.optisigns.com"
ARTICLES_API_URL = f"{BASE_URL}/api/v2/help_center/en-us/articles.json"
DEFAULT_TIMEOUT = 20
HEADERS = {
    "User-Agent": "OptiSignsDocsBot/1.0 (+https://support.optisigns.com)"
}

ASSISTANT_NAME = "OptiBot Mini Clone"
SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_VECTOR_STORE_ID_ENV = "OPENAI_VECTOR_STORE_ID"
OPENAI_ASSISTANT_ID_ENV = "OPENAI_ASSISTANT_ID"
DEFAULT_MODEL = "gpt-4.1-mini"
