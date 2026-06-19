import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
PROXY_URL: str = os.getenv("PROXY_URL") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or ""
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
MASTER_USERNAME: str = os.getenv("MASTER_USERNAME", "@master")
CARD_NUMBER: str = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
PHONE_SBP: str = os.getenv("PHONE_SBP", "+7 (000) 000-00-00")
BANK_NAME: str = os.getenv("BANK_NAME", "Сбербанк")
RECIPIENT_NAME: str = os.getenv("RECIPIENT_NAME", "Татьяна Б.")

DB_PATH: str = os.path.join(os.getenv("DATA_DIR", "/data" if os.path.isdir("/data") else "."), "bot.db")
