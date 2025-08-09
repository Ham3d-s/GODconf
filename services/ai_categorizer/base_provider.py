import json
import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict

class AIProvider(ABC):
    """
    یک کلاس پایه انتزاعی (Interface) که ساختار تمام ارائه‌دهندگان
    هوش مصنوعی را تعریف می‌کند.
    """
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"AIProvider.{self.name}")

    @abstractmethod
    def process_chunk(self, chunk: List[Dict]) -> List[Dict]:
        """این متد باید توسط کلاس‌های فرزند پیاده‌سازی شود."""
        pass

    def _get_prompt(self, chunk: List[Dict], enforce_json_output: bool = True) -> str:
        """
        --- FINAL ARCHITECTURE: ADVANCED PROMPT ENGINEERING ---
        این پرامپت با استفاده از تکنیک‌های Few-Shot Learning و تعریف Taxonomy،
        مدل را برای ارائه خروجی دقیق، ساختاریافته و سازگار، راهنمایی می‌کند.
        """
        items_to_send = [{"link": item["link"], "file_path": item["file_path"]} for item in chunk]
        items_json_string = json.dumps(items_to_send, indent=2, ensure_ascii=False)

        prompt = f"""
You are an expert file categorizer. Your task is to analyze a list of file paths and categorize them into a structured hierarchy.

**1. TAXONOMY (Allowed Categories):**
You MUST use the following primary categories. Do not invent new ones.
- **Subscriptions:** For general subscription links.
- **Configs:** For specific application configuration files (not subscription links).
- **Utilities:** For scripts, workflows, documentation, or other non-config files.
- **Geolocation:** For files categorized by country or region.

**2. EXAMPLES (Few-Shot Learning):**
Here is how you should categorize different file paths:

- **Example 1 (Subscription by Protocol):**
  - Input: `{{"link": "...", "file_path": "subscriptions/xray/normal/vless"}}`
  - Output: `{{"category": "Subscriptions", "sub_category": "Vless", "name": "Vless", "link": "..."}}`

- **Example 2 (GitHub Workflow):**
  - Input: `{{"link": "...", "file_path": ".github/workflows/speedtest.yml"}}`
  - Output: `{{"category": "Utilities", "sub_category": "GitHub Actions", "name": "Speedtest Workflow", "link": "..."}}`

- **Example 3 (Geolocation):**
  - Input: `{{"link": "...", "file_path": "Countries/United_States.txt"}}`
  - Output: `{{"category": "Geolocation", "sub_category": "North America", "name": "United States", "link": "..."}}`

- **Example 4 (Specific Config File):**
  - Input: `{{"link": "...", "file_path": "templates/clash.yaml"}}`
  - Output: `{{"category": "Configs", "sub_category": "Clash", "name": "Clash Template", "link": "..."}}`

**3. RULES AND GUIDELINES:**
- Your response MUST be a single, valid JSON object.
- The JSON object must contain ONE key: "categorized_items".
- The value of "categorized_items" MUST be a JSON array.
- You MUST return an object for EVERY item in the input list. The output array length must exactly match the input array length.
- The "name" field should be a clean, human-readable version of the file name, without the extension.
- Be concise. Do not create overly nested sub-categories. Stick to the taxonomy.

**4. LIST TO CATEGORIZE:**
{items_json_string}
"""
        if enforce_json_output:
            prompt += "\nIMPORTANT: Your final output must be ONLY the JSON object, with no additional text before or after."
        return prompt

    def _extract_json_from_response(self, text: str) -> List[Dict]:
        if not text:
            self.logger.warning("Received empty text for JSON extraction.")
            return []
        
        try:
            match = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.DOTALL)
            if match:
                clean_json_str = match.group(1).strip()
            else:
                start_index = text.find('{')
                end_index = text.rfind('}')
                if start_index != -1 and end_index != -1 and end_index > start_index:
                    clean_json_str = text[start_index : end_index + 1]
                else:
                    self.logger.error(f"Could not find a valid JSON structure in the response: {text[:250]}...")
                    return []

            data = json.loads(clean_json_str)
            items = data.get("categorized_items")

            if isinstance(items, list) and all(isinstance(i, dict) for i in items):
                return items
            
            self.logger.warning(f"Parsed JSON but 'categorized_items' key is not a valid list. Response: {text[:250]}...")
            return []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from cleaned string. Content (first 300 chars): {clean_json_str[:300]}...")
            return []
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during JSON extraction: {e}")
            return []
