# Используем полный образ Python (не slim, как вы просили)
FROM python:3.10

# Устанавливаем рабочую директорию в /app
WORKDIR /app

# Сначала копируем зависимости для кэширования слоев
# Предполагаем, что requirements.txt лежит в папке backend
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Копируем всё содержимое проекта (и backend, и frontend)
# Это важно, так как main.py обращается к папке ../frontend
COPY . .

# Переходим в папку с бэкендом для запуска
WORKDIR /app/backend

# Порт 5055 уже прописан в вашем main.py
EXPOSE 5055

# Запуск через python main.py (как в вашем .bat файле)
CMD ["python", "main.py"]