"""Main anonymization logic for document processing."""

import re
import json
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

from .document_parser import ParsedDocument, TextBlock
from anonymizer_utils.regex_patterns import (
    PRICE_PATTERN,
    COMPANY_FULL_PATTERN,
    COMPANY_INFORMAL_PATTERN,
    FIO_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    ADDRESS_PATTERN,
    INN_PATTERN,
    OGRN_PATTERN,
    BANK_ACCOUNT_PATTERN,
    BIK_PATTERN,
    KPP_PATTERN,
    DATE_PATTERN,
)

if TYPE_CHECKING:
    from .ml_integration import MLIntegration


@dataclass
class Replacement:
    """Represents a single replacement made during anonymization."""
    original: str
    anonymized: str
    replacement_type: str
    position: dict = field(default_factory=dict)


@dataclass
class AnonymizationResult:
    """Result of anonymization process."""
    original_text: str
    anonymized_text: str
    replacements: list[Replacement] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Anonymizer:
    """Main class for document anonymization."""
    
    def __init__(self, ml_integration: Optional["MLIntegration"] = None):
        # Counters for consistent naming
        self._company_counter = 0
        self._person_counter = 0
        self._address_counter = 0
        self._date_counter = 0
        self._product_counter = 0
        self._price_counter = 0
        
        # Mapping caches for consistency
        self._company_map: dict[str, str] = {}
        self._person_map: dict[str, str] = {}
        self._address_map: dict[str, str] = {}
        
        # ML integration for enhanced detection
        self._ml = ml_integration
        
    def reset_counters(self):
        """Reset all counters and mappings for a new document."""
        self._company_counter = 0
        self._person_counter = 0
        self._address_counter = 0
        self._date_counter = 0
        self._product_counter = 0
        self._price_counter = 0
        self._company_map = {}
        self._person_map = {}
        self._address_map = {}
    
    def anonymize_text(
        self, 
        text: str, 
        settings: dict[str, bool],
        use_ml: bool = True
    ) -> AnonymizationResult:
        """
        Anonymize text based on provided settings.
        
        Args:
            text: Text to anonymize
            settings: Dictionary of anonymization options
            use_ml: Whether to use ML for enhanced detection
            
        Returns:
            AnonymizationResult with anonymized text and replacements
        """
        result = AnonymizationResult(original_text=text, anonymized_text=text)
        
        # Try ML-based detection first for better accuracy
        ml_entities = {}
        if use_ml and self._ml:
            ml_entities = self._detect_entities_with_ml(text, settings)
            if ml_entities:
                result = self._apply_ml_entities(result, ml_entities, settings)
        
        # Apply regex-based anonymization (catches what ML might miss)
        if settings.get("prices", False):
            result = self._anonymize_prices(result)
        
        if settings.get("companies", False):
            result = self._anonymize_companies(result)
        
        if settings.get("personal_data", False) or settings.get("personal", False):
            result = self._anonymize_personal_data(result)
        
        if settings.get("addresses", False):
            result = self._anonymize_addresses(result)
        
        if settings.get("requisites", False):
            result = self._anonymize_requisites(result)
        
        if settings.get("dates", False):
            result = self._anonymize_dates(result)
        
        if settings.get("technical_details", False) or settings.get("technical", False):
            result = self._anonymize_technical(result)
        
        return result
    
    def _detect_entities_with_ml(self, text: str, settings: dict) -> dict:
        """Use ML model to detect entities that regex might miss."""
        if not self._ml:
            return {}
        
        try:
            # Truncate text for ML (avoid token limits)
            text_sample = text[:8000] if len(text) > 8000 else text
            
            prompt = f"""Проанализируй текст и найди ВСЕ упоминания следующих сущностей. 
Верни JSON с массивами найденных значений.

Искать:
- companies: названия компаний, организаций (включая без ООО/АО, например "Уралмеханобр", "НИР-центр")
- persons: ФИО людей, имена, фамилии
- prices: цены, суммы денег с числами

Текст:
{text_sample}

Ответ ТОЛЬКО в формате JSON:
{{"companies": ["...", "..."], "persons": ["...", "..."], "prices": ["...", "..."]}}"""

            response_text, error = self._ml.ask_gpt(prompt)
            
            if error or not response_text:
                return {}
            
            # Parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
            
        except Exception as e:
            # ML failed, continue with regex only
            return {}
    
    def _apply_ml_entities(self, result: AnonymizationResult, entities: dict, settings: dict) -> AnonymizationResult:
        """Apply ML-detected entities to text."""
        text = result.anonymized_text
        
        # Apply company replacements
        if settings.get("companies", False):
            for company in entities.get("companies", []):
                if company and len(company) > 2 and company in text:
                    if company not in self._company_map:
                        self._company_counter += 1
                        self._company_map[company] = f"Компания {self._company_counter}"
                        result.replacements.append(Replacement(
                            original=company,
                            anonymized=self._company_map[company],
                            replacement_type="company_ml"
                        ))
                    text = text.replace(company, self._company_map[company])
        
        # Apply person replacements
        if settings.get("personal_data", False) or settings.get("personal", False):
            for person in entities.get("persons", []):
                if person and len(person) > 2 and person in text:
                    if person not in self._person_map:
                        self._person_counter += 1
                        self._person_map[person] = f"Контактное лицо {self._person_counter}"
                        result.replacements.append(Replacement(
                            original=person,
                            anonymized=self._person_map[person],
                            replacement_type="person_ml"
                        ))
                    text = text.replace(person, self._person_map[person])
        
        result.anonymized_text = text
        return result
    
    def _anonymize_prices(self, result: AnonymizationResult) -> AnonymizationResult:
        """Replace all price mentions with anonymized versions."""
        text = result.anonymized_text
        
        def replace_price(match):
            original = match.group()
            # Try to preserve currency symbol at the end
            if "₽" in original or "руб" in original.lower():
                replacement = "0 ₽"
            elif "$" in original or "USD" in original.upper():
                replacement = "$0"
            elif "€" in original or "EUR" in original.upper():
                replacement = "€0"
            else:
                replacement = "0"
            
            result.replacements.append(Replacement(
                original=original,
                anonymized=replacement,
                replacement_type="price"
            ))
            return replacement
        
        result.anonymized_text = PRICE_PATTERN.sub(replace_price, text)
        return result
    
    def _anonymize_companies(self, result: AnonymizationResult) -> AnonymizationResult:
        """Replace company names with anonymized versions."""
        text = result.anonymized_text
        
        def replace_company(match):
            original = match.group()
            
            # Skip very short matches or common words
            if len(original) < 3:
                return original
            
            # Filter stopwords!
            from anonymizer_utils.stopwords import is_stopword
            if is_stopword(original):
                return original
            
            # Check if we've seen this company before
            if original in self._company_map:
                return self._company_map[original]
            
            self._company_counter += 1
            replacement = f"Компания {self._company_counter}"
            self._company_map[original] = replacement
            
            result.replacements.append(Replacement(
                original=original,
                anonymized=replacement,
                replacement_type="company"
            ))
            return replacement
        
        # First apply formal company patterns (ООО, АО, etc.)
        text = COMPANY_FULL_PATTERN.sub(replace_company, text)
        
        # Then apply informal patterns (НИР-центр, etc.)
        text = COMPANY_INFORMAL_PATTERN.sub(replace_company, text)
        
        result.anonymized_text = text
        return result
    
    def _anonymize_personal_data(self, result: AnonymizationResult) -> AnonymizationResult:
        """Replace personal data (FIO, email, phone)."""
        text = result.anonymized_text
        
        # Replace FIO
        def replace_fio(match):
            original = match.group()
            
            if original in self._person_map:
                return self._person_map[original]
            
            self._person_counter += 1
            replacement = f"Контактное лицо {self._person_counter}"
            self._person_map[original] = replacement
            
            result.replacements.append(Replacement(
                original=original,
                anonymized=replacement,
                replacement_type="person"
            ))
            return replacement
        
        text = FIO_PATTERN.sub(replace_fio, text)
        
        # Replace emails
        def replace_email(match):
            original = match.group()
            result.replacements.append(Replacement(
                original=original,
                anonymized="[email удален]",
                replacement_type="email"
            ))
            return "[email удален]"
        
        text = EMAIL_PATTERN.sub(replace_email, text)
        
        # Replace phones
        def replace_phone(match):
            original = match.group()
            result.replacements.append(Replacement(
                original=original,
                anonymized="[телефон удален]",
                replacement_type="phone"
            ))
            return "[телефон удален]"
        
        text = PHONE_PATTERN.sub(replace_phone, text)
        
        result.anonymized_text = text
        return result
    
    def _anonymize_addresses(self, result: AnonymizationResult) -> AnonymizationResult:
        """Replace addresses with anonymized versions."""
        text = result.anonymized_text
        
        def replace_address(match):
            original = match.group()
            
            # Filter stopwords
            from anonymizer_utils.stopwords import is_stopword
            if is_stopword(original):
                return original
            
            # Skip if it's just a keyword without real address info
            # Real addresses have numbers or specific location words
            import re
            has_number = bool(re.search(r'\d', original))
            has_location = any(w in original.lower() for w in ['москва', 'санкт', 'город', 'область', 'край', 'район'])
            if not has_number and not has_location and len(original) < 20:
                return original
            
            if original in self._address_map:
                return self._address_map[original]
            
            self._address_counter += 1
            replacement = f"Адрес №{self._address_counter}"
            self._address_map[original] = replacement
            
            result.replacements.append(Replacement(
                original=original,
                anonymized=replacement,
                replacement_type="address"
            ))
            return replacement
        
        result.anonymized_text = ADDRESS_PATTERN.sub(replace_address, text)
        return result
    
    def _anonymize_requisites(self, result: AnonymizationResult) -> AnonymizationResult:
        """Replace business requisites (INN, OGRN, bank accounts)."""
        text = result.anonymized_text
        
        # INN
        def replace_inn(match):
            original = match.group()
            result.replacements.append(Replacement(
                original=original,
                anonymized="ИНН: [УДАЛЕНО]",
                replacement_type="inn"
            ))
            return "ИНН: [УДАЛЕНО]"
        
        text = INN_PATTERN.sub(replace_inn, text)
        
        # OGRN
        def replace_ogrn(match):
            original = match.group()
            result.replacements.append(Replacement(
                original=original,
                anonymized="ОГРН: [УДАЛЕНО]",
                replacement_type="ogrn"
            ))
            return "ОГРН: [УДАЛЕНО]"
        
        text = OGRN_PATTERN.sub(replace_ogrn, text)
        
        # Bank account
        def replace_account(match):
            original = match.group()
            result.replacements.append(Replacement(
                original=original,
                anonymized="Счет: [УДАЛЕНО]",
                replacement_type="bank_account"
            ))
            return "Счет: [УДАЛЕНО]"
        
        text = BANK_ACCOUNT_PATTERN.sub(replace_account, text)
        
        # BIK
        def replace_bik(match):
            original = match.group()
            result.replacements.append(Replacement(
                original=original,
                anonymized="БИК: [УДАЛЕНО]",
                replacement_type="bik"
            ))
            return "БИК: [УДАЛЕНО]"
        
        text = BIK_PATTERN.sub(replace_bik, text)
        
        # KPP
        def replace_kpp(match):
            original = match.group()
            result.replacements.append(Replacement(
                original=original,
                anonymized="КПП: [УДАЛЕНО]",
                replacement_type="kpp"
            ))
            return "КПП: [УДАЛЕНО]"
        
        text = KPP_PATTERN.sub(replace_kpp, text)
        
        result.anonymized_text = text
        return result
    
    def _anonymize_dates(self, result: AnonymizationResult) -> AnonymizationResult:
        """Replace absolute dates with relative ones."""
        text = result.anonymized_text
        
        def replace_date(match):
            original = match.group()
            self._date_counter += 1
            replacement = f"Дата {self._date_counter}"
            
            result.replacements.append(Replacement(
                original=original,
                anonymized=replacement,
                replacement_type="date"
            ))
            return replacement
        
        result.anonymized_text = DATE_PATTERN.sub(replace_date, text)
        return result
    
    def _anonymize_technical(self, result: AnonymizationResult) -> AnonymizationResult:
        """Replace technical details (product names, versions)."""
        text = result.anonymized_text
        
        # Version patterns
        version_pattern = re.compile(
            r'(?:версия|версии|v\.|version)\s*[\d\.]+',
            re.IGNORECASE
        )
        
        def replace_version(match):
            original = match.group()
            replacement = "версия X.Y"
            
            result.replacements.append(Replacement(
                original=original,
                anonymized=replacement,
                replacement_type="version"
            ))
            return replacement
        
        result.anonymized_text = version_pattern.sub(replace_version, text)
        return result
    
    def get_mapping_json(self, result: AnonymizationResult) -> dict:
        """
        Generate a mapping JSON for export.
        
        Args:
            result: AnonymizationResult with replacements
            
        Returns:
            Dictionary suitable for JSON export
        """
        return {
            "date": datetime.now().isoformat(),
            "total_replacements": len(result.replacements),
            "replacements": [
                {
                    "original": r.original,
                    "anonymized": r.anonymized,
                    "type": r.replacement_type
                }
                for r in result.replacements
            ],
            "by_type": self._group_by_type(result.replacements)
        }
    
    def _group_by_type(self, replacements: list[Replacement]) -> dict[str, int]:
        """Group replacements by type and count."""
        counts = {}
        for r in replacements:
            counts[r.replacement_type] = counts.get(r.replacement_type, 0) + 1
        return counts


