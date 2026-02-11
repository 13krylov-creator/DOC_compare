# Локальный запуск DocumentMerge Platform

## Требования

- **Python 3.10+**
- **Windows** (инструкция для Windows, для Linux аналогично через `source`)

---

## 1. Создать виртуальное окружение

```bash
cd "c:\УГМК\DocumentMerge Platform"

# Создать venv (если ещё нет)
python -m venv .venv

# Активировать
.venv\Scripts\activate
```

После активации в терминале появится `(.venv)` перед строкой.

---

## 2. Установить зависимости

```bash
pip install -r backend\requirements.txt
```

---

## 3. Запустить сервер

```bash
cd backend
python main.py
```

Или из корня проекта:

```bash
python run_server.py
```

Сервер запустится на **http://localhost:5055**

---

## 4. Открыть в браузере

Перейти на [http://localhost:5055](http://localhost:5055)

Доступны 3 вкладки:
- **Сравнение** — сравнение документов
- **Слияние** — объединение документов
- **Обезличивание** — анонимизация документов

---

## Структура проекта

```
DocumentMerge Platform/
├── backend/
│   ├── main.py                 # Точка входа FastAPI
│   ├── config.py               # Конфигурация
│   ├── requirements.txt        # Зависимости Python
│   ├── routers/
│   │   ├── auth.py             # Аутентификация
│   │   ├── compare.py          # Сравнение
│   │   ├── merge.py            # Слияние
│   │   ├── anonymizer.py       # Обезличивание (NEW)
│   │   └── ...
│   ├── anonymizer_core/        # Ядро обезличивания
│   └── anonymizer_utils/       # Утилиты обезличивания
├── frontend/
│   ├── index.html              # Главная страница (3 вкладки)
│   ├── styles.css              # Стили
│   └── app.js                  # Логика фронтенда
├── .venv/                      # Виртуальное окружение
├── run_server.py               # Скрипт запуска
└── start_server.bat            # Запуск через .bat
```

---

## Переменные окружения (опционально)

Можно создать файл `backend/.env`:

```env
ML_HOST_GPT=10.109.50.250:1212
ML_HOST_VISION=10.109.50.250:8880
UPLOAD_DIR=./uploads
FILE_RETENTION_DAYS=7
```

Без `.env` будут использоваться значения по умолчанию.
