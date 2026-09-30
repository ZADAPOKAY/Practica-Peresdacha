# Агрегатор access-логов Apache

Читает access-логи Apache (форматы Common и Combined), сохраняет в MySQL и показывает
через консоль, веб-интерфейс и JSON API.

## Что понадобится
- Python 3.10+
- Docker (для MySQL) 

## Запуск

```bash
# 1. Зависимости
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. База данных (подождите ~20 секунд, пока MySQL стартует)
docker compose up -d

# 3. Создайте пользователя для входа
python -m app create-user admin

# 4. Разберите логи (в проекте есть пример в logs_sample/)
python -m app parse

# 5. Запустите веб-интерфейс
python -m app runserver
```
Откройте http://127.0.0.1:5000 и войдите под созданным пользователем.

## Настройки
Всё в `config.yaml`: путь к логам (`logs.dir`), маска файлов (`logs.mask`), доступ к БД,
адрес и порт сервера, секрет для сессий. Другой файл: `python -m app --config /путь/config.yaml ...`

## Консоль
```bash
python -m app show                                   # последние записи
python -m app show --group-by ip                     # группировка по IP
python -m app show --group-by date --from 2026-05-10 --to 2026-05-11
python -m app show --ip 10.0.0.5 --keyword login
```
Даты: `ГГГГ-ММ-ДД` или `ГГГГ-ММ-ДД ЧЧ:ММ`. `--to` с датой без времени включает весь этот день.
Время хранится в UTC.

## JSON API
Нужна авторизация (сначала войдите в браузере; cookie сессии используется автоматически).

| Запрос | Описание |
|---|---|
| `GET /api/logs?from=2026-05-10&to=2026-05-12` | записи за промежуток |
| `GET /api/logs?ip=10.0.0.5` | фильтр по IP |
| `GET /api/logs?group_by=ip` / `group_by=date` | группировка |
| `GET /api/logs?keyword=login&limit=50&offset=0` | поиск по URL, постраничность (limit ≤ 1000) |
| `POST /api/parse` | запустить разбор логов |

Ошибки возвращаются как `{"error": "текст"}` с кодами 400/401/500.

## Разбор по cron
Каждые 10 минут (`crontab -e`, пути замените на свои):
```
*/10 * * * * cd /путь/к/проекту && /путь/к/проекту/venv/bin/python -m app parse >> cron.log 2>&1
```
Повторный разбор безопасен: уже сохранённые строки не дублируются (по хешу строки).
Строки, которые не удалось распознать, пишутся в `parse_errors.log`.

## Структура
```
app/config.py    чтение настроек
app/db.py        модели MySQL и запросы
app/parser.py    разбор логов
app/web.py       Flask: авторизация, страницы, API
app/__main__.py  консольные команды
app/templates/   HTML
```
