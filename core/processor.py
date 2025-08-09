import hashlib
import logging
import os
import re
from typing import Dict, Any, List, Set, Tuple

from config.settings import settings
from services.github_service import GitHubService
from utils.helpers import _beautify_name
from config.logging_config import file_id_var, repo_id_var

logger = logging.getLogger(__name__)

class FileProcessor:
    """
    این کلاس مسئولیت پردازش یک فایل را بر عهده دارد. این فرآیند شامل
    دانلود محتوا، بررسی یکتا بودن از طریق هش، و تلاش برای دسته‌بندی
    آن با استفاده از قوانین Regex است.
    """
    def __init__(self, github_service: GitHubService, content_hashes: Set[str]):
        self.github_service = github_service
        self.content_hashes = content_hashes
        self.categorization_patterns = settings.get("categorization_patterns", [])

    def process_file(self, file_info: Dict, owner: str, repo: str, branch: str, repo_id: str) -> Tuple[Dict | None, Dict | None]:
        """
        یک فایل را پردازش می‌کند.
        
        خروجی:
            - یک تاپل (Tuple) شامل دو مقدار:
            1.  نتیجه دسته‌بندی Regex (در صورت موفقیت)
            2.  آیتم دسته‌بندی نشده برای ارسال به AI (در صورت شکست Regex)
        """
        repo_id_var.set(repo_id)
        
        file_path = file_info.get('path', '')
        if not file_path:
            return None, None
        
        file_id_var.set(file_path)
        logger.debug(f"Processing file: {file_path}")

        download_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
        
        content = self.github_service.download_file_content(download_url)
        if content is None:
            logger.warning(f"Skipping file due to download failure.")
            file_id_var.set('N/A')
            repo_id_var.set('N/A')
            return None, None

        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        if content_hash in self.content_hashes:
            logger.debug(f"Skipping duplicate content: {file_path}")
            file_id_var.set('N/A')
            repo_id_var.set('N/A')
            return None, None
        self.content_hashes.add(content_hash)

        repo_key_name = _beautify_name(repo)
        
        categorized_data, success = self._categorize_with_regex(download_url, file_path)
        
        file_id_var.set('N/A')
        repo_id_var.set('N/A')
        
        if success:
            # --- UX ENHANCEMENT: تغییر سطح لاگ از INFO به DEBUG برای کاهش شلوغی کنسول ---
            logger.debug(f"Successfully categorized by Regex: {file_path}")
            return {"repo_key": repo_key_name, "data": categorized_data}, None
        else:
            logger.debug(f"Regex did not match, passing to AI queue: {file_path}")
            categorized_data["repo_key"] = repo_key_name
            return None, categorized_data

    def _categorize_with_regex(self, link: str, file_path: str) -> Tuple[Dict[str, Any], bool]:
        """
        منطق دسته‌بندی مبتنی بر الگوهای Regex تعریف شده در config.json.
        """
        filename_raw = os.path.basename(file_path)
        filename_clean = _beautify_name(os.path.splitext(filename_raw)[0])
        format_type = "Base64" if "base64" in filename_raw.lower() else "Plain-Text"

        for pattern_def in self.categorization_patterns:
            match = re.search(pattern_def["regex"], file_path, re.IGNORECASE)
            if match:
                groups = match.groups()
                category_path = [pattern_def["name"]]
                category_path.extend(_beautify_name(g) for g in groups if g)

                if pattern_def["name"] == "Daily Archives" and groups:
                    try:
                        date_str = groups[0]
                        year = "20" + date_str[:2]
                        month_num = int(date_str[2:])
                        from datetime import datetime
                        month_name = datetime(int(year), month_num, 1).strftime('%B')
                        category_path[1] = f"{year}-{month_name}"
                    except (ValueError, IndexError):
                        pass

                category_path.append(format_type)
                
                final_dict = current_level = {}
                for part in category_path:
                    current_level = current_level.setdefault(part, {})
                current_level[filename_clean] = link
                
                return final_dict, True

        return {"link": link, "file_path": file_path}, False
