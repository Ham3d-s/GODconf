# config/logging_config.py
import logging
import logging.config
import os
import uuid
from contextvars import ContextVar

# متغیرهای زمینه برای نگهداری شناسه‌های منحصر به فرد در طول اجرای برنامه
# این شناسه‌ها به صورت خودکار به تمام لاگ‌ها اضافه می‌شوند.
run_id_var = ContextVar('run_id', default='main')
repo_id_var = ContextVar('repo_id', default='N/A')
file_id_var = ContextVar('file_id', default='N/A')

class ContextFilter(logging.Filter):
    """
    این فیلتر سفارشی، اطلاعات زمینه (run_id, repo_id, file_id) را
    به هر رکورد لاگ قبل از نمایش، تزریق می‌کند.
    """
    def filter(self, record):
        record.run_id = run_id_var.get()
        record.repo_id = repo_id_var.get()
        record.file_id = file_id_var.get()
        return True

class CustomConsoleFormatter(logging.Formatter):
    """فرمت‌بندی رنگی و خوانا برای لاگ‌های کنسول."""
    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: GREY + "%(asctime)s - %(levelname)s - %(message)s" + RESET,
        logging.INFO: BLUE + "INFO: %(message)s" + RESET,
        logging.WARNING: YELLOW + "WARN: %(message)s (%(name)s:%(lineno)d)" + RESET,
        logging.ERROR: RED + "ERROR: %(message)s (%(name)s:%(lineno)d)" + RESET,
        logging.CRITICAL: BOLD_RED + "CRITICAL: %(message)s (%(name)s:%(lineno)d)" + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging():
    """
    پیکربندی اصلی سیستم لاگینگ برنامه.
    این تابع یک شناسه منحصر به فرد برای هر اجرا (run_id) تولید کرده
    و دو نوع خروجی لاگ تعریف می‌کند: یکی برای کنسول (خوانا) و دیگری برای
    فایل (ساختاریافته و مناسب برای تحلیل).
    """
    run_id = str(uuid.uuid4()).split('-')[0]
    run_id_var.set(run_id)

    LOG_DIR = "reports"
    os.makedirs(LOG_DIR, exist_ok=True)

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context_filter": {
                "()": "config.logging_config.ContextFilter",
            }
        },
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(run_id)s %(repo_id)s %(file_id)s %(name)s %(lineno)d %(message)s"
            },
            "console": {
                "()": "config.logging_config.CustomConsoleFormatter",
            },
        },
        "handlers": {
            "json_file": {
                "class": "logging.FileHandler",
                "filename": os.path.join(LOG_DIR, f"run_{run_id}_structured.log"),
                "formatter": "json",
                "mode": "w",
                "encoding": "utf-8",
                "filters": ["context_filter"],
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
        },
        "root": {
            "handlers": ["json_file", "console"],
            "level": "INFO"
        },
    }

    logging.config.dictConfig(logging_config)
    logging.info(f"Logging configured successfully. Run ID: {run_id}")