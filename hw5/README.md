## Запуск

1. Запустить сервисы:
```bash
docker-compose up -d
```

2. Применить миграцию:
```bash
psql -h localhost -U user -d moderationservices -f migrations/add_moderation_results.sql
```

3. Установить зависимости:
```bash
pip -m install -r requirements.txt
```

4. Запустить API:
```bash
python main.py
```

1. Запустить воркер:
```bash
python -m app.workers.moderation_worker
```
