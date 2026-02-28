# Голосовой ассистент кафедры

Speech-to-speech голосовой ассистент для университетской кафедры на Raspberry Pi 5 (4GB RAM). Полностью оффлайн, open-source.

**Пользователь нажимает кнопку (или говорит "Окей кафедра") → задаёт вопрос голосом → ассистент отвечает голосом**, используя базу знаний из документов кафедры.

## Архитектура

```
Кнопка / Wake word
       │
       ▼
  ASR (Vosk)         — русская речь → текст
       │
       ▼
  RAG pipeline        — поиск по документам + генерация ответа
  ├─ Embed (rubert-tiny2)
  ├─ Search (FAISS)
  └─ Generate (template / Vikhr-1B LLM)
       │
       ▼
  TTS (Piper)         — текст → русская речь
       │
       ▼
  Динамик
```

## Стек технологий

| Компонент | Технология | RAM | Назначение |
|-----------|-----------|-----|------------|
| ASR | Vosk (vosk-model-small-ru-0.22) | ~300 MB | Распознавание русской речи |
| Wake word | Vosk keyword spotting | 0 (reuse) | Детекция "Окей кафедра" |
| Embeddings | rubert-tiny2 (ONNX) | ~150 MB | Vectorization текста |
| Vector store | FAISS + SQLite | ~15 MB | Хранение и поиск чанков |
| LLM (MVP) | Template-based | 0 | Формирование ответа |
| LLM (Enhanced) | Vikhr-Llama-3.2-1B Q3_K_M | ~1000 MB | Генерация ответа через LLM |
| TTS | Piper (ru_RU-irina-medium) | ~150 MB | Синтез русской речи |

**Пиковое потребление RAM**: ~2.0 GB из 4.0 GB (последовательная загрузка моделей).

## Требования

### Железо
- Raspberry Pi 5 (4 GB RAM) — или любой Linux-компьютер для разработки
- USB-микрофон
- Динамик (USB или 3.5mm jack)
- GPIO-кнопка на пин 17 (опционально — есть fallback на Enter с клавиатуры)

### Софт
- Raspberry Pi OS 64-bit (Bookworm) или любой Linux с Python 3.11+
- ~1.5 GB свободного места на диске (модели + зависимости)

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone <repo-url> ~/voice-assistant
cd ~/voice-assistant
```

### 2. Установка (автоматическая, для RPi5)

```bash
bash scripts/install.sh
```

Этот скрипт:
- Устанавливает системные зависимости (portaudio, libsndfile, cmake)
- Создаёт Python venv и ставит pip-пакеты
- Скачивает модели
- Индексирует sample-документ
- Настраивает systemd-сервис

### 2 (альтернатива). Ручная установка

```bash
# Системные зависимости
sudo apt update && sudo apt install -y \
    python3-pip python3-venv \
    portaudio19-dev libsndfile1 \
    cmake build-essential wget unzip

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Модели
bash scripts/download_models.sh

# Индексация
python3 -m src.rag.indexer
```

### 3. Запуск

```bash
source .venv/bin/activate
python -m src.main
```

После запуска:
- Нажмите **Enter** (или GPIO-кнопку) → говорите → получите ответ
- Или скажите **"Окей кафедра"** → говорите → получите ответ

### 4. Автозапуск (systemd)

```bash
sudo systemctl enable voice-assistant
sudo systemctl start voice-assistant

# Логи
journalctl -u voice-assistant -f
```

## Структура проекта

```
src/
├── main.py               # Точка входа, оркестрация pipeline
├── config.py              # Загрузка YAML-конфигурации
├── asr/
│   ├── recognizer.py      # Vosk ASR (речь → текст)
│   └── wake_word.py       # Детекция wake word
├── rag/
│   ├── document_loader.py # Парсинг PDF/DOCX/TXT + chunking
│   ├── embedder.py        # rubert-tiny2 ONNX embeddings
│   ├── indexer.py         # FAISS + SQLite индексация
│   ├── retriever.py       # Семантический поиск
│   ├── generator.py       # Генерация ответа (template / LLM)
│   └── watcher.py         # Автоиндексация при изменении документов
├── tts/
│   └── synthesizer.py     # Piper TTS (текст → голос)
├── audio/
│   ├── recorder.py        # Запись с микрофона + VAD
│   └── player.py          # Воспроизведение аудио
├── hardware/
│   └── button.py          # GPIO-кнопка (+ клавиатурный fallback)
└── utils/
    ├── memory.py           # Управление RAM
    └── sounds.py           # Генерация системных звуков

config/assistant.yaml      # Вся конфигурация
data/documents/            # Документы базы знаний (сюда кладёте файлы)
data/models/               # Скачанные модели (не в git)
data/index/                # FAISS индекс + SQLite (генерируется)
```

## Конфигурация

Все настройки в `config/assistant.yaml`:

```yaml
# Режим генерации: template (быстро, без LLM) или llm (Vikhr-1B, качественнее)
rag:
  generator:
    mode: template  # template | llm

# Wake word (можно отключить)
wake_word:
  enabled: true
  phrase: "окей кафедра"

# GPIO-пин кнопки (или keyboard fallback для разработки)
hardware:
  button:
    gpio_pin: 17
    use_keyboard_fallback: true
```

## Управление базой знаний

Положите файлы (PDF, DOCX, TXT) в `data/documents/`:

```bash
cp расписание.pdf data/documents/
cp faq.txt data/documents/
```

**Автоиндексация**: система проверяет папку каждые 60 секунд и автоматически индексирует новые/изменённые файлы.

**Ручная индексация**:
```bash
bash scripts/index_documents.sh
```

## Известные ограничения и на что обратить внимание

### Модели
- **ONNX-модель rubert-tiny2**: скрипт `download_models.sh` скачивает tokenizer, но не саму ONNX-модель. При первом запуске embedder попробует загрузить через transformers (нужен `pip install transformers torch`). Для оптимальной работы на RPi нужно заранее экспортировать модель в ONNX и положить `model.onnx` в `data/models/rubert-tiny2-int8/`. Можно сделать на мощной машине:
  ```python
  from transformers import AutoModel, AutoTokenizer
  import torch
  model = AutoModel.from_pretrained("cointegrated/rubert-tiny2")
  tokenizer = AutoTokenizer.from_pretrained("cointegrated/rubert-tiny2")
  dummy = tokenizer("test", return_tensors="pt")
  torch.onnx.export(model, (dummy["input_ids"], dummy["attention_mask"], dummy["token_type_ids"]),
                    "model.onnx", input_names=["input_ids", "attention_mask", "token_type_ids"],
                    dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}, "token_type_ids": {0: "batch", 1: "seq"}})
  ```

### Piper TTS
- URL скачивания моделей может измениться. Если `download_models.sh` не работает — скачайте `.onnx` и `.onnx.json` файлы вручную с [Piper voices](https://github.com/rhasspy/piper/blob/master/VOICES.md) и положите в `data/models/piper-ru_RU-irina-medium/`.

### Vikhr-1B LLM (enhanced mode)
- Скачивание опционально (691 MB). Без неё система работает в template mode — возвращает найденный фрагмент документа как есть.
- На RPi5 генерация ~5-10 токенов/сек. Ответ из 50 слов ≈ 5-10 секунд.
- Если переключаете `mode: llm` в конфиге — нужен `llama-cpp-python`, который компилируется из исходников. На RPi5 компиляция занимает ~10 минут.

### Аудио
- Убедитесь, что микрофон определяется системой: `arecord -l`
- Убедитесь, что динамик работает: `speaker-test -t wav`
- Если несколько аудиоустройств — может потребоваться указать device index в sounddevice. Проверить: `python -c "import sounddevice; print(sounddevice.query_devices())"`

### GPIO
- На не-RPi машинах GPIO недоступен — автоматически включается keyboard fallback (нажатие Enter).
- На RPi: кнопка между GPIO 17 и GND, подтяжка к питанию включена программно.
- Если нужен другой пин — измените `gpio_pin` в `config/assistant.yaml`.

### RAM
- Модели загружаются/выгружаются последовательно, но если что-то идёт не так — проверьте потребление: `htop` или `free -m`.
- При template mode (без LLM) пиковое потребление ~1.0 GB, при LLM mode ~2.0 GB.

### Качество распознавания
- Vosk small-ru модель хорошо работает для коротких команд и вопросов, но может ошибаться на длинных сложных предложениях.
- В шумном окружении качество падает. Рекомендуется направленный микрофон.

## Разработка на обычном компьютере

Проект можно запускать и без RPi:
- GPIO-кнопка заменяется на Enter с клавиатуры (`use_keyboard_fallback: true`)
- Все модели работают на x86_64 (Linux/macOS/Windows с WSL)
- Для Windows: нужен PortAudio — `pip install sounddevice` обычно ставит его сам

## Лицензии используемых компонентов

| Компонент | Лицензия |
|-----------|---------|
| Vosk | Apache 2.0 |
| Piper TTS | MIT |
| FAISS | MIT |
| rubert-tiny2 | MIT |
| Vikhr-Llama-3.2-1B | Llama 3.2 Community License |
| llama.cpp | MIT |
