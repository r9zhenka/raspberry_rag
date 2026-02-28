# Implementation Plan: Голосовой ассистент кафедры

**Branch**: `001-voice-assistant` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-voice-assistant/spec.md`

## Summary

Speech-to-speech голосовой ассистент для кафедры на Raspberry Pi 5 (4GB). Три модуля: ASR (Vosk), RAG (rubert-tiny2 + FAISS + Vikhr-1B), TTS (Piper). Полностью оффлайн, open-source. Два режима активации: кнопка и wake word.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: vosk, piper-tts, faiss-cpu, onnxruntime, llama-cpp-python, sentence-transformers, python-docx, PyPDF2, sounddevice, RPi.GPIO
**Storage**: FAISS index (файл) + SQLite (метаданные и текст чанков) + файловая система (документы)
**Testing**: pytest
**Target Platform**: Raspberry Pi 5, ARM64, Raspberry Pi OS (64-bit Bookworm)
**Project Type**: embedded-service (systemd daemon)
**Performance Goals**: Ответ за <10 сек, ASR распознавание 80%+, RAM <3.5 GB
**Constraints**: 4 GB RAM, полностью оффлайн, только open-source, русский язык
**Scale/Scope**: 1 устройство, 1 пользователь одновременно, база знаний ~100-1000 документов

## Constitution Check

*GATE: Constitution не настроена (шаблон по умолчанию). Нет блокирующих ограничений.*

## Project Structure

### Documentation (this feature)

```text
specs/001-voice-assistant/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── pipeline.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── main.py                  # Точка входа, оркестрация pipeline
├── config.py                # Конфигурация (пути, параметры моделей)
├── asr/
│   ├── __init__.py
│   ├── recognizer.py        # Vosk ASR — запись и распознавание речи
│   └── wake_word.py         # Vosk keyword spotting — детекция wake word
├── rag/
│   ├── __init__.py
│   ├── embedder.py          # rubert-tiny2 ONNX — embedding текста
│   ├── indexer.py           # FAISS индексация + SQLite хранение чанков
│   ├── retriever.py         # Поиск релевантных чанков
│   ├── generator.py         # LLM генерация (Vikhr-1B) / template fallback
│   └── document_loader.py   # Парсинг PDF/DOCX/TXT, chunking
├── tts/
│   ├── __init__.py
│   └── synthesizer.py       # Piper TTS — синтез речи
├── audio/
│   ├── __init__.py
│   ├── recorder.py          # Запись с микрофона (sounddevice)
│   └── player.py            # Воспроизведение аудио (sounddevice)
├── hardware/
│   ├── __init__.py
│   └── button.py            # GPIO-кнопка для push-to-talk
└── utils/
    ├── __init__.py
    └── memory.py             # Управление памятью (загрузка/выгрузка моделей)

tests/
├── unit/
│   ├── test_document_loader.py
│   ├── test_embedder.py
│   ├── test_retriever.py
│   └── test_generator.py
└── integration/
    ├── test_asr_pipeline.py
    ├── test_rag_pipeline.py
    └── test_full_pipeline.py

data/
├── documents/               # Папка для документов базы знаний
│   └── sample_department.txt # Синтетический документ-заглушка
├── models/                  # Скачанные модели (не в git)
│   ├── vosk-model-small-ru-0.22/
│   ├── piper-ru_RU-irina-medium/
│   ├── rubert-tiny2-int8/
│   └── vikhr-1b-q3_k_m.gguf
├── index/                   # FAISS индекс + SQLite база
│   ├── faiss.index
│   └── chunks.db
└── sounds/                  # Системные звуки
    ├── activate.wav          # Звук активации
    └── error.wav             # Звук ошибки

scripts/
├── download_models.sh       # Скрипт скачивания моделей
├── index_documents.sh       # Скрипт индексации документов
└── install.sh               # Установка зависимостей на RPi5

config/
└── assistant.yaml           # Конфигурация ассистента

requirements.txt
setup.py
systemd/
└── voice-assistant.service  # Systemd unit для автозапуска
```

**Structure Decision**: Single project — все модули в одном Python-пакете `src/`. Это embedded-приложение без API/фронтенда, поэтому плоская структура с модулями по функциональности (asr/, rag/, tts/, audio/, hardware/).

## Technology Stack Summary

| Компонент | Технология | RAM | Модель/Размер |
|-----------|-----------|-----|---------------|
| ASR | Vosk (vosk-model-small-ru-0.22) | ~300 MB | 46 MB на диске |
| Wake Word | Vosk keyword spotting | 0 (reuse ASR) | — |
| Embeddings | rubert-tiny2 (ONNX int8) | ~150 MB | ~50 MB на диске |
| Vector Store | FAISS (IndexFlatIP) | ~10 MB | — |
| Metadata | SQLite | ~5 MB | — |
| LLM (MVP) | Template-based | 0 | — |
| LLM (Enhanced) | Vikhr-Llama-3.2-1B Q3_K_M | ~1000 MB | 691 MB на диске |
| TTS | Piper (ru_RU-irina-medium) | ~150 MB | ~50 MB на диске |
| Audio I/O | sounddevice + PortAudio | ~10 MB | — |
| Button | RPi.GPIO | ~1 MB | — |

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────┐
│                   IDLE STATE                         │
│  Vosk keyword spotting (wake word) ──┐               │
│  GPIO button listener ──────────────┤               │
│                                     ▼               │
│                              ┌──────────┐           │
│                              │ ACTIVATE │           │
│                              │ (beep)   │           │
│                              └────┬─────┘           │
│                                   ▼                 │
│                         ┌─────────────────┐         │
│                         │   ASR (Vosk)    │         │
│                         │ audio → text    │         │
│                         └────────┬────────┘         │
│                                  ▼                  │
│                      ┌───────────────────┐          │
│                      │  RAG Pipeline     │          │
│                      │  1. Embed query   │          │
│                      │  2. FAISS search  │          │
│                      │  3. Generate ans  │          │
│                      └────────┬──────────┘          │
│                               ▼                     │
│                      ┌────────────────┐             │
│                      │  TTS (Piper)   │             │
│                      │  text → audio  │             │
│                      └────────┬───────┘             │
│                               ▼                     │
│                         ┌──────────┐                │
│                         │  PLAY    │                │
│                         │  audio   │                │
│                         └──────────┘                │
└─────────────────────────────────────────────────────┘
```

## Memory Management Strategy

Последовательная загрузка/выгрузка моделей для экономии RAM:

1. **Постоянно в памяти**: Vosk (~300 MB), Piper (~150 MB), FAISS index (~10 MB)
2. **Загружается на фазу retrieval**: rubert-tiny2 (~150 MB) → выгружается после embed
3. **Загружается на фазу generation**: Vikhr-1B (~1000 MB) → выгружается после генерации

Пиковое потребление: ~2.0 GB (во время LLM генерации). Свободно: ~2.0 GB.

## Complexity Tracking

Нет нарушений конституции — заполнение не требуется.
