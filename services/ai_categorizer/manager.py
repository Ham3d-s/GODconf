import logging
import time
import os
from typing import List, Dict

from openai import APIError, RateLimitError

from config.settings import settings
from utils.helpers import _beautify_name
from .base_provider import AIProvider
from .google_ai import GoogleAIProvider
from .open_router import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

class AICategorizer:
    """
    این کلاس ارکستریتور اصلی برای دسته‌بندی با هوش مصنوعی است.
    این کلاس ارائه‌دهندگان مختلف را مدیریت کرده و در صورت شکست یکی،
    به سراغ دیگری می‌رود (Fallback).
    """
    def __init__(self):
        self.providers: List[AIProvider] = self._initialize_providers()
        if not self.providers:
            logger.warning("No valid AI providers found. AI categorizer will be disabled.")
        else:
            provider_names = ", ".join(p.name for p in self.providers)
            logger.info(f"AI Categorizer enabled with providers: {provider_names}")

    def _initialize_providers(self) -> List[AIProvider]:
        providers = []
        providers_config = settings.get("providers_config", [])
        
        for config in providers_config:
            api_key_env_name = config['api_key_env']
            api_key = settings.get_api_key(api_key_env_name)
            
            if api_key:
                try:
                    provider_type = config.get("type")
                    if provider_type == "openai_compatible":
                        providers.append(OpenAICompatibleProvider(
                            name=config["name"], 
                            api_key=api_key,
                            **config["config"]
                        ))
                    elif provider_type == "google_ai":
                        providers.append(GoogleAIProvider(
                            name=config["name"], 
                            api_key=api_key,
                            **config["config"]
                        ))
                    logger.info(f"Successfully initialized provider: {config['name']}")
                except Exception as e:
                    logger.error(f"Failed to initialize provider '{config['name']}': {e}")
            else:
                logger.warning(f"API key for '{config['name']}' ({api_key_env_name}) not found in .env file. Skipping.")

        return providers
    
    def is_enabled(self) -> bool:
        return bool(self.providers)

    def batch_categorize(self, items: List[Dict]) -> List[Dict]:
        """
        لیستی از آیتم‌ها را دریافت کرده و با استفاده از مکانیزم تلاش مجدد و جایگزین،
        آن‌ها را دسته‌بندی می‌کند.
        """
        if not self.is_enabled() or not items:
            return []
        
        logger.info(f"Starting stateful AI processing for {len(items)} items...")
        remaining_items = list(items)
        all_categorized_items = []

        for provider in self.providers:
            if not remaining_items:
                break

            logger.info(f"--- Using Provider: {provider.name} for {len(remaining_items)} remaining items ---")
            
            successfully_processed_links = set()
            chunk_size = settings.get('ai_chunk_size', 50)

            for i in range(0, len(remaining_items), chunk_size):
                chunk = remaining_items[i : i + chunk_size]
                
                # --- FIX: به جای `_process_chunk_recursively` از متد امن‌تر جدید استفاده می‌کنیم ---
                categorized_chunk = self._process_chunk_with_fallback(provider, chunk)
                
                if categorized_chunk:
                    if len(categorized_chunk) == len(chunk):
                        for original_item, categorized_item in zip(chunk, categorized_chunk):
                            categorized_item['repo_key'] = original_item.get('repo_key')
                            successfully_processed_links.add(original_item['link'])
                        all_categorized_items.extend(categorized_chunk)
                    else:
                        logger.warning(
                            f"Provider '{provider.name}' returned a mismatched number of items. "
                            f"Expected {len(chunk)}, got {len(categorized_chunk)}. Skipping this chunk."
                        )

            if successfully_processed_links:
                remaining_items = [item for item in remaining_items if item['link'] not in successfully_processed_links]

        if remaining_items:
            logger.error(f"{len(remaining_items)} items could not be categorized by any provider. Moving to fallback.")
            all_categorized_items.extend(self._build_fallback_items(remaining_items))
            
        return all_categorized_items

    def _process_chunk_with_fallback(self, provider: AIProvider, chunk: List[Dict], max_depth=3) -> List[Dict]:
        """
        --- NEW & SAFER METHOD ---
        یک chunk را پردازش می‌کند. در صورت خطای مربوط به حجم ورودی، آن را به صورت بازگشتی
        و تا یک عمق مشخص نصف می‌کند تا از حلقه‌های بی‌نهایت جلوگیری شود.
        """
        if not chunk:
            return []
        
        try:
            return provider.process_chunk(chunk)
        except (RateLimitError, APIError) as e:
            # بررسی می‌کنیم که آیا خطا مربوط به حجم ورودی است یا خیر
            is_input_too_large = (
                isinstance(e, APIError) and
                (e.status_code == 422 or (e.body and "tokens" in str(e.body).lower()))
            )

            if is_input_too_large and max_depth > 0:
                logger.warning(f"Input too large for '{provider.name}'. Splitting chunk (depth {max_depth}).")
                mid_point = len(chunk) // 2
                
                # اگر chunk قابل نصف شدن نباشد، شکست می‌خوریم
                if mid_point == 0:
                    logger.error(f"Cannot split chunk of size {len(chunk)} any further. Failing this item.")
                    return []
                
                # پردازش دو نیمه به صورت بازگشتی با کاهش عمق
                processed_a = self._process_chunk_with_fallback(provider, chunk[:mid_point], max_depth - 1)
                processed_b = self._process_chunk_with_fallback(provider, chunk[mid_point:], max_depth - 1)
                return processed_a + processed_b
            
            # برای سایر خطاهای API یا رسیدن به حداکثر عمق بازگشت، شکست می‌خوریم
            logger.error(f"Unhandled API Error for '{provider.name}' or max recursion depth reached: {e}. Failing chunk.")
            return []
        except Exception as e:
            # برای هر خطای پیش‌بینی نشده دیگر
            logger.error(f"An unexpected exception occurred with provider '{provider.name}': {e}. Failing chunk.")
            return []

    def _build_fallback_items(self, items: List[Dict]) -> List[Dict]:
        """
        برای آیتم‌هایی که توسط هیچ ارائه‌دهنده‌ای پردازش نشده‌اند، یک ساختار پیش‌فرض می‌سازد.
        """
        fallback_items = []
        for item in items:
            fallback_items.append({
                "category": "AI Failed - Uncategorized",
                "sub_category": "General",
                "name": _beautify_name(os.path.splitext(os.path.basename(item["file_path"]))[0]),
                "link": item["link"],
                "repo_key": item.get("repo_key")
            })
        return fallback_items
