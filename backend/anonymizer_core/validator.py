"""Validation module for checking anonymization quality."""

from typing import Optional
from dataclasses import dataclass, field

from anonymizer_utils.regex_patterns import (
    PRICE_PATTERN,
    COMPANY_FULL_PATTERN,
    FIO_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    INN_PATTERN,
    OGRN_PATTERN,
    BANK_ACCOUNT_PATTERN,
)
from .ml_integration import MLIntegration


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 1.0


class Validator:
    """Validator for checking anonymization completeness."""
    
    def __init__(self, ml_integration: Optional[MLIntegration] = None):
        self.ml = ml_integration
    
    def validate_regex(self, text: str, settings: dict[str, bool]) -> ValidationResult:
        """
        Validate text using regex patterns.
        
        Args:
            text: Text to validate
            settings: Anonymization settings that were used
            
        Returns:
            ValidationResult with any issues found
        """
        import re
        result = ValidationResult()
        
        # Strip HTML/markdown tags to avoid false positives
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', clean_text)  # markdown links
        clean_text = re.sub(r'[#*_`~]', '', clean_text)  # markdown formatting
        
        # Check for remaining prices
        if settings.get("prices", False):
            prices = PRICE_PATTERN.findall(clean_text)
            # Filter out anonymized prices (0 ₽, $0, etc.)
            real_prices = [p for p in prices if not self._is_anonymized_price(p)]
            if real_prices:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные цены: {real_prices[:3]}")
        
        # Check for remaining companies
        if settings.get("companies", False):
            companies = COMPANY_FULL_PATTERN.findall(clean_text)
            # Filter out anonymized companies (Компания 1, etc.)
            real_companies = [c for c in companies if not c.startswith("Компания ")]
            if real_companies:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные компании: {real_companies[:3]}")
        
        # Check for remaining personal data
        if settings.get("personal", False):
            fio = FIO_PATTERN.findall(clean_text)
            # Filter out anonymized FIO
            real_fio = [f for f in fio if "Контактное лицо" not in f]
            if real_fio:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные ФИО: {real_fio[:3]}")
            
            emails = EMAIL_PATTERN.findall(clean_text)
            real_emails = [e for e in emails if "[email удален]" not in e]
            if real_emails:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные email: {real_emails[:3]}")
            
            phones = PHONE_PATTERN.findall(clean_text)
            real_phones = [p for p in phones if "[телефон удален]" not in p]
            if real_phones:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные телефоны: {real_phones[:3]}")
        
        # Check for remaining requisites
        if settings.get("requisites", False):
            inn = INN_PATTERN.findall(clean_text)
            real_inn = [i for i in inn if "[УДАЛЕНО]" not in str(i)]
            if real_inn:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные ИНН")
            
            ogrn = OGRN_PATTERN.findall(clean_text)
            real_ogrn = [o for o in ogrn if "[УДАЛЕНО]" not in str(o)]
            if real_ogrn:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные ОГРН")
            
            accounts = BANK_ACCOUNT_PATTERN.findall(clean_text)
            real_accounts = [a for a in accounts if "[УДАЛЕНО]" not in str(a)]
            if real_accounts:
                result.is_valid = False
                result.issues.append(f"Найдены необезличенные банковские реквизиты")
        
        # Calculate confidence
        if result.issues:
            result.confidence = max(0.3, 1.0 - (len(result.issues) * 0.1))
        
        return result
    
    async def validate_with_ml(
        self, 
        text: str, 
        settings: dict[str, bool]
    ) -> ValidationResult:
        """
        Validate text using ML model.
        
        Args:
            text: Text to validate
            settings: Anonymization settings that were used
            
        Returns:
            ValidationResult with any issues found
        """
        # First do regex validation
        result = self.validate_regex(text, settings)
        
        # If ML is available, do additional check
        if self.ml:
            try:
                ml_result = await self.ml.validate_anonymization(text)
                
                if ml_result.get("found", False):
                    items = ml_result.get("items", [])
                    for item in items:
                        result.issues.append(f"ML обнаружил: {item}")
                    result.is_valid = False
                    result.confidence = min(result.confidence, 0.5)
                
                if ml_result.get("error"):
                    result.warnings.append(f"ML проверка: {ml_result['error']}")
                    
            except Exception as e:
                result.warnings.append(f"Ошибка ML валидации: {str(e)}")
        
        return result
    
    def _is_anonymized_price(self, price: str) -> bool:
        """Check if a price string is already anonymized."""
        anonymized_patterns = ["0 ₽", "0 руб", "$0", "€0", "[СУММА"]
        price_lower = price.lower().strip()
        if "[сумма" in price_lower:
            return True
        return any(p.lower() in price_lower for p in anonymized_patterns)
    
    def generate_report(self, result: ValidationResult) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            result: ValidationResult to report on
            
        Returns:
            Formatted report string
        """
        lines = ["=" * 50, "ОТЧЕТ О ВАЛИДАЦИИ ОБЕЗЛИЧИВАНИЯ", "=" * 50, ""]
        
        if result.is_valid:
            lines.append("✅ Документ успешно обезличен")
            lines.append(f"   Уровень уверенности: {result.confidence * 100:.0f}%")
        else:
            lines.append("⚠️ Обнаружены проблемы")
            lines.append(f"   Уровень уверенности: {result.confidence * 100:.0f}%")
        
        if result.issues:
            lines.append("")
            lines.append("ПРОБЛЕМЫ:")
            for i, issue in enumerate(result.issues, 1):
                lines.append(f"  {i}. {issue}")
        
        if result.warnings:
            lines.append("")
            lines.append("ПРЕДУПРЕЖДЕНИЯ:")
            for warning in result.warnings:
                lines.append(f"  • {warning}")
        
        lines.append("")
        lines.append("=" * 50)
        
        return "\n".join(lines)


