"""Integration with ML models for advanced anonymization."""

import json
import base64
import httpx
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ML_CONFIG


@dataclass
class MLResponse:
    """Response from ML model."""
    success: bool
    content: str = ""
    error: str = ""
    raw_response: dict = None


class MLIntegration:
    """Integration with ML models for text and image analysis."""
    
    def __init__(self):
        self.gpt_host = ML_CONFIG["gpt"]["host"]
        self.gpt_model = ML_CONFIG["gpt"]["model"]
        self.vision_host = ML_CONFIG["vision"]["host"]
        self.vision_model = ML_CONFIG["vision"]["model"]
        self.timeout = ML_CONFIG["timeout"]
    
    async def detect_companies_gpt(self, text: str) -> list[str]:
        """
        Use GPT to detect company names in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected company names
        """
        prompt = f"""Найди в тексте все названия компаний и организаций, даже если они без ООО/АО.
Верни только JSON в формате: {{"companies": ["название1", "название2"]}}
Если компаний нет, верни: {{"companies": []}}

Текст:
{text[:4000]}"""  # Limit text length

        response = await self._call_gpt(prompt)
        
        if response.success:
            try:
                data = json.loads(response.content)
                return data.get("companies", [])
            except json.JSONDecodeError:
                return []
        
        return []
    
    async def detect_personal_data_gpt(self, text: str) -> dict[str, list[str]]:
        """
        Use GPT to detect personal data in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with detected personal data
        """
        prompt = f"""Найди в тексте все персональные данные:
- ФИО людей
- Должности
- Email адреса
- Номера телефонов

Верни только JSON в формате:
{{
    "names": ["ФИО1", "ФИО2"],
    "positions": ["должность1"],
    "emails": ["email1"],
    "phones": ["телефон1"]
}}

Текст:
{text[:4000]}"""

        response = await self._call_gpt(prompt)
        
        if response.success:
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                return {"names": [], "positions": [], "emails": [], "phones": []}
        
        return {"names": [], "positions": [], "emails": [], "phones": []}
    
    async def detect_prices_gpt(self, text: str) -> list[str]:
        """
        Use GPT to detect prices and monetary values in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected price strings
        """
        prompt = f"""Найди в тексте все упоминания цен, стоимости, сумм, бюджетов.
Включи как явные числа с валютой, так и словесные описания ("несколько миллионов", "около 100 тысяч").

Верни только JSON в формате: {{"prices": ["цена1", "цена2"]}}

Текст:
{text[:4000]}"""

        response = await self._call_gpt(prompt)
        
        if response.success:
            try:
                data = json.loads(response.content)
                return data.get("prices", [])
            except json.JSONDecodeError:
                return []
        
        return []
    
    async def detect_technical_details_gpt(self, text: str) -> list[str]:
        """
        Use GPT to detect product names and technical details.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected product/technology names
        """
        prompt = f"""Найди в тексте все названия:
- Программных продуктов
- Сервисов и платформ
- Технологий и фреймворков
- Версий программного обеспечения

Верни только JSON в формате: {{"products": ["продукт1", "продукт2"]}}

Текст:
{text[:4000]}"""

        response = await self._call_gpt(prompt)
        
        if response.success:
            try:
                data = json.loads(response.content)
                return data.get("products", [])
            except json.JSONDecodeError:
                return []
        
        return []
    
    async def is_logo_image(self, image_data: bytes) -> bool:
        """
        Use Qwen3VL to determine if an image is a company logo.
        
        Args:
            image_data: Image as bytes
            
        Returns:
            True if the image appears to be a logo
        """
        prompt = "Является ли это изображение логотипом компании или организации? Ответь только одним словом: да или нет"
        
        response = await self._call_vision(prompt, image_data)
        
        if response.success:
            answer = response.content.lower().strip()
            return answer in ["да", "yes", "true", "1"]
        
        return False
    
    async def has_watermark(self, image_data: bytes) -> bool:
        """
        Use Qwen3VL to detect watermarks in an image.
        
        Args:
            image_data: Image as bytes
            
        Returns:
            True if a watermark is detected
        """
        prompt = "Есть ли на этом изображении водяной знак, полупрозрачный текст или логотип поверх основного содержимого? Ответь только: да или нет"
        
        response = await self._call_vision(prompt, image_data)
        
        if response.success:
            answer = response.content.lower().strip()
            return answer in ["да", "yes", "true", "1"]
        
        return False
    
    async def ocr_image(self, image_data: bytes) -> str:
        """
        Use Qwen3VL to perform OCR on an image.
        
        Args:
            image_data: Image as bytes
            
        Returns:
            Extracted text from the image
        """
        prompt = "Распознай и верни весь текст, который виден на этом изображении. Верни только текст, без комментариев."
        
        response = await self._call_vision(prompt, image_data)
        
        return response.content if response.success else ""
    
    async def validate_anonymization(self, text: str) -> dict:
        """
        Use GPT to validate that text is properly anonymized.
        
        Args:
            text: Anonymized text to validate
            
        Returns:
            Dictionary with validation results
        """
        prompt = f"""Проверь текст на наличие конфиденциальной информации:
- Названия реальных компаний (не "Компания 1", "Компания 2")
- ФИО людей (не "Контактное лицо 1")
- Реальные цены и суммы (не "0 ₽")
- Адреса и географические данные
- Телефоны и email
- ИНН, ОГРН, банковские реквизиты
- Даты (не "Дата 1", "Дата 2")

Если найдена конфиденциальная информация, верни JSON:
{{"found": true, "items": ["описание найденного 1", "описание найденного 2"]}}

Если всё обезличено корректно, верни:
{{"found": false, "items": []}}

Текст для проверки:
{text[:4000]}"""

        response = await self._call_gpt(prompt)
        
        if response.success:
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                return {"found": False, "items": [], "error": "Invalid JSON response"}
        
        return {"found": False, "items": [], "error": response.error}
    
    async def _call_gpt(self, prompt: str) -> MLResponse:
        """Make a call to the GPT model."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"http://{self.gpt_host}/v1/chat/completions",
                    json={
                        "model": self.gpt_model,
                        "messages": [
                            {"role": "system", "content": "Ты — полезный и краткий помощник."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 512,
                        "temperature": 0.0
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return MLResponse(success=True, content=content, raw_response=data)
                else:
                    return MLResponse(
                        success=False, 
                        error=f"HTTP {response.status_code}: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            return MLResponse(success=False, error="Request timeout")
        except httpx.ConnectError:
            return MLResponse(success=False, error="Connection failed - ML model unavailable")
        except Exception as e:
            return MLResponse(success=False, error=str(e))
    
    async def _call_vision(self, prompt: str, image_data: bytes) -> MLResponse:
        """Make a call to the vision model with an image."""
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"http://{self.vision_host}/v1/chat/completions",
                    json={
                        "model": self.vision_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{image_base64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 512,
                        "temperature": 0.0
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return MLResponse(success=True, content=content, raw_response=data)
                else:
                    return MLResponse(
                        success=False, 
                        error=f"HTTP {response.status_code}: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            return MLResponse(success=False, error="Request timeout")
        except httpx.ConnectError:
            return MLResponse(success=False, error="Connection failed - Vision model unavailable")
        except Exception as e:
            return MLResponse(success=False, error=str(e))
    
    def is_available(self) -> dict[str, bool]:
        """Check if ML models are available (synchronous check)."""
        import socket
        
        results = {"gpt": False, "vision": False}
        
        # Check GPT
        try:
            host, port = self.gpt_host.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, int(port)))
            results["gpt"] = result == 0
            sock.close()
        except Exception:
            pass
        
        # Check Vision
        try:
            host, port = self.vision_host.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, int(port)))
            results["vision"] = result == 0
            sock.close()
        except Exception:
            pass
        
        return results
    
    def ask_gpt(self, prompt: str, max_retries: int = 3) -> tuple[str, str]:
        """
        Synchronous call to GPT model with retries.
        
        Returns:
            tuple: (response_text, error_message)
            If successful, error_message is empty.
            If failed, response_text is empty and error_message contains details.
        """
        import requests
        import time
        
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                # Exponential backoff
                if attempt > 0:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                
                response = requests.post(
                    f"http://{self.gpt_host}/v1/chat/completions",
                    json={
                        "model": self.gpt_model,
                        "messages": [
                            {"role": "system", "content": "Ты — полезный и краткий помощник. Отвечай только JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2048,
                        "temperature": 0.0
                    },
                    timeout=120  # 2 minutes per attempt
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    if content and len(content) > 5:
                        return content, ""
                    else:
                        last_error = f"Пустой ответ от GPT (попытка {attempt + 1})"
                elif response.status_code == 429:
                    last_error = f"GPT перегружен (429), попытка {attempt + 1}/{max_retries}"
                elif response.status_code >= 500:
                    last_error = f"Ошибка сервера GPT ({response.status_code}), попытка {attempt + 1}/{max_retries}"
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    break  # Don't retry on client errors
                    
            except requests.exceptions.Timeout:
                last_error = f"Таймаут GPT (попытка {attempt + 1}/{max_retries})"
            except requests.exceptions.ConnectionError:
                last_error = f"GPT недоступен (попытка {attempt + 1}/{max_retries})"
            except Exception as e:
                last_error = f"Ошибка: {str(e)[:50]} (попытка {attempt + 1}/{max_retries})"
        
        return "", last_error
    
    def ocr_with_chandra(self, image_data: bytes) -> str:
        """OCR image using Chandra with markdown output."""
        import requests
        
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        prompt = """Распознай весь текст на изображении и верни его в формате Markdown.
Сохрани структуру:
- Заголовки как # ## ###
- Таблицы в формате Markdown (|заголовок|заголовок|)
- Списки как - или 1. 2. 3.
Верни ТОЛЬКО текст в Markdown без комментариев."""
        
        try:
            response = requests.post(
                f"http://{self.vision_host}/v1/chat/completions",
                json={
                    "model": self.vision_model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                            }
                        ]
                    }],
                    "max_tokens": 4096,
                    "temperature": 0.0
                },
                timeout=180
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"Chandra Error: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"Chandra Exception: {e}")
            return ""


