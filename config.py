import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.environ["DISCORD_TOKEN"]
ALLOWED_GUILD_ID: int = int(os.environ["ALLOWED_GUILD_ID"])
ALLOWED_CHANNEL_ID: int = int(os.environ["ALLOWED_CHANNEL_ID"])
UNITY_PROJECT_PATH: str = os.environ["UNITY_PROJECT_PATH"]
CLAUDE_PATH: str = os.environ.get("CLAUDE_PATH", "claude")
