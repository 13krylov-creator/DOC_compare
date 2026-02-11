"""Regular expression patterns for document anonymization."""

import re

# ============== PRICES & MONEY ==============

# Russian rubles patterns
PRICE_RUB_PATTERNS = [
    # "1 500 000 руб.", "1500000 рублей", "1,5 млн ₽"
    r'\d[\d\s]*[\d]\s*(?:руб(?:л(?:ей|я|ь)?)?\.?|₽)',
    r'\d[\d\s,\.]*\s*(?:млн|тыс|млрд)\.?\s*(?:руб(?:л(?:ей|я|ь)?)?\.?|₽)',
    # Standalone numbers with currency context
    r'(?:стоимость|цена|сумма|итого|всего|оплата|бюджет)[\s:]+\d[\d\s,\.]*',
]

# USD/EUR patterns
PRICE_FOREIGN_PATTERNS = [
    r'\$\s*\d[\d\s,\.]*(?:\s*(?:млн|тыс|M|K))?',
    r'\d[\d\s,\.]*\s*(?:USD|EUR|€|\$)',
    r'€\s*\d[\d\s,\.]*(?:\s*(?:млн|тыс|M|K))?',
]

# Combined price pattern
PRICE_PATTERN = re.compile(
    '|'.join(PRICE_RUB_PATTERNS + PRICE_FOREIGN_PATTERNS),
    re.IGNORECASE | re.UNICODE
)

# ============== COMPANIES ==============

# Russian legal forms
COMPANY_FORMS = r'(?:ООО|ОАО|ЗАО|ПАО|АО|ИП|НКО|ГК|ГУП|МУП|ФГУП)'

# Company name patterns
COMPANY_PATTERNS = [
    # "ООО «Ромашка»", "ООО "Ромашка""
    rf'{COMPANY_FORMS}\s*[«"\'„]([^»"\'\"]+)[»"\'"]',
    # "ООО Ромашка"
    rf'{COMPANY_FORMS}\s+([А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+)*)',
]

COMPANY_PATTERN = re.compile(
    '|'.join(COMPANY_PATTERNS),
    re.UNICODE
)

# Full company with legal form
COMPANY_FULL_PATTERN = re.compile(
    rf'{COMPANY_FORMS}\s*[«"\'„]?[^»"\'\"]*[»"\'"]?|{COMPANY_FORMS}\s+[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+)*',
    re.UNICODE
)

# Companies without legal form (common patterns)
# Words ending with -центр, -банк, -холдинг, etc. or quoted names
COMPANY_INFORMAL_PATTERNS = [
    # Words with common company suffixes
    r'[А-ЯЁA-Z][а-яёa-zA-Z]*(?:-[А-Яа-яЁёA-Za-z]+)*(?:центр|банк|холдинг|групп[аы]?|корпорация|фонд|институт|завод|фабрика|комбинат)',
    # Quoted company names  
    r'[«"][А-ЯЁA-Z][^»"]+[»"]',
]

COMPANY_INFORMAL_PATTERN = re.compile(
    '|'.join(COMPANY_INFORMAL_PATTERNS),
    re.UNICODE | re.IGNORECASE
)

# ============== PERSONAL DATA ==============

# Russian full names (ФИО)
FIO_PATTERNS = [
    # Иванов Иван Иванович
    r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+ич|[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+на',
    # И.И. Иванов, Иванов И.И.
    r'[А-ЯЁ]\.\s*[А-ЯЁ]\.\s*[А-ЯЁ][а-яё]+',
    r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.',
]

FIO_PATTERN = re.compile(
    '|'.join(FIO_PATTERNS),
    re.UNICODE
)

# Email pattern
EMAIL_PATTERN = re.compile(
    r'[\w\.-]+@[\w\.-]+\.\w+',
    re.UNICODE
)

# Phone patterns (Russian)
PHONE_PATTERNS = [
    r'(?:\+7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}',
    r'(?:\+7|8)\s*\(\d{3}\)\s*\d{3}[\-\s]?\d{2}[\-\s]?\d{2}',
    r'(?:\+7|8)\d{10}',
]

PHONE_PATTERN = re.compile(
    '|'.join(PHONE_PATTERNS),
    re.UNICODE
)

# ============== ADDRESSES ==============

# Only match specific address patterns that are clearly addresses
# Removed "дом" and "д." as standalone - they need to be followed by a number
ADDRESS_STREET_KEYWORDS = r'(?:ул\.|улица|пр\.|проспект|пер\.|переулок|бул\.|бульвар|наб\.|набережная|пл\.|площадь|ш\.|шоссе)'
ADDRESS_BUILDING_KEYWORDS = r'(?:(?:д\.|дом|корп\.|корпус|стр\.|строение|кв\.|квартира|оф\.|офис)\s*\d+)'

# Address must have either a street keyword OR building keyword with number
ADDRESS_PATTERN = re.compile(
    rf'(?:{ADDRESS_STREET_KEYWORDS})\s*[А-Яа-яЁёA-Za-z0-9\-\,\.\s]{{3,50}}|'
    rf'(?:г\.|город)\s*[А-Яа-яЁё][а-яё]+(?:\s*,\s*{ADDRESS_STREET_KEYWORDS}\s*[А-Яа-яЁёA-Za-z0-9\-\,\.\s]{{3,30}})?',
    re.IGNORECASE | re.UNICODE
)

# Postal code pattern (Russian 6-digit)
POSTAL_CODE_PATTERN = re.compile(r'\b\d{6}\b')

# ============== REQUISITES ==============

# INN (Individual Tax Number) - 10 or 12 digits
INN_PATTERN = re.compile(
    r'(?:ИНН|инн)[\s:]*(\d{10}|\d{12})|(?<!\d)(\d{10}|\d{12})(?!\d)',
    re.UNICODE
)

# OGRN - 13 or 15 digits
OGRN_PATTERN = re.compile(
    r'(?:ОГРН|огрн|ОГРНИП|огрнип)[\s:]*(\d{13}|\d{15})',
    re.UNICODE
)

# Bank account - 20 digits
BANK_ACCOUNT_PATTERN = re.compile(
    r'(?:р/?с|расч[её]тный счет|к/?с|корр[её]спонденский счет)[\s:]*(\d{20})',
    re.IGNORECASE | re.UNICODE
)

# BIK - 9 digits
BIK_PATTERN = re.compile(
    r'(?:БИК|бик)[\s:]*(\d{9})',
    re.UNICODE
)

# KPP - 9 digits  
KPP_PATTERN = re.compile(
    r'(?:КПП|кпп)[\s:]*(\d{9})',
    re.UNICODE
)

# ============== DATES ==============

DATE_PATTERNS = [
    # DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
    r'\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4}',
    # "01 января 2025 г.", "январь 2025"
    r'\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\s*г?\.?',
    r'(?:январ[яь]|феврал[яь]|март[а]?|апрел[яь]|ма[яй]|июн[яь]|июл[яь]|август[а]?|сентябр[яь]|октябр[яь]|ноябр[яь]|декабр[яь])\s+\d{4}\s*г?\.?',
    # Q1 2025, 1Q2025
    r'[QКкq][1-4]\s*\d{4}|\d{4}\s*[QКкq][1-4]',
    # "2025 год", "2025 г."
    r'\d{4}\s*(?:год[а]?|г\.)',
]

DATE_PATTERN = re.compile(
    '|'.join(DATE_PATTERNS),
    re.IGNORECASE | re.UNICODE
)

# ============== HELPER FUNCTIONS ==============

def find_all_prices(text: str) -> list[tuple[str, int, int]]:
    """Find all price mentions in text with positions."""
    matches = []
    for match in PRICE_PATTERN.finditer(text):
        matches.append((match.group(), match.start(), match.end()))
    return matches

def find_all_companies(text: str) -> list[tuple[str, int, int]]:
    """Find all company mentions in text with positions."""
    matches = []
    for match in COMPANY_FULL_PATTERN.finditer(text):
        matches.append((match.group(), match.start(), match.end()))
    return matches

def find_all_personal_data(text: str) -> dict[str, list[tuple[str, int, int]]]:
    """Find all personal data (FIO, email, phone) in text."""
    return {
        "fio": [(m.group(), m.start(), m.end()) for m in FIO_PATTERN.finditer(text)],
        "email": [(m.group(), m.start(), m.end()) for m in EMAIL_PATTERN.finditer(text)],
        "phone": [(m.group(), m.start(), m.end()) for m in PHONE_PATTERN.finditer(text)],
    }

def find_all_requisites(text: str) -> dict[str, list[tuple[str, int, int]]]:
    """Find all business requisites in text."""
    return {
        "inn": [(m.group(), m.start(), m.end()) for m in INN_PATTERN.finditer(text)],
        "ogrn": [(m.group(), m.start(), m.end()) for m in OGRN_PATTERN.finditer(text)],
        "bank_account": [(m.group(), m.start(), m.end()) for m in BANK_ACCOUNT_PATTERN.finditer(text)],
        "bik": [(m.group(), m.start(), m.end()) for m in BIK_PATTERN.finditer(text)],
        "kpp": [(m.group(), m.start(), m.end()) for m in KPP_PATTERN.finditer(text)],
    }

def find_all_dates(text: str) -> list[tuple[str, int, int]]:
    """Find all date mentions in text with positions."""
    matches = []
    for match in DATE_PATTERN.finditer(text):
        matches.append((match.group(), match.start(), match.end()))
    return matches


