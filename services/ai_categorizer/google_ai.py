# services/ai_categorizer/google_ai.py
from typing import List, Dict
import google.generativeai as genai
from .base_provider import AIProvider

class GoogleAIProvider(AIProvider):
    def __init__(self, name: str, api_key: str, model_name: str):
        super().__init__(name)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.logger.info(f"GoogleAI provider '{self.name}' initialized with model: {model_name}")

    def process_chunk(self, chunk: List[Dict]) -> List[Dict]:
        self.logger.info(f"Processing chunk of {len(chunk)} items with model: {self.model.model_name}")
        prompt = self._get_prompt(chunk)
        
        try:
            response = self.model.generate_content(prompt)
            # --- FIX: اضافه کردن بلاک کدنویسی دفاعی ---
            if response and response.text:
                return self._extract_json_from_response(response.text)
            else:
                self.logger.warning(f"Received an empty response from model: {self.model.model_name}. Skipping chunk.")
                return []
        except Exception as e:
            self.logger.error(f"Error during content generation with GoogleAI: {e}")
            return []