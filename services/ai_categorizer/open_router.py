from typing import List, Dict, Any, Set
from openai import OpenAI, NotFoundError, APIError, BadRequestError
from .base_provider import AIProvider

class OpenAICompatibleProvider(AIProvider):
    """
    --- FINAL ARCHITECTURE v3 ---
    - دارای حافظه داخلی برای به خاطر سپردن مدل‌های ناموفق در طول يک اجرا.
    - کاملاً داده-محور و تطبیق‌پذیر با کانفیگ.
    """
    def __init__(self, name: str, base_url: str, api_key: str, models: List[Dict], 
                 routing: Dict[str, Any] = None, model_filters: Dict[str, Any] = None, 
                 max_tokens: int = 4096, **kwargs):
        super().__init__(name)
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=180.0)
        self.routing_options = routing or {}
        self.default_max_tokens = max_tokens
        
        self.candidate_models = self._filter_models(models, model_filters or {})
        
        # --- FIX: حافظه برای مدل‌های ناموفق ---
        self.unavailable_models: Set[str] = set()
        
        if self.candidate_models:
            model_names = [m['name'] for m in self.candidate_models]
            self.logger.info(
                f"Provider '{self.name}' initialized with {len(self.candidate_models)} candidate models: {model_names}"
            )
        else:
            self.logger.warning(f"Provider '{self.name}': No models matched filters. This provider will be skipped.")

    def _filter_models(self, models: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        filtered_list = list(models)
        
        if filters.get("tier"):
            filtered_list = [m for m in filtered_list if m.get("tier") == filters["tier"]]
        if filters.get("min_context_window"):
            filtered_list = [m for m in filtered_list if m.get("context_window", 0) >= filters["min_context_window"]]
        if filters.get("supports_json"):
            filtered_list = [m for m in filtered_list if m.get("supports_json") is True]
            
        return filtered_list

    def process_chunk(self, chunk: List[Dict]) -> List[Dict]:
        if not self.candidate_models:
            return []

        prompt = self._get_prompt(chunk, enforce_json_output=True)
        
        available_models = [m for m in self.candidate_models if m['name'] not in self.unavailable_models]
        if not available_models:
            self.logger.error("No available models left to try for this provider.")
            return []

        for model_info in available_models:
            model_name = model_info['name']
            self.logger.info(f"Attempting chunk with model: {model_name}")
            
            model_max_output = model_info.get('max_output', self.default_max_tokens)
            safe_max_tokens = min(self.default_max_tokens, model_max_output)

            request_params = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "max_tokens": safe_max_tokens
            }

            base_url_str = str(self.client.base_url)
            provider_opts = {}
            if "openrouter" in base_url_str and self.routing_options:
                if self.routing_options.get('strategy') == 'sort' and self.routing_options.get('sort_by'):
                    provider_opts['sort'] = self.routing_options['sort_by']
                if 'allow_fallbacks' in self.routing_options:
                    provider_opts['allow_fallbacks'] = self.routing_options['allow_fallbacks']
            
            if provider_opts:
                request_params["extra_body"] = {"provider": provider_opts}

            try:
                response = self.client.chat.completions.create(**request_params)
                
                if response.choices and response.choices[0].message and response.choices[0].message.content:
                    if hasattr(response, 'model'):
                        self.logger.info(f"API provider successfully used '{response.model}' for this request.")
                    response_text = response.choices[0].message.content
                    
                    result = self._extract_json_from_response(response_text)
                    if len(result) == len(chunk):
                        return result
                    else:
                        self.logger.warning(
                            f"Model '{model_name}' returned a mismatched number of items. "
                            f"Expected {len(chunk)}, got {len(result)}. Trying next model..."
                        )
                        continue
                else:
                    self.logger.warning(f"Received an empty response from model: {model_name}. Trying next model...")
                    continue

            except (NotFoundError, BadRequestError) as e:
                self.logger.warning(f"Model '{model_name}' failed permanently for this run: {e.__class__.__name__}. Marking as unavailable.")
                self.unavailable_models.add(model_name)
                continue
            
            except APIError as e:
                self.logger.error(f"A general API error occurred with model '{model_name}': {e.__class__.__name__}")
                raise e

        self.logger.error(f"All available candidate models failed for this chunk.")
        return []
