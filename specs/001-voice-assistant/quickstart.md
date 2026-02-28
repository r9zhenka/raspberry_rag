# Quickstart: Голосовой ассистент кафедры

**Branch**: `001-voice-assistant` | **Date**: 2026-02-28

## Требования

- Raspberry Pi 5 (4GB RAM)
- Raspberry Pi OS 64-bit (Bookworm)
- Python 3.11+
- USB-микрофон + динамик (USB или 3.5mm)
- GPIO-кнопка (подключена к GPIO-пину, по умолчанию GPIO 17)

## Установка

### 1. Системные зависимости

```bash
sudo apt update && sudo apt install -y \
    python3-pip python3-venv \
    portaudio19-dev \
    libsndfile1 \
    cmake build-essential
```

### 2. Python-окружение

```bash
cd ~/voice-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Скачивание моделей

```bash
bash scripts/download_models.sh
```

Скрипт скачивает:
- `vosk-model-small-ru-0.22` (46 MB)
- `piper-ru_RU-irina-medium` (~50 MB)
- `rubert-tiny2-int8` ONNX (~50 MB)
- `vikhr-1b-q3_k_m.gguf` (691 MB) — опционально для Enhanced mode

### 4. Добавление документов

Положите документы о кафедре в папку `data/documents/`:

```bash
cp расписание.pdf учебный_план.docx faq.txt data/documents/
```

### 5. Индексация документов

```bash
python3 -m src.rag.indexer
```

### 6. Запуск

```bash
python3 -m src.main
```

## Автозапуск (systemd)

```bash
sudo cp systemd/voice-assistant.service /etc/systemd/system/
sudo systemctl enable voice-assistant
sudo systemctl start voice-assistant
```

## Проверка работоспособности

1. Нажмите кнопку — должен прозвучать сигнал активации
2. Скажите «Какие предметы на первом курсе?»
3. Дождитесь голосового ответа (~10 сек)

Или через wake word:
1. Скажите «Окей кафедра»
2. Дождитесь сигнала
3. Задайте вопрос
