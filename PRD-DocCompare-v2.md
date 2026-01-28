# 📄 PRD: DocumentCompare Platform
## Multi-Tenant Document Comparison & Analysis Engine

**Версия:** 2.0  
**Дата:** Январь 2026  
**Статус:** Ready for Development  
**Фокус:** Smart Document Diff, Not Workflow/Approval

---

## 1. EXECUTIVE SUMMARY

**DocumentCompare** — это SaaS платформа для **глубокого семантического анализа и сравнения** PDF контрактов и документов. Система помогает командам **понять, что реально изменилось** между версиями, найти различия на разных уровнях анализа и автоматически слить несовместимые версии.

### Ключевая разница от других инструментов
- Не просто выделяет изменённые строки (это делает diff)
- **Понимает суть изменений**: "Платёжные условия изменились с 90 на 30 дней" вместо просто "текст изменился"
- Несколько режимов сравнения для разных задач
- Beautiful timeline visualization всех версий
- Автоматический merge разных вариантов

### Основная проблема
- Трудно понять, что реально изменилось в большом контракте
- Версии file naming: "contract_v1_final_REAL_v2_approved.pdf" — невозможно отследить
- Нужно вручную сравнивать две версии, особенно если они большие
- Когда есть 5 вариантов от разных отделов — как их слить?

### Решение
- **Multi-Mode Comparison**: Line-by-line, Semantic, Impact, Clause, Legal diff
- **Smart Timeline**: Beautiful визуализация всех версий документа
- **AI-Powered Insights**: LLM анализирует, что означают изменения
- **Automatic Merge**: Слияние конфликтных версий с выделением точек разногласия
- **Risk Signals**: Автоматически выделяет критичные изменения

---

## 2. VISION & GOALS

### Vision
Стать лучшей платформой для **понимания** того, как изменялись документы, предоставляя инсайты, которые невозможно получить обычным diff инструментом.

### OKRs (Objectives & Key Results)
1. **Reduce time to understand changes** from 30 min → 5 min (per contract)
2. **Capture 100% of meaningful changes** с контекстом и семантикой
3. **Enable 80% non-conflicting merges** автоматически
4. **Risk detection accuracy** > 95% for critical parameters
5. **Timeline visualization** becomes workflow centerpiece (красота + функциональность)

---

## 3. TARGET USERS & PERSONAS

### Persona 1: **Legal Manager (Дарья)**
- Role: Head of Legal Department
- Goal: Быстро разобраться в изменениях контракта
- Task: "5 вариантов контракта от разных отделов — что отличается?"
- Usage: Загружает варианты, видит semantic diff, понимает риски

### Persona 2: **Procurement Manager (Петр)**
- Role: Procurement/Sourcing Lead
- Goal: Управлять версиями контрактов, находить критичные изменения
- Task: "Отследить, как менялись платежные условия через 10 итераций"
- Usage: Просматривает timeline, видит историю изменений

### Persona 3: **Finance Controller (Мария)**
- Role: Finance Department
- Goal: Контролировать финансовые параметры (суммы, сроки, штрафы)
- Task: "Какие суммы изменились между версиями?"
- Usage: Использует "Impact Mode" для анализа финансовых рисков

### Persona 4: **Contract Analyst (Иван)**
- Role: Contract Review / Risk Management
- Goal: Анализировать контракты на соответствие стандартам
- Task: "Какие клаузулы добавлены/удалены? Какие ключевые условия?"
- Usage: Режим "Clause Analysis", "Legal Diff"

### Persona 5: **Data Officer (Борис)**
- Role: Compliance / Audit
- Goal: Троить audit trail, отследить все изменения
- Task: "Кто что менял? Полная история для compliance"
- Usage: Экспорт в CSV/JSON, интеграция с audit systems

---

## 4. CORE PRODUCT ARCHITECTURE

### 4.1 Document Comparison Modes

**Система предлагает 5+ режимов сравнения в зависимости от задачи:**

#### **Mode 1: Line-by-Line Diff** (Классический)
Что это: Побайтовое сравнение, как в Git
- Красные строки: удалено
- Зелёные строки: добавлено
- Жёлтые строки: изменено
- Context lines: 3-5 строк до/после каждого изменения

Когда использовать: Когда нужно увидеть ВСЕ изменения, даже пунктуацию

**UI:**
- Side-by-side view (left: original, right: modified)
- Слайдер для выбора количества context lines
- Навигация между изменениями (↑/↓ кнопки)
- Статистика: +47 строк, -23 строки, 15 изменено

---

#### **Mode 2: Semantic Diff** (Умный анализ)
Что это: LLM анализирует смысл изменений, группирует по типам

Категории изменений:
- `DEFINITION_CHANGE`: "Определение условия изменилось"
- `NUMERICAL_CHANGE`: "Сумма изменилась с 100k на 150k"
- `TEMPORAL_CHANGE`: "Срок изменился с 30 на 60 дней"
- `SCOPE_CHANGE`: "Добавлена новая услуга/обязательство"
- `TERMINOLOGY`: "Переформулировка без изменения смысла"
- `STRUCTURE_CHANGE`: "Пункт переместился из раздела 3 в раздел 5"

Для каждого изменения:
- Оригинальный текст + новый текст
- LLM summary: "Что это означает?"
- Impact score: как это влияет на договор (0-100)
- Риск-флаг: CRITICAL/MAJOR/MINOR

Когда использовать: Понимание сути изменений, анализ влияния

**UI:**
- Изменения сгруппированы по типам
- Карточки с оригинальным/новым текстом
- Иконки: 🔴 CRITICAL, 🟡 MAJOR, 🟢 MINOR
- "Why does this matter?" explanation
- Filter by type или severity

---

#### **Mode 3: Impact Analysis** (Анализ влияния)
Что это: Фокусируется на ключевых параметрах, которые влияют на результат

Отслеживаемые параметры:
- **Financial:** суммы, скидки, штрафы, условия платежа
- **Temporal:** даты, сроки, deadlines, renewal terms
- **Obligations:** кто должен делать что, ответственность
- **Penalties:** штрафы, пени, санкции
- **Termination:** условия расторжения
- **Liability:** ограничения ответственности

Для каждого параметра показывает:
- Оригинальное значение → Новое значение
- Изменение в процентах (для чисел)
- "Is this significant?" (порог значимости)
- Business context: почему это важно

Когда использовать: Финансовый анализ, понимание деловых последствий

**UI:**
- Таблица: Параметр | Было | Стало | Изменение | Значимость
- Color-coded rows (зелёный/жёлтый/красный)
- Pie chart: распределение изменений по типам
- "What changed the most?" dashboard

---

#### **Mode 4: Clause-by-Clause Analysis** (Анализ клаузул)
Что это: Разбивает документ на логические клаузулы, сравнивает их

识распознавание клаузул:
- Определение (Definitions)
- Платёжные условия (Payment Terms)
- Ответственность (Liability)
- Конфиденциальность (Confidentiality)
- Интеллектуальная собственность (IP Rights)
- Расторжение (Termination)
- Прочие условия (Other Terms)

Для каждой клаузулы:
- Status: ADDED / REMOVED / MODIFIED / UNCHANGED
- Old clause text vs New clause text
- LLM-generated summary
- "Impact on overall agreement"

Когда использовать: Контроль соответствия, анализ структуры

**UI:**
- Список клаузул с иконками status
- Expandable: click → see full old vs new
- Timeline по клаузулам (какая клаузула на каком этапе менялась?)
- Export структурированной информации

---

#### **Mode 5: Legal Diff** (Юридический анализ)
Что это: Специализированный анализ для юристов

Фокус на:
- Обязательства vs Права
- Ограничения ответственности
- Исключения (exceptions)
- Условия вступления в силу
- Порядок разрешения споров
- Применяемое право (governing law)
- Force majeure
- Confidentiality & NDA

Для каждого элемента:
- Какова была формулировка
- Как она изменилась
- Юридические риски
- Рекомендации по смягчению

Когда использовать: Глубокий юридический анализ

**UI:**
- Список юридических элементов
- Risk matrix: вероятность × влияние
- Expert notes: почему это важно
- Comparison of legal frameworks (если разное применяемое право)

---

#### **Mode 6: Timeline Visualization** (Главная фишка)
Что это: Beautiful, interactive timeline всех версий документа

Компоненты:
- **Vertical Timeline** (как в Figma версии)
  - Каждая версия = точка на timeline
  - Дата загрузки
  - Кто загрузил (avatar)
  - Brief summary: "3 параметра изменились"
  - Иконки: 🔴 3 CRITICAL, 🟡 5 MAJOR

- **Interactive Features:**
  - Click на версию → открыть фулл-diff vs previous
  - Drag to compare any two versions
  - Hover → preview изменений (popup)
  - Zoom in/out: посмотреть на разные масштабы

- **Visual Indicators:**
  - Толщина линии = количество изменений (больше changes = толще)
  - Цвет точки = risk level (красный = CRITICAL, жёлтый = MAJOR)
  - Дугообразные связи между версиями (если merge произошёл)

- **Metadata на timeline:**
  - File name
  - Size
  - Page count
  - Change count
  - Key changes: "Payment: 90→30 days, Sum: 100k→150k"

Когда использовать: Обзор всей истории, понимание тренда изменений

**UI:**
```
Timeline View:
┌──────────────────────────────────────────┐
│  v1.0 (Jan 15)  →  v1.1 (Jan 16)  →  v1.2 (Jan 17) │
│     👤 Ivan        👤 Maria         👤 Finance      │
│     ●              ●                ●              │
│  🟢 MINOR      🟡 MAJOR         🔴 CRITICAL      │
│  (1 change)    (5 changes)      (3 changes!)     │
│                                                    │
│  ↓ Click любую версию для детального анализа    │
└──────────────────────────────────────────┘

Detail Panel:
┌──────────────────────────────────────────┐
│ Version 1.2 - Detailed Analysis           │
│                                            │
│ 🔴 CRITICAL CHANGES (3):                 │
│  • Payment days: 90 → 30                 │
│  • Total sum: 100k → 150k RUB            │
│  • Liability cap: REMOVED                │
│                                            │
│ 🟡 MAJOR CHANGES (5):                    │
│  • Added: Confidentiality clause         │
│  • Modified: Termination conditions      │
│  [see more...]                            │
└──────────────────────────────────────────┘
```

---

### 4.2 Document Upload & Management

**Описание:** Загрузка PDF, автоматическая обработка через OCR + LLM

**Требования:**
- [ ] Drag-and-drop загрузка одного или мультипла PDF
- [ ] Support форматов: PDF (основной), DOCX, TXT
- [ ] Автоматический OCR через сервис Chandra на Ubuntu
- [ ] Распознавание структуры документа (разделы, клаузулы, таблицы)
- [ ] Сохранение raw PDF + extracted text в БД
- [ ] Metadata: filename, upload_date, uploaded_by, file_size, page_count, hash
- [ ] Виртуальная папка (folder/project) для группировки документов
- [ ] Soft delete (архивирование) документов
- [ ] Full-text search по контенту документов
- [ ] Automatic version detection: если загрузить файл с похожим именем, система предложит добавить как версию

**UI/UX:**
- Экран: Document Library (grid/list view с preview)
- Upload zone: drag-and-drop или выбор файла
- Документ card: thumbnail PDF preview, metadata, last_modified
- Batch select для bulk operations

**Backend API:**
```
POST /api/v1/documents/upload
POST /api/v1/documents/batch-upload
GET /api/v1/documents
GET /api/v1/documents/{id}
DELETE /api/v1/documents/{id}
PUT /api/v1/documents/{id}/archive
GET /api/v1/documents/search?q=...
GET /api/v1/documents/{id}/versions
```

---

### 4.3 Smart Semantic Diff Engine

**Описание:** Сердце платформы — умный анализ разницы между версиями

**Требования:**

#### 4.3.1 Diff Algorithm (Multi-Layer)

**Layer 1: Text Tokenization**
- Разбить текст на clauses/paragraphs/sentences
- Preserving document structure
- Identify sections (headers, numbered lists, tables)

**Layer 2: Semantic Embedding**
- Embed каждый блок текста через sentence-transformers (local)
- Создать embedding vectors для быстрого поиска похожих блоков
- Сравнение: cosine similarity + Levenshtein distance

**Layer 3: Change Classification**
```
DELETED      → текст был в v1, нет в v2
ADDED        → текста не было в v1, есть в v2
MODIFIED     → текст изменился (редактирование слов)
MOVED        → текст на месте, но переместился в структуре
REWORDED     → смысл тот же, слова другие (semantic similarity > 0.9)
SEMANTIC_SHIFT → смысл изменился (similarity < 0.7)
```

**Layer 4: Critical Parameter Detection**
- Regex для выявления:
  - Финансовые суммы: `\d+(\.\d{2})?\s*(USD|RUB|EUR|k|m)`
  - Даты: `\d{1,2}\.\d{1,2}\.\d{4}` или ISO
  - Сроки: `\d+\s*(дня|дней|месяца|месяцев|лет|years|months|days)`
  - Проценты: `\d+(\.\d+)?\s*%`
  - Ключевые слова: "ответственность", "штраф", "риск", "обязательство", "запрещается", "должен"

**Layer 5: Impact Scoring**
- Для каждого изменения: how significant is it?
- Threshold по типу:
  - Финансовые: если > 10% от суммы = CRITICAL
  - Временные: если < 30 дней = CRITICAL
  - Структурные: добавление/удаление раздела = CRITICAL
  - Текстовые: переформулировка = MINOR

#### 4.3.2 Comparison Output

```json
{
  "document_id_v1": "doc_123_v1",
  "document_id_v2": "doc_123_v2",
  "comparison_id": "comp_456",
  "generated_at": "2026-01-19T21:00:00Z",
  
  "summary": {
    "total_changes": 47,
    "critical_changes": 3,
    "major_changes": 12,
    "minor_changes": 32,
    "similarity_score": 0.78
  },
  
  "changes": [
    {
      "id": "change_001",
      "type": "SEMANTIC_SHIFT",
      "classification": "NUMERICAL_CHANGE",
      "severity": "CRITICAL",
      "location": "section_3.2",
      "original_text": "Payment shall be due within 90 days from invoice date",
      "new_text": "Payment shall be due within 30 days from invoice date",
      "ai_summary": "Payment deadline significantly shortened from 90 to 30 days",
      "impact_score": 95,
      "business_context": "This dramatically reduces credit period, increasing cash flow pressure"
    },
    {
      "id": "change_002",
      "type": "ADDED",
      "classification": "SCOPE_CHANGE",
      "severity": "MAJOR",
      "location": "section_5_new",
      "original_text": null,
      "new_text": "Confidentiality: All proprietary information must be kept confidential for 3 years after termination",
      "ai_summary": "New confidentiality obligations added",
      "impact_score": 67,
      "business_context": "Adds post-termination confidentiality requirements"
    }
  ],
  
  "financial_impact": {
    "changes": [
      { "parameter": "Total Amount", "original": 1000000, "new": 1500000, "currency": "RUB", "change_percent": 50 },
      { "parameter": "Payment Days", "original": 90, "new": 30, "unit": "days", "change_percent": -67 }
    ]
  },
  
  "clauses": {
    "status": {
      "added": ["Confidentiality", "Force Majeure"],
      "removed": ["Warranty Period"],
      "modified": ["Liability Cap", "Termination"]
    }
  }
}
```

**Backend API:**
```
POST /api/v1/documents/{id1}/compare/{id2}
  Query: mode=line-by-line|semantic|impact|clause|legal|timeline
  → Returns: detailed comparison result

GET /api/v1/documents/{id1}/compare/{id2}
  → Retrieve previously generated comparison

GET /api/v1/documents/{id}/versions
  → List all versions for timeline

GET /api/v1/documents/{id1}/semantic-diff
  → Semantic-specific comparison
```

---

### 4.4 Automatic Merge (Multi-Way)

**Описание:** Автоматическое слияние нескольких версий документа

**Требования:**

#### 4.4.1 Three-Way Merge
- Input: base version + 2 modified versions
- Алгоритм: каждый блок анализируется независимо
- Если обе версии меняют один блок по-разному = CONFLICT
- Non-conflicting changes: автоматически применяются обе
- Output: merged document + conflict markers

#### 4.4.2 Multi-Way Merge (N версий)
- Загрузить 2-10 вариантов одного документа
- Система ищет consensus version:
  - Для каждого блока: какой вариант встречается чаще?
  - Если одинаково часто: конфликт
- Merge strategies:
  - `CONSENSUS`: голосование (most common variant wins)
  - `MOST_RECENT`: последняя версия
  - `MANUAL`: пользователь выбирает для каждого конфликта

#### 4.4.3 Conflict Resolution UI

**Когда конфликтов < 5:**
- Inline resolution (все на одной странице)
- Для каждого конфликта: 2-3 варианта
- Пользователь кликает на нужный вариант

**Когда конфликтов > 5:**
- Wizard-like interface
- Шаг за шагом: conflict 1 of 7
- Preview merged result after each step

**UI:**
```
Conflict Resolution:
┌────────────────────────────────────┐
│ Merge Conflicts: 3 of 7            │
├────────────────────────────────────┤
│ Conflict #3: Payment Terms         │
│                                    │
│ Version A (Moscow):               │
│ ☐ Payment: 30 days, 5% discount   │
│                                    │
│ Version B (SPB):                  │
│ ☐ Payment: 45 days, 3% discount   │
│                                    │
│ Version C (Ekb):                  │
│ ☒ Payment: 30 days, 0% discount   │
│                                    │
│ Consensus: Version A (picked by 2) │
│                                    │
│ [Back] [Next] [Preview Result]    │
└────────────────────────────────────┘
```

**Backend API:**
```
POST /api/v1/documents/merge
  Body: { 
    document_ids: [id1, id2, id3],
    merge_strategy: "CONSENSUS|MOST_RECENT|MANUAL",
    base_version?: id_base
  }
  → Returns: { merged_content, conflicts: [...], preview_url }

POST /api/v1/documents/merge/{merge_id}/resolve
  Body: { conflict_index, chosen_variant_index }
  → Update merge

POST /api/v1/documents/merge/{merge_id}/finalize
  → Create new document with merged content
```

---

### 4.5 Intelligent Timeline Visualization

**Описание:** Beautiful, интерактивная timeline всех версий

**Компоненты:**

1. **Main Timeline View**
   - Вертикальная линия (как в истории коммитов Git или Figma версии)
   - Каждая версия = узел (node) на timeline
   - Подключено к левой стороне экрана

2. **Node Information (при hover/click)**
   - File name
   - Upload date & time
   - Uploaded by (avatar + name)
   - File size & page count
   - Quick stats: "15 changes, 3 CRITICAL, 5 MAJOR"
   - Visualization: радар или pie chart изменений

3. **Connectors Between Versions**
   - Если версия A → версия B: простая линия
   - Если версия = merge нескольких: дугообразная линия из всех родителей
   - Color-coded: зелёный (minor), жёлтый (major), красный (critical)

4. **Interaction Features**
   - Click версию → открыть детальный diff vs previous
   - Ctrl+Click две версии → открыть diff между ними
   - Drag version → reorder (если это логический порядок)
   - Search/filter timeline по date, uploader, risk level

5. **Density Options**
   - Compact: только даты и иконки
   - Normal: +file names, +change counts
   - Detailed: +full summaries, +file sizes

**Visual Design (Inspiration: Figma Version History)**
```
Timeline Example:

                v1.0 (Jan 15)         Created by Ivan
                    •
                    │ 🟢 MINOR (1 change)
                    │
                v1.1 (Jan 16)         Created by Maria
                    •
                    │ 🟡 MAJOR (5 changes)
                    │
          ╱─────────•─────────╲        Merged from Finance + Legal
         /          v1.2      \
    v1.2a (Jan 17) │ v1.2b (Jan 17)   Two branches
        •          │          •
        │ 🔴       │          │ 🟡
        │CRITICAL  │          │MAJOR
        │ (3)      │          │ (4)
        └──────────•──────────┘
                v1.3 (Jan 18)         Merged: Final version
                    •
                    │
```

**Backend API:**
```
GET /api/v1/documents/{id}/timeline
  → Returns: timeline data structure with all versions

GET /api/v1/documents/{id}/timeline/compact
  → Returns: lightweight version for performance

GET /api/v1/documents/{id}/timeline/compare-path
  Query: from={version_id}&to={version_id}
  → Returns: path of changes from one version to another
```

---

### 4.6 Entity Extraction & Structured Export

**Описание:** Парсинг документа в структурированные данные

**Требования:**

#### 4.6.1 Contract Entity Extraction

LLM (GPT-20B-oss) выявляет:
- `parties`: стороны договора (компания, ФИО, адреса, реквизиты)
- `effective_date`: дата начала
- `expiration_date`: дата окончания
- `renewal_term`: условия продления
- `payment_terms`: условия оплаты (сумма, срок, способ, реквизиты)
- `penalties`: штрафы, неустойки, размеры
- `termination_clause`: условия расторжения, notice period
- `liability`: ограничения ответственности, insurance
- `governing_law`: какое право применяется
- `dispute_resolution`: порядок разрешения споров
- `key_obligations`: основные обязательства сторон
- `key_rights`: основные права сторон
- `confidentiality`: требования к конфиденциальности
- `ip_ownership`: владение интеллектуальной собственностью

#### 4.6.2 Structured Output & Export

```json
{
  "document_id": "doc_123",
  "extraction_timestamp": "2026-01-19T21:00:00Z",
  "confidence": 0.94,
  "entities": {
    "parties": [
      {
        "type": "legal_entity",
        "name": "ООО Пример",
        "registration_number": "1234567890",
        "address": "Москва, ул. Примерная 1",
        "contact_person": "Иван Иванов",
        "email": "ivan@example.ru"
      }
    ],
    "dates": {
      "effective_date": "2026-01-20",
      "expiration_date": "2027-01-20",
      "renewal_term": "12 months auto-renew with 30 days notice"
    },
    "payment_terms": {
      "currency": "RUB",
      "total_amount": 1500000,
      "payment_schedule": [
        { "due_date": "2026-02-20", "amount": 500000, "note": "Advance" },
        { "due_date": "2026-04-20", "amount": 500000 },
        { "due_date": "2026-06-20", "amount": 500000 }
      ],
      "payment_method": "Bank transfer to account: ...",
      "early_payment_discount": "5% if paid within 10 days"
    },
    "penalties": [
      {
        "type": "late_payment_fine",
        "rate": "0.5% per day",
        "max_cap": "10% of payment"
      }
    ]
  }
}
```

#### 4.6.3 Export Formats
- [ ] JSON: полная структурированная информация
- [ ] CSV: таблица с key-value
- [ ] iCal: календарные события (dates, deadlines)
- [ ] PDF Report: красиво оформленный отчёт
- [ ] Excel: структурированные листы по типам сущностей

**UI/UX:**
- Экран: Document Summary
- Карточки: Parties, Dates, Payment Terms, Penalties, Obligations
- Each entity editable (если extraction неточна)
- Кнопки: "Export to JSON", "Add to Calendar", "Export PDF Report"

**Backend API:**
```
GET /api/v1/documents/{id}/extract
  → Returns: structured JSON with all entities

PUT /api/v1/documents/{id}/extract/{entity_type}/{entity_id}
  → Update extracted data if incorrect

GET /api/v1/documents/{id}/extract/export
  Query: format=json|csv|ical|pdf
  → Returns: formatted export
```

---

### 4.7 Risk Analysis & Critical Change Detection

**Описание:** Автоматический анализ рисков в документе и изменениях

**Требования:**

#### 4.7.1 Risk Dimensions

**Financial Risks:**
- Сумма платежа: флаг если > 500k RUB
- Платежные условия: флаг если > 60 дней
- Штрафы: флаг если штраф > 5% суммы контракта
- Дисконты: флаг если discount > 20%
- Currency risks: флаг если контракт в иностранной валюте + нет hedge

**Temporal Risks:**
- Сроки исполнения: флаг если < 30 дней (tight timeline)
- Пени за просрочку: флаг если > 1% в день
- Автоматическое продление: флаг если нет явного opt-out
- Renewal notice: флаг если notice period < 30 дней

**Legal Risks:**
- Индемнификация: есть ли ограничения на ответственность
- Liability cap: флаг если нет или > contract value (слишком высоко)
- Arbitration clause: флаг если нет альтернативы суду (риск)
- Governing law: иностранное право (complexity)
- IP ownership: флаг если неясно, кому принадлежит IP
- Non-compete: флаг если ограничения слишком строгие

**Operational Risks:**
- Insurance requirements: есть ли обязательное страхование, какой размер
- Performance guarantees: есть ли гарантии, какие SLA
- Compliance requirements: references к regulations (GDPR, SOC 2, ISO27001)
- Force majeure: есть ли protecting clause

#### 4.7.2 Change-Based Risk Detection

Когда сравниваем две версии:
- Какие параметры изменились?
- Направление: лучше или хуже?
- Magnitude: насколько значимо?

```
Financial Risk Analysis:
- Payment days: 90 → 30 = RED (cash flow pressure)
- Total sum: 100k → 150k = RED (cost increase)
- Discount: 5% → 0% = YELLOW (less favorable)

Legal Risk Analysis:
- Liability cap: 2x sum → REMOVED = RED (unlimited liability!)
- Arbitration: yes → no = RED (must go to court now)
```

#### 4.7.3 Risk Scoring

- Каждый риск: score (0-100)
- Overall risk score: weighted average
- Risk level: GREEN (0-30), YELLOW (31-70), RED (71-100)
- Change in risk between versions: was GREEN, now RED

**UI/UX:**
```
Risk Dashboard:

🔴 RED RISKS (3):
  • Liability cap removed (score: 95)
  • Payment days reduced to 30 (score: 88)
  • Currency: RUB with no hedge (score: 75)

🟡 YELLOW RISKS (5):
  • Renewal auto-renews without opt-out (score: 62)
  [more...]

🟢 GREEN (8):
  • Clear arbitration clause (score: 15)
  [...]

Overall Risk: 72/100 (YELLOW)
Risk Trend: ↑ (increased by 25 points from v1.0)
```

**Backend API:**
```
GET /api/v1/documents/{id}/risk-analysis
  → Returns: { risks: [...], overall_score, level, trend }

GET /api/v1/documents/{id1}/risk-comparison/{id2}
  → Returns: risk diff between two versions

POST /api/v1/documents/{id}/risk-assessment/acknowledge
  Body: { risk_id, action: "accept|mitigate|escalate" }
  → Track risk decisions
```

---

## 5. ADVANCED FEATURES (Phase 2)

### 5.1 Clause Library & Pattern Matching
- Создать library типовых клаузул (standard templates)
- Автоматическое распознавание клаузул между версиями
- "Clauses matched: 87/90, new clauses: 2, removed: 1"
- Suggest standard clause if missing

### 5.2 Compliance Checking Against Template
- Upload эталонный контракт (template)
- System проверяет: все ли обязательные клаузулы есть?
- Flags: missing clauses, non-standard terms vs template
- Compliance score (%)

### 5.3 Document Repository Analytics
- Сколько версий в месяц?
- Какие разделы часто меняются?
- Среднее количество итераций для согласования?
- Тренды: платежные условия становятся жестче?

### 5.4 Semantic Versioning
- Automatic versioning: CRITICAL, MAJOR, MINOR
- "v1.0 → v1.1" вместо "contract_v1_final_v2.pdf"
- Semantic version bumping rules

### 5.5 Integration Layer
- Email alerts: "Important changes in your contracts"
- Slack notifications: post changes to channel
- Webhook для custom integrations
- Calendar export (iCal, Google Calendar) for key dates

### 5.6 Comparison History & Bookmarks
- Save comparisons для later reference
- Bookmark важные changes
- Create comparison templates для часто сравниваемых документов

---

## 6. TECHNICAL ARCHITECTURE

### 6.1 Tech Stack

**Frontend:**
- React 18 + TypeScript
- State management: Zustand
- Styling: Tailwind CSS + ShadcnUI
- PDF viewer: react-pdf + custom annotations
- Diff viewer: custom React component (для timeline, semantic diff)
- Timeline: custom D3.js или Recharts
- Real-time: Socket.io client
- Forms: React Hook Form + Zod

**Backend:**
- Framework: FastAPI (Python 3.11+)
- ORM: SQLAlchemy + Alembic
- Database: PostgreSQL 15+ с pgvector для embeddings
- Cache: Redis (для кеша дифф результатов)
- Message queue: Celery + Redis (async processing)
- Document processing:
  - OCR: Chandra (custom Ubuntu svc)
  - LLM: GPT-20B-oss (local, Ubuntu)
  - Embeddings: sentence-transformers (local, fast)
  - Text processing: difflib, Levenshtein
- Storage: S3-compatible (MinIO or AWS S3)

**DevOps:**
- Containerization: Docker + Docker Compose
- CI/CD: GitHub Actions
- Monitoring: Prometheus + Grafana
- Logging: structured logs to file or ELK
- Deployment: Ubuntu 22.04 LTS

### 6.2 Multi-Tenancy Architecture

**Data Isolation:**
- Row-level security (RLS) в PostgreSQL
- JWT tokens содержат tenant_id
- Middleware автоматически фильтрует по tenant

**Database Schema (Core):**

```sql
-- Tenants
CREATE TABLE tenants (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  created_at TIMESTAMP,
  subscription_tier ENUM('FREE', 'PRO', 'ENTERPRISE')
);

-- Documents
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  name VARCHAR(255),
  description TEXT,
  file_path VARCHAR(512),
  file_size INTEGER,
  page_count INTEGER,
  uploaded_by UUID REFERENCES users(id),
  uploaded_at TIMESTAMP,
  status ENUM('DRAFT', 'PROCESSING', 'READY', 'ERROR'),
  content_hash VARCHAR(256),
  extracted_text TEXT,
  embeddings VECTOR(1536)
);

-- Versions (same document, different versions)
CREATE TABLE document_versions (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id),
  version_number INTEGER,
  content TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP,
  parent_version_id UUID REFERENCES document_versions(id)
);

-- Comparisons (cached diff results)
CREATE TABLE document_comparisons (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  version1_id UUID REFERENCES document_versions(id),
  version2_id UUID REFERENCES document_versions(id),
  comparison_mode VARCHAR(50),
  result JSONB,
  created_at TIMESTAMP,
  created_by UUID REFERENCES users(id)
);

-- Merges
CREATE TABLE document_merges (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  source_version_ids UUID[],
  merge_strategy VARCHAR(50),
  status ENUM('IN_PROGRESS', 'COMPLETED', 'FAILED'),
  result_version_id UUID REFERENCES document_versions(id),
  conflicts_count INTEGER,
  created_at TIMESTAMP
);

-- Extracted entities
CREATE TABLE extracted_entities (
  id UUID PRIMARY KEY,
  document_version_id UUID REFERENCES document_versions(id),
  entity_type VARCHAR(100),
  entity_data JSONB,
  confidence FLOAT,
  extracted_at TIMESTAMP
);

-- Risk assessments
CREATE TABLE risk_assessments (
  id UUID PRIMARY KEY,
  document_version_id UUID REFERENCES document_versions(id),
  risk_dimension VARCHAR(100),
  risk_type VARCHAR(100),
  risk_score INTEGER,
  risk_level ENUM('GREEN', 'YELLOW', 'RED'),
  description TEXT,
  assessed_at TIMESTAMP
);

-- Audit logs
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  user_id UUID REFERENCES users(id),
  resource_type VARCHAR(100),
  resource_id UUID,
  action VARCHAR(100),
  created_at TIMESTAMP
);
```

### 6.3 API Structure

```
/api/v1/
├── /auth/
│   ├── POST /login
│   ├── POST /register
│   └── POST /refresh-token
├── /documents/
│   ├── POST /upload
│   ├── POST /batch-upload
│   ├── GET /
│   ├── GET /{id}
│   ├── DELETE /{id}
│   ├── PUT /{id}/archive
│   ├── GET /search
│   ├── GET /{id}/versions
│   ├── GET /{id}/timeline
│   └── WebSocket /stream/{id}
├── /compare/
│   ├── POST /{id1}/vs/{id2}
│   │   Query: mode=line-by-line|semantic|impact|clause|legal|timeline
│   ├── GET /history
│   ├── POST /save-bookmark
│   └── GET /bookmarks
├── /merge/
│   ├── POST /
│   │   Body: { document_ids: [...], merge_strategy: "..." }
│   ├── GET /{id}/status
│   ├── POST /{id}/resolve-conflict
│   ├── POST /{id}/finalize
│   └── GET /{id}/conflicts
├── /extract/
│   ├── GET /documents/{id}
│   ├── PUT /documents/{id}/{entity_type}/{entity_id}
│   └── GET /documents/{id}/export?format=json|csv|ical|pdf
├── /risk/
│   ├── GET /documents/{id}
│   ├── GET /compare/{id1}/{id2}
│   └── POST /acknowledge
└── /admin/
    ├── GET /users
    ├── GET /audit-logs
    └── GET /analytics
```

### 6.4 Processing Pipeline

```
[Upload PDF]
    ↓
[OCR via Chandra]
    ↓
[Extract raw text]
    ↓
[Generate embeddings via sentence-transformers]
    ↓
[LLM entity extraction + risk analysis] (async via Celery)
    ↓
[Store in DB + S3]
    ↓
[Ready for comparison]
```

---

## 7. USER FLOWS

### Flow 1: Quick Comparison (2 contracts)

```
1. User opens Documents page
2. Selects contract_v1.pdf and contract_v2.pdf
3. Clicks "Compare"
4. System shows comparison mode selector:
   - Line-by-Line (classic diff)
   - Semantic (what changed in meaning)
   - Impact (financial/risk changes)
   - Clause (structural analysis)
   - Legal (for lawyers)
   - Timeline (all versions history)
5. User selects "Semantic"
6. System loads beautiful diff view:
   - Original vs Modified side-by-side
   - Changes grouped by type (DEFINITION_CHANGE, NUMERICAL_CHANGE, etc.)
   - Color-coded severity (🔴 CRITICAL, 🟡 MAJOR, 🟢 MINOR)
7. User can click each change to see AI explanation
8. User scrolls through or uses navigation
```

### Flow 2: Merge Multiple Versions

```
1. User has 5 versions of same contract
2. Uploads all 5 to same "Contract Negotiation" folder
3. System auto-detects: "These look like versions of same document"
4. User clicks "Merge" button
5. Selects merge strategy: "CONSENSUS" (majority wins)
6. System processes:
   - Compares all 5 versions
   - Finds common blocks (apply to merged automatically)
   - Finds conflicts (3 blocks where versions differ)
7. UI shows conflict resolution wizard:
   - Conflict 1 of 3: Payment Terms
   - Shows 3 options (from 3 different versions)
   - User selects winning option
8. Repeats for conflicts 2, 3
9. Preview merged result
10. Click "Create Merged Version"
11. New document created, timeline updated
```

### Flow 3: Timeline Deep Dive

```
1. User opens "Contracts by Project" folder
2. Selects one contract (which has 8 versions over 2 months)
3. Clicks "View Timeline"
4. Beautiful vertical timeline appears:
   - v1.0 (Jan 5) - Ivan
   - v1.1 (Jan 7) - Maria
   - v1.2 (Jan 10) - Finance (merged from 2 branches)
   - v2.0 (Jan 20) - Legal rewrite
   - v2.1 (Jan 22) - Final approved
5. User hovers over v1.2 → sees popup:
   - "Merged version"
   - "15 changes, 3 CRITICAL"
   - Key changes: "Payment 90→30 days, Sum 100k→150k"
6. User clicks v1.2 → opens detailed view
7. Can see exact diff between v1.1 and v1.2
8. Or can drag to compare v1.0 vs v2.1 directly
```

### Flow 4: Risk Analysis

```
1. User uploads new contract
2. System async processes:
   - OCR + extraction
   - Entity extraction
   - Risk analysis
3. After processing, user opens document
4. See "Risk Summary" card:
   - Overall score: 72/100 (YELLOW)
   - 3 RED risks, 5 YELLOW risks
5. User clicks each risk to see:
   - What it is
   - Why it matters
   - How to mitigate
6. User compares two versions:
   - v1.0: risk score 45 (GREEN)
   - v1.1: risk score 72 (YELLOW)
   - "Risk increased by 27 points"
   - Show which changes caused the risk increase
```

---

## 8. NON-FUNCTIONAL REQUIREMENTS

### 8.1 Performance
- [ ] Document upload: < 10s for typical 10-page PDF
- [ ] Diff generation (semantic mode): < 5s for comparing 2 documents
- [ ] Timeline generation: < 2s even for 20 versions
- [ ] Search: < 2s for full-text search
- [ ] API response: < 200ms for typical queries
- [ ] Entity extraction: < 30s per document (async)

### 8.2 Scalability
- [ ] Support 10+ tenants initially (roadmap: 1000+)
- [ ] Support 100+ users per tenant
- [ ] Support 10,000 documents per tenant
- [ ] Horizontal scaling: stateless backend
- [ ] Database: read replicas for scaling reads

### 8.3 Security
- [ ] Authentication: OAuth 2.0 + JWT
- [ ] Encryption: TLS 1.3
- [ ] Row-level security (RLS) in PostgreSQL
- [ ] Audit logging: all actions logged
- [ ] GDPR compliance: data retention, right to deletion

### 8.4 Availability
- [ ] Uptime: 99% SLA
- [ ] Backup: daily automatic
- [ ] Disaster recovery: RTO 4h, RPO 1h

### 8.5 Reliability
- [ ] Graceful error handling
- [ ] Retry logic: exponential backoff
- [ ] Circuit breaker for external services

---

## 9. ACCEPTANCE CRITERIA (MVP)

- [ ] Document upload + OCR processing
- [ ] All 6 comparison modes functional (Line-by-Line, Semantic, Impact, Clause, Legal, Timeline)
- [ ] Beautiful timeline visualization with interactivity
- [ ] 3-way merge algorithm working
- [ ] Multi-way merge with conflict detection
- [ ] Semantic diff with AI summaries
- [ ] Risk analysis for financial/legal/temporal dimensions
- [ ] Entity extraction for key contract fields
- [ ] Multi-tenancy with data isolation
- [ ] Authentication (JWT)
- [ ] API documented (Swagger/OpenAPI)
- [ ] Performance targets met
- [ ] Unit tests: 70%+ coverage
- [ ] E2E tests: critical flows

---

## 10. ROADMAP

### Q1 2026 (Current)
- ✅ MVP: all 6 comparison modes
- ✅ Beautiful timeline
- ✅ Merge algorithms
- ✅ Risk analysis
- ⚙️ Beta testing

### Q2 2026
- Clause library & compliance checking
- Document analytics dashboard
- Semantic versioning
- Performance optimization

### Q3 2026
- Integration layer (Slack, Email, Webhooks)
- Advanced comparison templates
- Repository analytics

### Q4 2026
- Enterprise features
- Advanced security (MFA, SSO)

---

## 11. SUCCESS METRICS (KPIs)

1. **Time to Understand Changes**
   - Baseline: 30 minutes per contract
   - Target: 5 minutes
   - Measurement: user task completion time

2. **Comparison Accuracy**
   - Target: 95% of changes correctly identified
   - Measurement: user feedback accuracy rating

3. **Merge Success Rate**
   - Target: 80% without manual intervention
   - Measurement: auto-merged / total merges

4. **System Performance**
   - Semantic diff: < 5s
   - Timeline: < 2s
   - Uptime: 99%

---

## 12. GLOSSARY

| Термин | Описание |
|--------|---------|
| **Diff** | Различия между двумя версиями |
| **Semantic diff** | Умный diff, который понимает смысл |
| **Impact Analysis** | Анализ влияния изменений на бизнес |
| **Merge** | Объединение нескольких версий |
| **Timeline** | История всех версий документа |
| **Risk Score** | Числовая оценка риска (0-100) |
| **Entity Extraction** | Парсинг в структурированные данные |
| **Tenant** | Организация/компания |

---

**End of PRD**

Успехов! 🚀
