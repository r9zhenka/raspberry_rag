# Research: Голосовой ассистент кафедры

**Branch**: `001-voice-assistant` | **Date**: 2026-02-28

## ASR (Speech-to-Text)

### Decision: Vosk (vosk-model-small-ru-0.22)

**Rationale**:
- ~300 MB RAM — оставляет запас для остальных модулей
- Настоящий стриминг — partial results по мере речи, низкая воспринимаемая задержка
- Первоклассная поддержка русского (разработчики — русскоязычные)
- Встроенный keyword spotting для wake word (на том же движке)
- Простейшая Python-интеграция: `pip install vosk`, ~10 строк кода
- Латентность ~600мс на RPi5 для коротких фраз
- 100% оффлайн

**Alternatives considered**:
- **whisper.cpp (small Q5)**: Лучше качество (WER ~30-40% vs Vosk), но ~850 MB RAM, нет стриминга, нет wake word. Модель small — минимум для приемлемого русского.
- **faster-whisper (small int8)**: ~900 MB RAM, отличный Python API, но есть проблемы стабильности на ARM64, нет стриминга из коробки.
- Оба варианта Whisper слишком тяжелы для 4GB при совместной работе с LLM.

### Wake Word: Vosk keyword spotting mode

**Rationale**:
- Использует тот же vosk-model-small-ru (~300 MB) — не требует дополнительной RAM
- Поддержка русских wake word (например "окей кафедра")
- Полностью open-source (Apache 2.0)

**Alternatives considered**:
- **Porcupine**: 1.4 MB RAM, поддержка русского, но проприетарная лицензия — не подходит под требование open-source
- **OpenWakeWord**: Open-source, <60 MB RAM, но нет поддержки русского

## TTS (Text-to-Speech)

### Decision: Piper TTS (ru_RU-irina-medium)

**Rationale**:
- ~100-200 MB RAM — самый экономичный среди нейросетевых
- Sub-second латентность на RPi5 (RTF 0.05-0.15)
- Специально спроектирован для Raspberry Pi (ONNX Runtime, ARM64)
- Несколько русских голосов: irina, denis, dmitri, ruslan
- `pip install piper-tts`, модель ~40-70 MB
- Активно развивается (Rhasspy/Home Assistant)

**Alternatives considered**:
- **Silero TTS**: Лучшее качество русского голоса (9/10 vs 7/10), но требует PyTorch (~400-600 MB RAM), холодный старт 10-20 сек.
- **RHVoice**: Минимальные ресурсы (~20-50 MB), но роботизированный голос (5/10).
- **Coqui TTS**: Слишком тяжёлый (~800 MB - 2 GB), медленный на ARM, проект на поддержке.

## RAG — Embeddings

### Decision: cointegrated/rubert-tiny2 (ONNX int8)

**Rationale**:
- 29M параметров, ~50 MB на диске (ONNX int8), ~150-200 MB RAM
- Специально создан для русских sentence-embeddings
- Encodechka benchmark: 0.704 — лучший по соотношению качество/размер для русского
- 312 измерений — компактные векторы
- ONNX Runtime — быстрый inference на ARM64 (~50-150мс/предложение)

**Alternatives considered**:
- **multilingual-e5-small**: 117M параметров, ~500-700 MB RAM — слишком тяжёлый
- **FastText/Navec**: word-level, не подходит для семантического поиска предложений
- **sbert_large_nlu_ru**: 335M, ~1.5-2 GB — не помещается

## RAG — Vector Store

### Decision: FAISS (faiss-cpu, IndexFlatIP)

**Rationale**:
- ~12 MB RAM на 10K векторов (312d) — минимальный overhead
- Sub-millisecond поиск для <100K векторов
- Нет фонового процесса, нет сервера
- Persistence: `faiss.write_index()` / `faiss.read_index()`
- Текст и метаданные храним отдельно в SQLite

**Alternatives considered**:
- **ChromaDB**: ~180-200 MB на 10K векторов, не рекомендуется на <2 GB RAM
- **sqlite-vec**: Хорошая альтернатива (~30 MB), но менее зрелый проект

## RAG — LLM (генерация ответов)

### Decision: Гибридный подход (Template MVP → Vikhr-1B)

**MVP**: Template-based — возвращаем найденный фрагмент в обёртке "По данным кафедры: {chunk}". 0 MB RAM, мгновенный ответ.

**Enhanced**: Vikhr-Llama-3.2-1B-Instruct (Q3_K_M GGUF) через llama.cpp
- 691 MB на диске, ~800-1200 MB RAM
- Специально дообучен для русского (GrandMaster-PRO-MAX dataset)
- 5-10 tok/s на RPi5
- Контекст: 512 токенов

**Ключевая оптимизация — последовательная загрузка моделей**:
- Фаза 1 (Retrieval): загружаем rubert-tiny2 → embed → выгружаем. Пик: ~160 MB
- Фаза 2 (Generation): загружаем Vikhr-1B → генерируем → выгружаем. Пик: ~1000 MB
- Никогда не держим embedding-модель и LLM в RAM одновременно

**Alternatives considered**:
- **Qwen2.5-0.5B Q4_K_M**: 491 MB, быстрее (15-20 tok/s), но хуже русский
- **Только шаблоны**: Мгновенно, но ответы — сырые фрагменты документов

## RAM Budget (пиковое потребление)

```
Компонент                          RAM
──────────────────────────────────────
OS + сервисы                       ~500 MB
Vosk ASR (small-ru)                ~300 MB
Piper TTS                         ~150 MB
FAISS index (persistent)           ~10 MB
──────────────────────────────────────
Базовое потребление:              ~960 MB

+ Retrieval phase:
  rubert-tiny2 ONNX                ~150 MB
  Пик фазы:                      ~1110 MB

+ Generation phase:
  Vikhr-1B Q3_K_M + KV cache     ~1000 MB
  Пик фазы:                      ~1960 MB

Максимальный пик:                 ~2.0 GB
Свободно:                         ~2.0 GB
```
