import concurrent.futures
import logging
import os
import time
from typing import List, Set
from dataclasses import dataclass, field

from tqdm import tqdm

from config.logging_config import repo_id_var
from config.settings import settings
from core.fetcher import RepoFetcher
from core.processor import FileProcessor
from services.github_service import GitHubService
from utils.helpers import parse_github_url

logger = logging.getLogger(__name__)

@dataclass
class ScanResults:
    """یک کلاس داده برای نگهداری نتایج خروجی اسکن."""
    regex_categorized_items: list = field(default_factory=list)
    uncategorized_items: list = field(default_factory=list)
    repo_scan_stats: list = field(default_factory=list)
    total_files_analyzed: int = 0
    
class GitHubScanner:
    """
    ارکستریتور اصلی فرآیند اسکن.
    """
    def __init__(self, github_service: GitHubService):
        self.fetcher = RepoFetcher(github_service)
        self.github_service = github_service
        self.content_hashes: Set[str] = set()

    def _is_potential_config_file(self, file_path: str) -> bool:
        """
        بررسی می‌کند که آیا یک فایل پتانسیل داشتن کانفیگ را دارد یا خیر.
        """
        file_path_lower = file_path.lower()
        
        if any(file_path_lower.endswith(ext) for ext in settings.get('ignored_extensions', [])):
            return False
        
        if any(keyword.lower() in file_path_lower for keyword in settings.get('keyword_blacklist', [])):
            return False

        if any(file_path_lower.endswith(ext) for ext in settings.get('allowed_extensions', [])):
            return True
            
        if '.' not in os.path.basename(file_path):
            return True
            
        return False

    def run_scan(self, repo_urls: List[str]) -> ScanResults:
        """
        لیستی از URL های ریپازیتوری را اسکن کرده و نتایج را برمی‌گرداند.
        """
        results = ScanResults()

        for repo_url in repo_urls:
            repo_start_time = time.time()
            owner, repo_name = parse_github_url(repo_url)
            if not owner or not repo_name:
                logger.warning(f"Skipping invalid GitHub URL: {repo_url}")
                continue

            repo_id = f"{owner}/{repo_name}"
            repo_id_var.set(repo_id)
            logger.info(f"--- Starting scan for repository: {repo_id} ---")

            files, branch_name = self.fetcher.fetch_files(owner, repo_name)
            if not files:
                logger.error("Could not fetch file tree. Skipping repository.")
                results.repo_scan_stats.append({"repo": repo_id, "status": "Failed", "time": 0, "files_analyzed": 0})
                repo_id_var.set('N/A')
                continue

            potential_files = [f for f in files if f.get('type') == 'blob' and self._is_potential_config_file(f.get('path', ''))]
            num_potential_files = len(potential_files)
            logger.info(f"Found {num_potential_files} potential config files to analyze.")
            results.total_files_analyzed += num_potential_files
            
            processor = FileProcessor(self.github_service, self.content_hashes)

            repo_regex_success_count = 0
            repo_ai_queued_count = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.get('max_workers', 10)) as executor:
                future_to_file = {
                    executor.submit(processor.process_file, f, owner, repo_name, branch_name, repo_id): f 
                    for f in potential_files
                }
                
                progress_desc = f"🧠 Analyzing {repo_name.ljust(20)}"
                progress = tqdm(concurrent.futures.as_completed(future_to_file), total=num_potential_files, desc=progress_desc, unit="file")
                
                for future in progress:
                    regex_result, ai_item = future.result()
                    if regex_result:
                        results.regex_categorized_items.append(regex_result)
                        repo_regex_success_count += 1
                    if ai_item:
                        results.uncategorized_items.append(ai_item)
                        repo_ai_queued_count += 1

            scan_duration = time.time() - repo_start_time
            # --- FIX: اضافه کردن تعداد فایل‌های تحلیل شده به آمار هر ریپازیتوری ---
            results.repo_scan_stats.append({
                "repo": repo_id,
                "status": "Success",
                "time": scan_duration,
                "files_analyzed": num_potential_files,
                "regex_success_count": repo_regex_success_count,
                "ai_total_items": repo_ai_queued_count
            })
            
            logger.info(
                f"Scan for {repo_id} finished in {scan_duration:.2f}s. "
                f"Results: {repo_regex_success_count} categorized by Regex, "
                f"{repo_ai_queued_count} queued for AI."
            )
            
            repo_id_var.set('N/A')

        return results
