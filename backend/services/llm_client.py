"""
Enterprise LLM Client for Document Analysis
Integrates with GPT and Vision services for entity extraction and OCR
"""
import httpx
import re
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import ML_CONFIG, settings


class LLMClient:
    """Client for LLM and Vision services"""
    
    def __init__(self):
        self.gpt_host = ML_CONFIG["gpt"]["host"]
        self.gpt_model = ML_CONFIG["gpt"]["model"]
        self.vision_host = ML_CONFIG["vision"]["host"]
        self.vision_model = ML_CONFIG["vision"]["model"]
        self.timeout = ML_CONFIG["timeout"]
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities from document text using LLM
        Falls back to regex-based extraction if LLM unavailable
        """
        try:
            return self._llm_extract(text)
        except Exception as e:
            print(f"LLM extraction failed: {e}, using fallback")
            return self._regex_extract(text)
    
    def _llm_extract(self, text: str) -> Dict[str, Any]:
        """Extract using LLM API"""
        prompt = f"""Извлеки из текста договора следующие сущности в JSON формате:

1. parties - стороны договора (массив объектов с полями: type, name, inn, address, contact)
2. dates - ключевые даты (объект с полями: effective_date, expiration_date, renewal_terms)
3. payment_terms - условия оплаты (объект: total_amount, currency, payment_schedule, payment_days, method)
4. penalties - штрафы и неустойки (массив: type, rate, cap)
5. obligations - основные обязательства сторон (массив строк)
6. termination - условия расторжения (объект: notice_days, grounds)
7. liability - ответственность (объект: cap, exclusions)
8. confidentiality - конфиденциальность (объект: duration, scope)
9. governing_law - применимое право (строка)
10. dispute_resolution - порядок разрешения споров (строка)

Текст договора:
{text[:6000]}

Ответь ТОЛЬКО валидным JSON без markdown:"""

        try:
            response = httpx.post(
                f"http://{self.gpt_host}/v1/chat/completions",
                json={
                    "model": self.gpt_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2500
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
                # Ensure all expected keys exist
                return self._normalize_extracted(extracted)
        except Exception as e:
            print(f"LLM API error: {e}")
            raise
        
        return self._regex_extract(text)
    
    def _normalize_extracted(self, extracted: Dict) -> Dict[str, Any]:
        """Normalize extracted data to ensure consistent structure"""
        normalized = {
            "parties": extracted.get("parties", []),
            "dates": extracted.get("dates", {}),
            "payment_terms": extracted.get("payment_terms", {}),
            "penalties": extracted.get("penalties", []),
            "obligations": extracted.get("obligations", []),
            "termination": extracted.get("termination", {}),
            "liability": extracted.get("liability", {}),
            "confidentiality": extracted.get("confidentiality", {}),
            "governing_law": extracted.get("governing_law", ""),
            "dispute_resolution": extracted.get("dispute_resolution", "")
        }
        return normalized
    
    def _regex_extract(self, text: str) -> Dict[str, Any]:
        """Comprehensive regex-based extraction fallback"""
        entities = {
            "parties": self._extract_parties(text),
            "dates": self._extract_dates(text),
            "payment_terms": self._extract_payment_terms(text),
            "penalties": self._extract_penalties(text),
            "obligations": self._extract_obligations(text),
            "termination": self._extract_termination(text),
            "liability": self._extract_liability(text),
            "confidentiality": self._extract_confidentiality(text),
            "governing_law": self._extract_governing_law(text),
            "dispute_resolution": self._extract_dispute_resolution(text)
        }
        return entities
    
    def _extract_parties(self, text: str) -> List[Dict]:
        """Extract party information"""
        parties = []
        
        # Company patterns
        company_patterns = [
            r'(?:ООО|ОАО|ЗАО|ПАО|АО)\s*[«"]([^»"]+)[»"]',
            r'(?:ООО|ОАО|ЗАО|ПАО|АО)\s+([А-Яа-яЁё\s\-]+)',
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            for match in matches[:3]:
                if len(match.strip()) > 2:
                    parties.append({
                        "type": "legal_entity",
                        "name": match.strip(),
                        "inn": self._find_inn_for_party(text, match),
                        "address": None,
                        "contact": None
                    })
        
        # Role-based extraction
        role_patterns = [
            (r'(?:Заказчик|Customer)[:\s]+([^\n,]+)', "customer"),
            (r'(?:Исполнитель|Contractor)[:\s]+([^\n,]+)', "contractor"),
            (r'(?:Поставщик|Supplier)[:\s]+([^\n,]+)', "supplier"),
            (r'(?:Покупатель|Buyer)[:\s]+([^\n,]+)', "buyer"),
        ]
        
        for pattern, role in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 3 and not any(p["name"] == name for p in parties):
                    parties.append({
                        "type": role,
                        "name": name,
                        "inn": self._find_inn_for_party(text, name),
                        "address": None,
                        "contact": None
                    })
        
        return parties[:5]
    
    def _find_inn_for_party(self, text: str, party_name: str) -> Optional[str]:
        """Find INN near party name"""
        # Look for INN pattern near the party name
        idx = text.lower().find(party_name.lower()[:20])
        if idx >= 0:
            context = text[idx:idx+500]
            inn_match = re.search(r'ИНН[:\s]*(\d{10,12})', context, re.IGNORECASE)
            if inn_match:
                return inn_match.group(1)
        return None
    
    def _extract_dates(self, text: str) -> Dict[str, Any]:
        """Extract dates comprehensively"""
        dates = {}
        
        # General date pattern
        date_pattern = r'\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4}'
        all_dates = re.findall(date_pattern, text)
        if all_dates:
            dates["found_dates"] = list(set(all_dates))[:10]
        
        # Specific date types
        patterns = {
            "effective_date": [
                r'(?:вступает в силу|начало действия|effective)[^\d]*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',
                r'(?:с|from)\s*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',
            ],
            "expiration_date": [
                r'(?:срок действия|до|until|окончание)[^\d]*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',
                r'(?:действует до|expires)[^\d]*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',
            ],
            "signing_date": [
                r'(?:подписан|signed|заключен)[^\d]*(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})',
            ]
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    dates[key] = match.group(1)
                    break
        
        # Extract duration
        duration_match = re.search(r'(?:срок|period|duration)[^\d]*(\d+)\s*(год|лет|месяц|month|year)', text, re.IGNORECASE)
        if duration_match:
            dates["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}"
        
        # Auto-renewal
        if re.search(r'(автоматическ|automatic).*(продлен|renew|пролонг)', text, re.IGNORECASE):
            dates["auto_renewal"] = True
            renewal_match = re.search(r'(\d+)\s*(год|лет|месяц|month|year)', text[text.lower().find('продлен'):text.lower().find('продлен')+100] if 'продлен' in text.lower() else text, re.IGNORECASE)
            if renewal_match:
                dates["renewal_term"] = f"{renewal_match.group(1)} {renewal_match.group(2)}"
        
        return dates
    
    def _extract_payment_terms(self, text: str) -> Dict[str, Any]:
        """Extract payment terms comprehensively"""
        terms = {}
        
        # Amount patterns
        amount_patterns = [
            (r'(\d[\d\s]*[\.,]?\d*)\s*(рубл|руб|RUB|₽)', "RUB"),
            (r'(\d[\d\s]*[\.,]?\d*)\s*(USD|\$)', "USD"),
            (r'(\d[\d\s]*[\.,]?\d*)\s*(EUR|€)', "EUR"),
        ]
        
        amounts = []
        for pattern, currency in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:3]:
                try:
                    value = float(match[0].replace(' ', '').replace(',', '.'))
                    amounts.append({"value": value, "currency": currency})
                except ValueError:
                    pass
        
        if amounts:
            # Assume largest is total
            amounts.sort(key=lambda x: x["value"], reverse=True)
            terms["total_amount"] = amounts[0]["value"]
            terms["currency"] = amounts[0]["currency"]
            terms["all_amounts"] = amounts[:5]
        
        # Payment days
        days_patterns = [
            r'(?:оплата|платеж|payment)[^\d]*(\d+)\s*(?:календарных|рабочих|business)?\s*дн',
            r'(\d+)\s*(?:календарных|рабочих)?\s*дн[яейь].*(?:оплат|платеж)',
            r'в течение\s*(\d+)\s*дн',
        ]
        for pattern in days_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                terms["payment_days"] = int(match.group(1))
                break
        
        # Advance payment
        advance_match = re.search(r'(предоплат|аванс|advance)[^\d]*(\d+)\s*%', text, re.IGNORECASE)
        if advance_match:
            terms["advance_percent"] = int(advance_match.group(2))
        
        # Payment method
        if re.search(r'(безналичн|bank transfer|wire)', text, re.IGNORECASE):
            terms["method"] = "bank_transfer"
        elif re.search(r'(наличн|cash)', text, re.IGNORECASE):
            terms["method"] = "cash"
        
        return terms
    
    def _extract_penalties(self, text: str) -> List[Dict]:
        """Extract penalty clauses"""
        penalties = []
        
        penalty_patterns = [
            (r'(?:штраф|неустойка|пеня|penalty)[^\d]*(\d+[\.,]?\d*)\s*%', "percent"),
            (r'(\d+[\.,]?\d*)\s*%\s*(?:за каждый день|в день|per day)', "daily_percent"),
            (r'(?:штраф|неустойка|penalty)[^\d]*(\d[\d\s]*[\.,]?\d*)\s*(?:рубл|руб|RUB)', "fixed_rub"),
        ]
        
        for pattern, penalty_type in penalty_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:3]:
                try:
                    value = float(match.replace(' ', '').replace(',', '.'))
                    penalties.append({
                        "type": penalty_type,
                        "rate": value,
                        "unit": "%" if "percent" in penalty_type else "RUB"
                    })
                except ValueError:
                    pass
        
        # Check for penalty cap
        cap_match = re.search(r'(?:не более|не превышает|максимум|cap)[^\d]*(\d+)\s*%', text, re.IGNORECASE)
        if cap_match and penalties:
            for p in penalties:
                p["cap"] = f"{cap_match.group(1)}%"
        
        return penalties[:5]
    
    def _extract_obligations(self, text: str) -> List[str]:
        """Extract key obligations"""
        obligations = []
        
        patterns = [
            r'(?:обязуется|обязан|shall|must)[:\s]+([^\.]+)',
            r'(?:Исполнитель|Заказчик|Поставщик)\s+(?:обязуется|обязан)[:\s]+([^\.]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:5]:
                cleaned = match.strip()
                if len(cleaned) > 20 and len(cleaned) < 200:
                    obligations.append(cleaned)
        
        return list(set(obligations))[:10]
    
    def _extract_termination(self, text: str) -> Dict[str, Any]:
        """Extract termination conditions"""
        termination = {}
        
        # Notice period
        notice_patterns = [
            r'(?:уведомлен|извещен|notice)[^\d]*(\d+)\s*(?:календарных|рабочих)?\s*дн',
            r'за\s*(\d+)\s*дн.*(?:до расторжения|prior)',
        ]
        for pattern in notice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                termination["notice_days"] = int(match.group(1))
                break
        
        # Termination grounds
        grounds = []
        if re.search(r'(существенн.*нарушен|material breach)', text, re.IGNORECASE):
            grounds.append("material_breach")
        if re.search(r'(в одностороннем порядке|unilateral)', text, re.IGNORECASE):
            grounds.append("unilateral")
        if re.search(r'(по соглашению сторон|mutual agreement)', text, re.IGNORECASE):
            grounds.append("mutual_agreement")
        if re.search(r'(банкротств|bankruptcy|insolvency)', text, re.IGNORECASE):
            grounds.append("bankruptcy")
        
        if grounds:
            termination["grounds"] = grounds
        
        return termination
    
    def _extract_liability(self, text: str) -> Dict[str, Any]:
        """Extract liability provisions"""
        liability = {}
        
        # Liability cap
        cap_patterns = [
            r'(?:ответственност|liability)[^\d]*(?:не более|не превышает|limited to|cap)[^\d]*(\d[\d\s]*[\.,]?\d*)',
            r'(?:максимальн|maximum).*(?:ответственност|liability)[^\d]*(\d[\d\s]*[\.,]?\d*)',
        ]
        for pattern in cap_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    liability["cap"] = float(match.group(1).replace(' ', '').replace(',', '.'))
                except ValueError:
                    pass
                break
        
        # Check for unlimited liability
        if not liability.get("cap"):
            if re.search(r'(полн.*ответственност|full liability|unlimited)', text, re.IGNORECASE):
                liability["unlimited"] = True
        
        # Exclusions
        exclusions = []
        if re.search(r'(упущенн.*выгод|lost profits)', text, re.IGNORECASE):
            exclusions.append("lost_profits_excluded")
        if re.search(r'(косвенн.*убытк|indirect damages)', text, re.IGNORECASE):
            exclusions.append("indirect_damages_excluded")
        
        if exclusions:
            liability["exclusions"] = exclusions
        
        return liability
    
    def _extract_confidentiality(self, text: str) -> Dict[str, Any]:
        """Extract confidentiality provisions"""
        confidentiality = {}
        
        # Duration
        duration_match = re.search(r'(?:конфиденциальн|confidential)[^\d]*(\d+)\s*(год|лет|year)', text, re.IGNORECASE)
        if duration_match:
            confidentiality["duration_years"] = int(duration_match.group(1))
        
        # Post-termination
        if re.search(r'(после прекращения|after termination|post.?termination)', text, re.IGNORECASE):
            confidentiality["survives_termination"] = True
        
        return confidentiality
    
    def _extract_governing_law(self, text: str) -> str:
        """Extract governing law"""
        patterns = [
            r'(?:применимое право|governing law|applicable law)[:\s]+([^\n\.]+)',
            r'(?:регулируется|governed by)[:\s]+([^\n\.]+)',
            r'право\s+(России|РФ|Российской Федерации|England|USA)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_dispute_resolution(self, text: str) -> str:
        """Extract dispute resolution mechanism"""
        if re.search(r'(арбитраж|arbitrat)', text, re.IGNORECASE):
            # Try to find specific arbitration court
            court_match = re.search(r'(МКАС|ICC|LCIA|ТПП|Арбитражный суд[^\n\.]+)', text)
            if court_match:
                return f"Arbitration: {court_match.group(1)}"
            return "Arbitration"
        elif re.search(r'(третейск|mediation)', text, re.IGNORECASE):
            return "Mediation"
        elif re.search(r'(суд|court)', text, re.IGNORECASE):
            court_match = re.search(r'(Арбитражный суд[^\n\.]+|суд[^\n\.]+)', text)
            if court_match:
                return f"Court: {court_match.group(1)}"
            return "Court"
        
        return ""
    
    def ocr_document(self, file_path: str) -> str:
        """OCR a document using Chandra Vision"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = httpx.post(
                    f"http://{self.vision_host}{self.vision_model}",
                    files=files,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                return result.get("text", "")
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""
    
    def analyze_semantic_change(self, old_text: str, new_text: str) -> Dict[str, Any]:
        """Analyze semantic meaning of a change using LLM"""
        prompt = f"""Analyze the change in contract text:

WAS:
{old_text[:1000]}

BECAME:
{new_text[:1000]}

Describe:
1. What changed substantively?
2. Impact on parties?
3. Criticality (LOW/MEDIUM/HIGH)?

Answer in JSON:"""

        try:
            response = httpx.post(
                f"http://{self.gpt_host}/v1/chat/completions",
                json={
                    "model": self.gpt_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 500
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            return {"analysis": result["choices"][0]["message"]["content"]}
        except Exception as e:
            return {"error": str(e), "analysis": "LLM analysis unavailable"}
