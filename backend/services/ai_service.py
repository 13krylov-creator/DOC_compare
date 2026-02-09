"""
AI Service for Document Comparison
Integrates with GPT models for semantic analysis
"""
import httpx
import json
import re
from typing import Dict, Any, Optional, List
from config import ML_CONFIG


class AIService:
    """Service for AI-powered document analysis"""
    
    def __init__(self):
        self.gpt_host = ML_CONFIG["gpt"]["host"]
        self.gpt_model = ML_CONFIG["gpt"]["model"]
        self.timeout = ML_CONFIG["timeout"]
    
    def _extract_numbers(self, text: str) -> List[str]:
        """Extract all numbers from text"""
        return re.findall(r'\d+[.,]?\d*', text or "")
    
    def _format_change_for_prompt(self, change: Dict) -> str:
        """Format a single change for the prompt with emphasis on numbers"""
        old = (change.get("original_text") or "").strip()
        new = (change.get("new_text") or "").strip()
        change_type = change.get("type", "MODIFIED")
        classification = change.get("classification", "")
        location = change.get("location", "")
        
        # Extract numbers for comparison
        old_nums = self._extract_numbers(old)
        new_nums = self._extract_numbers(new)
        
        result_parts = []
        
        if location:
            result_parts.append(f"[{location}]")
        
        if change_type == "MODIFIED" and old and new:
            # Show full text without truncation for accurate analysis
            result_parts.append(f"БЫЛО: \"{old}\"")
            result_parts.append(f"СТАЛО: \"{new}\"")
            
            # Highlight numerical differences explicitly
            if old_nums != new_nums and (old_nums or new_nums):
                if old_nums and new_nums:
                    result_parts.append(f"⚠️ ЧИСЛА ИЗМЕНИЛИСЬ: {', '.join(old_nums)} → {', '.join(new_nums)}")
                elif new_nums:
                    result_parts.append(f"⚠️ ДОБАВЛЕНЫ ЧИСЛА: {', '.join(new_nums)}")
                elif old_nums:
                    result_parts.append(f"⚠️ УДАЛЕНЫ ЧИСЛА: {', '.join(old_nums)}")
        elif change_type == "DELETED" and old:
            result_parts.append(f"УДАЛЕНО: \"{old}\"")
            if old_nums:
                result_parts.append(f"(содержало числа: {', '.join(old_nums)})")
        elif change_type == "ADDED" and new:
            result_parts.append(f"ДОБАВЛЕНО: \"{new}\"")
            if new_nums:
                result_parts.append(f"(содержит числа: {', '.join(new_nums)})")
        
        return "\n".join(result_parts)
    
    async def generate_semantic_summary(
        self, 
        text1: str, 
        text2: str, 
        changes: List[Dict],
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AI summary of document changes"""
        
        if not changes:
            return {
                "summary": "✅ Документы идентичны, различий не обнаружено.",
                "ai_used": False
            }
        
        # Collect all numerical changes
        numerical_changes = []
        text_changes = []
        
        for c in changes[:30]:  # Analyze up to 30 changes
            old = c.get("original_text") or ""
            new = c.get("new_text") or ""
            old_nums = self._extract_numbers(old)
            new_nums = self._extract_numbers(new)
            
            if old_nums != new_nums and (old_nums or new_nums):
                numerical_changes.append(c)
            else:
                text_changes.append(c)
        
        # Build detailed changes description
        changes_description = []
        
        # First, highlight numerical changes (most important)
        if numerical_changes:
            changes_description.append("=== ЧИСЛОВЫЕ ИЗМЕНЕНИЯ (ВАЖНО!) ===")
            for c in numerical_changes[:15]:
                changes_description.append(self._format_change_for_prompt(c))
                changes_description.append("")
        
        # Then text changes
        if text_changes:
            changes_description.append("=== ТЕКСТОВЫЕ ИЗМЕНЕНИЯ ===")
            for c in text_changes[:10]:
                changes_description.append(self._format_change_for_prompt(c))
                changes_description.append("")
        
        changes_text = "\n".join(changes_description)
        
        # Build comprehensive prompt with strict instructions
        prompt = f"""Ты — эксперт по анализу документов. Проанализируй изменения между двумя версиями документа.

КРИТИЧЕСКИ ВАЖНО:
1. Обрати особое внимание на ЧИСЛОВЫЕ изменения (суммы, даты, проценты, количества)
2. Если числа изменились — это ОБЯЗАТЕЛЬНО нужно отметить в резюме
3. НЕ ВЫДУМЫВАЙ изменения, которых нет в списке ниже!
4. Описывай ТОЛЬКО те изменения, которые явно указаны в данных

ОБНАРУЖЕННЫЕ ИЗМЕНЕНИЯ:
{changes_text}

ЗАДАЧА: Напиши краткое резюме (2-4 предложения) о том, что конкретно изменилось.
- Если изменились числа/суммы — укажи какие именно значения изменились (было X, стало Y)
- Если изменился текст — опиши суть изменения
- НЕ придумывай изменений, которых нет в списке выше!
- Не пиши "ничего не изменилось" если есть хоть одно изменение выше"""

        # Add custom prompt if provided
        if custom_prompt:
            prompt += f"\n\nДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ: {custom_prompt}"
        
        try:
            print(f"Calling GPT at http://{self.gpt_host}/v1/chat/completions")
            response = await self._call_gpt(prompt)
            if response:
                return {
                    "summary": response,
                    "ai_used": True
                }
            else:
                return {
                    "summary": self.generate_fallback_summary(changes),
                    "ai_used": False
                }
        except Exception as e:
            print(f"GPT call failed: {e}")
            return {
                "summary": self.generate_fallback_summary(changes),
                "ai_used": False
            }
    
    def generate_fallback_summary(self, changes: List[Dict]) -> str:
        """Generate rule-based summary when AI is unavailable"""
        if not changes:
            return "✅ Документы идентичны."
        
        parts = [f"📋 Найдено **{len(changes)}** изменений.\n"]
        
        # First, highlight numerical changes
        numerical_found = False
        for c in changes[:30]:
            old = c.get("original_text") or ""
            new = c.get("new_text") or ""
            old_nums = self._extract_numbers(old)
            new_nums = self._extract_numbers(new)
            
            if old_nums != new_nums and old_nums and new_nums:
                if not numerical_found:
                    parts.append("**💰 Числовые изменения:**")
                    numerical_found = True
                parts.append(f"- Значение изменилось: {old_nums[0]} → {new_nums[0]}")
        
        if numerical_found:
            parts.append("")
        
        # Show other changes
        parts.append("**Изменения:**")
        for i, c in enumerate(changes[:5], 1):
            old = (c.get("original_text") or "—").strip()
            new = (c.get("new_text") or "—").strip()
            if c.get("type") == "MODIFIED":
                parts.append(f"{i}. Изменено: `{old[:60]}...` → `{new[:60]}...`")
            elif c.get("type") == "ADDED":
                parts.append(f"{i}. Добавлено: `{new[:80]}...`")
            elif c.get("type") == "DELETED":
                parts.append(f"{i}. Удалено: `{old[:80]}...`")
        
        parts.append("\n⚠️ *AI недоступен — автоматическое резюме.*")
        
        return "\n".join(parts)
    
    async def _call_gpt(self, prompt: str) -> Optional[str]:
        """Call GPT API"""
        url = f"http://{self.gpt_host}/v1/chat/completions"
        
        payload = {
            "model": self.gpt_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload)
                print(f"GPT response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content if content else None
                else:
                    print(f"GPT API error: {response.status_code} - {response.text[:200]}")
        except httpx.TimeoutException:
            print("GPT request timed out after 60 seconds")
        except Exception as e:
            print(f"GPT request error: {e}")
        return None


# Singleton instance
ai_service = AIService()
