# WhatsApp Chat Archive

Статический HTML-просмотр экспортов чатов WhatsApp с медиа.

## Страницы

- `index.html` — главная, список чатов
- `parinton.html` — чат с +66 91 824 1010 (~PARINTON)
- `beach-case.html` — группа «Andrey Freedom — beach case»

## Структура

- `build_chat.py` — генератор HTML из `_chat.txt`
- `WhatsApp Chat - +66 91 824 1010/` — экспорт первого чата (txt + медиа)
- `WhatsApp Chat - Andrey Freedom  beach case/` — экспорт второго чата
- `netlify.toml` — конфиг деплоя

## Регенерация

```bash
python3 build_chat.py
```

Генератор читает `_chat.txt` в каждой папке из списка `CHATS` в `build_chat.py`
и пересобирает `index.html` + по странице на чат.

## Деплой

Сайт статический. Netlify хостит файлы из корня (`publish = "."`) — push в `main`
триггерит авто-деплой.
