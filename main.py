# main.py
import logging
import time

from config.logging_config import setup_logging
from config.settings import settings
from core.scanner import GitHubScanner, ScanResults
from reporting.aggregator import ReportAggregator
from services.ai_categorizer.manager import AICategorizer
from services.github_service import GitHubService

# راه‌اندازی سیستم لاگینگ هوشمند در همان ابتدای برنامه
setup_logging()

def main():
    start_time = time.time()
    
    # 1. تزریق وابستگی‌ها: ساختن سرویس‌ها و ماژول‌ها
    github_service = GitHubService()
    ai_categorizer = AICategorizer()
    
    # -- FIX: آرگومان ai_categorizer از اینجا حذف شد --
    scanner = GitHubScanner(github_service) 
    
    aggregator = ReportAggregator()

    # 2. اجرای مرحله جمع‌آوری داده
    logging.info("--- Starting Stage 1: Data Collection ---")
    if not settings.repo_urls:
        logging.critical("Repository list is empty. Exiting.")
        return
    
    scan_results: ScanResults = scanner.run_scan(settings.repo_urls)

    # 3. اجرای مرحله پردازش با هوش مصنوعی
    logging.info("--- Starting Stage 2: AI Processing ---")
    ai_results = ai_categorizer.batch_categorize(scan_results.uncategorized_items)

    execution_time = time.time() - start_time

    # 4. اجرای مرحله تجمیع و گزارش‌دهی
    logging.info("--- Starting Stage 3: Aggregation & Reporting ---")
    aggregator.process_and_generate_reports(
        regex_items=scan_results.regex_categorized_items,
        ai_items=ai_results,
        scan_stats=scan_results.repo_scan_stats,
        total_files=scan_results.total_files_analyzed,
        execution_time=execution_time
    )

    logging.info(f"--- Process Complete in {execution_time:.2f} seconds ---")

if __name__ == "__main__":
    main()