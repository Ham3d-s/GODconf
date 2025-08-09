# config/settings.py
import json
import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AppSettings:
    def __init__(self, config_path: str = 'config.json', repo_path: str = 'repos.txt'):
        self.config: Dict[str, Any] = self._load_json_config(config_path)
        self.repo_urls: List[str] = self._load_repo_list(repo_path)
        
        # کلیدهای API مستقیماً از متغیرهای محیطی خوانده می‌شوند
        self._api_keys: Dict[str, str | None] = {
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
            "TOGETHER_API_KEY": os.getenv("TOGETHER_API_KEY"),
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        }
        
        if self._api_keys["GITHUB_TOKEN"]:
            logger.info("GITHUB_TOKEN loaded successfully.")
        else:
            logger.warning("GITHUB_TOKEN not found in .env file.")

        logger.info("Application settings loaded.")

    def _load_json_config(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                logger.debug(f"Loading JSON configuration from {path}")
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.critical(f"FATAL: Could not load or parse {path}. Error: {e}")
            exit(1)

    def _load_repo_list(self, path: str) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            logger.info(f"Found {len(urls)} repositories in {path} to scan.")
            return urls
        except FileNotFoundError:
            logger.critical(f"FATAL: Repository list file not found at {path}.")
            return []

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def get_api_key(self, key_name: str) -> str | None:
        """
        یک متد امن و صریح برای دریافت کلید API از متغیرهای محیطی بارگذاری شده.
        """
        return self._api_keys.get(key_name)

settings = AppSettings()