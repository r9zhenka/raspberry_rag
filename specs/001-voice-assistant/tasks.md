# Tasks: Голосовой ассистент кафедры

**Input**: Design documents from `/specs/001-voice-assistant/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/pipeline.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, structure, models download

- [x] T001 Create project directory structure per plan.md (src/, tests/, data/, scripts/, config/, systemd/)
- [x] T002 Create requirements.txt with all dependencies (vosk, piper-tts, faiss-cpu, onnxruntime, llama-cpp-python, sounddevice, PyPDF2, python-docx, pyyaml, RPi.GPIO)
- [x] T003 Create config/assistant.yaml with default configuration (paths to models, GPIO pin, wake word phrase, audio params)
- [x] T004 [P] Create src/config.py — загрузка конфигурации из assistant.yaml
- [x] T005 [P] Create scripts/download_models.sh — скрипт скачивания Vosk, Piper, rubert-tiny2, Vikhr-1B моделей в data/models/
- [x] T006 [P] Create .gitignore (data/models/, data/index/, .venv/, __pycache__/)
- [x] T007 [P] Create data/sounds/activate.wav и data/sounds/error.wav — системные звуковые сигналы (сгенерировать простые тоны программно)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Audio I/O и утилиты управления памятью — используются всеми user stories

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Create src/audio/recorder.py — класс Recorder: запись с микрофона через sounddevice, метод record_until_silence() с VAD по порогу громкости
- [x] T009 [P] Create src/audio/player.py — класс Player: воспроизведение numpy-аудио через sounddevice, метод play_sound() для системных звуков из data/sounds/
- [x] T010 [P] Create src/utils/memory.py — утилиты управления RAM: функции force_gc() и log_memory_usage() для контроля памяти при загрузке/выгрузке моделей
- [x] T011 Create src/audio/__init__.py, src/utils/__init__.py — init-файлы модулей

**Checkpoint**: Audio I/O и утилиты готовы — можно начинать user stories

---

## Phase 3: User Story 1 — Голосовой вопрос по кнопке (Priority: P1) MVP

**Goal**: Полный цикл speech-to-speech: кнопка → ASR → RAG → TTS → ответ голосом

**Independent Test**: Нажать кнопку, произнести вопрос, получить голосовой ответ из базы знаний

### Implementation for User Story 1

- [x] T012 [US1] Create src/hardware/button.py — класс Button: инициализация GPIO-пина, метод on_press(callback), debounce, cleanup. Fallback на keyboard input (Enter) для разработки без RPi
- [x] T013 [US1] Create src/hardware/__init__.py
- [x] T014 [US1] Create src/asr/__init__.py и src/asr/recognizer.py — класс Recognizer: загрузка vosk-model-small-ru-0.22, метод recognize(audio: np.ndarray) -> str, стриминг через KaldiRecognizer
- [x] T015 [P] [US1] Create src/rag/document_loader.py — класс DocumentLoader: парсинг PDF (PyPDF2), DOCX (python-docx), TXT. Метод load(filepath) -> list[str] с chunking по ~300-500 символов с перекрытием
- [x] T016 [P] [US1] Create src/rag/embedder.py — класс Embedder: загрузка rubert-tiny2 ONNX int8, метод embed(texts) -> np.ndarray[N, 312], метод unload() для освобождения RAM
- [x] T017 [US1] Create src/rag/indexer.py — класс Indexer: создание FAISS IndexFlatIP + SQLite база (таблицы documents, chunks). Метод index_directory(path) для индексации всей папки data/documents/. Запускается как `python -m src.rag.indexer`
- [x] T018 [US1] Create src/rag/retriever.py — класс Retriever: загрузка FAISS индекса, метод search(query_embedding, top_k=3) -> list[dict] с text, score, document_name из SQLite
- [x] T019 [US1] Create src/rag/generator.py — класс Generator: template mode (MVP) — форматирует ответ как "По данным кафедры: {chunk_text}". Заготовка для LLM mode (Vikhr-1B через llama-cpp-python, загрузка/выгрузка). Метод generate(query, context) -> str
- [x] T020 [US1] Create src/rag/__init__.py
- [x] T021 [US1] Create src/tts/__init__.py и src/tts/synthesizer.py — класс Synthesizer: загрузка Piper ru_RU-irina-medium, метод synthesize(text) -> np.ndarray (int16, 22050 Hz)
- [x] T022 [US1] Create data/documents/sample_department.txt — синтетический документ-заглушка с информацией о кафедре (расписание, преподаватели, предметы, контакты, FAQ). ~2000 слов для полноценного тестирования RAG
- [x] T023 [US1] Create src/main.py — главный pipeline: инициализация всех модулей, функция handle_query() (play activate → record → ASR → embed → search → generate → TTS → play), цикл ожидания нажатия кнопки, graceful shutdown
- [ ] T024 [US1] Интеграционное тестирование Story 1: запустить индексацию sample_department.txt, запустить main.py, проверить полный цикл button → voice → answer

**Checkpoint**: MVP готов — полный цикл speech-to-speech по кнопке работает

---

## Phase 4: User Story 2 — Активация голосом wake word (Priority: P2)

**Goal**: Режим wake word — произнести "Окей кафедра", ассистент активируется и слушает вопрос

**Independent Test**: Сказать "Окей кафедра", дождаться сигнала, задать вопрос, получить ответ

### Implementation for User Story 2

- [x] T025 [US2] Create src/asr/wake_word.py — класс WakeWordDetector: Vosk KaldiRecognizer с restricted vocabulary (wake word фраза из config), метод listen(callback) в отдельном потоке, метод stop(). Непрерывное прослушивание с минимальным CPU
- [x] T026 [US2] Update src/main.py — добавить режим wake word: параллельно с кнопкой запустить WakeWordDetector.listen(), при детекции wake word вызывать тот же handle_query(). Два потока: wake_word_thread + button listener

**Checkpoint**: Оба режима активации работают — кнопка и wake word

---

## Phase 5: User Story 3 — Управление базой знаний (Priority: P2)

**Goal**: Автоматическая индексация при добавлении/удалении документов в data/documents/

**Independent Test**: Положить новый файл в data/documents/, задать вопрос по его содержимому, получить ответ

### Implementation for User Story 3

- [x] T027 [US3] Create src/rag/watcher.py — класс DocumentWatcher: мониторинг папки data/documents/ через polling (каждые 60 сек проверка hash файлов). При добавлении/изменении — переиндексация. При удалении — удаление из SQLite + перестроение FAISS индекса
- [x] T028 [US3] Update src/main.py — запустить DocumentWatcher в фоновом потоке при старте приложения
- [x] T029 [US3] Update src/rag/indexer.py — добавить методы: add_document(filepath), remove_document(document_id), rebuild_index(). Инкрементальная индексация без пересоздания всего индекса

**Checkpoint**: Документы автоматически индексируются, система отвечает на вопросы по новым документам

---

## Phase 6: User Story 4 — Автозапуск и стабильная работа (Priority: P3)

**Goal**: Автозапуск при включении RPi, стабильная работа 24/7

**Independent Test**: Перезагрузить RPi, убедиться что ассистент запустился и отвечает

### Implementation for User Story 4

- [x] T030 [US4] Create systemd/voice-assistant.service — systemd unit: ExecStart, WorkingDirectory, Restart=always, User, After=sound.target
- [x] T031 [US4] Create scripts/install.sh — полный скрипт установки: apt dependencies, venv, pip install, download models, enable systemd service
- [x] T032 [US4] Update src/main.py — добавить обработку сигналов (SIGTERM, SIGINT), logging в файл, перехват необработанных исключений с автоперезапуском pipeline (не всего процесса)

**Checkpoint**: Система запускается автоматически и работает стабильно

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Улучшения, затрагивающие несколько user stories

- [x] T033 [P] Create scripts/index_documents.sh — удобный скрипт для ручной переиндексации
- [x] T034 [P] Update src/rag/generator.py — добавить LLM mode (Vikhr-1B Q3_K_M через llama-cpp-python): загрузка/выгрузка модели, генерация с контекстом 512 токенов, fallback на template mode при ошибке или таймауте
- [x] T035 Add error handling across all modules — graceful degradation: если ASR не распознал → голосовое сообщение, если RAG не нашёл → "не нашёл информацию", если TTS fail → логирование
- [x] T036 Run quickstart.md validation — пройти все шаги quickstart.md на тестовой машине, исправить несоответствия

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — начинаем сразу
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 — MVP
- **User Story 2 (Phase 4)**: Depends on Phase 3 (reuses ASR + pipeline)
- **User Story 3 (Phase 5)**: Depends on Phase 3 (reuses indexer)
- **User Story 4 (Phase 6)**: Depends on Phase 3 (needs working main.py)
- **Polish (Phase 7)**: Depends on all desired stories

### User Story Dependencies

- **US1 (P1)**: Foundational → US1. Полностью независима. MVP.
- **US2 (P2)**: Foundational → US1 → US2. Нужен работающий pipeline из US1.
- **US3 (P2)**: Foundational → US1 → US3. Нужен работающий indexer из US1.
- **US4 (P3)**: Foundational → US1 → US4. Нужен работающий main.py из US1.

### Parallel Opportunities

Phase 1:
- T004, T005, T006, T007 — все параллельно

Phase 2:
- T009, T010 — параллельно (T008 может идти параллельно с T009)

Phase 3 (US1):
- T015, T016 — параллельно (document_loader и embedder независимы)

Phase 7:
- T033, T034 — параллельно

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup → структура проекта готова
2. Complete Phase 2: Foundational → audio I/O работает
3. Complete Phase 3: User Story 1 → **полный speech-to-speech pipeline**
4. **STOP and VALIDATE**: нажать кнопку, задать вопрос, получить ответ
5. Это уже рабочий демонстрируемый MVP

### Incremental Delivery

1. Setup + Foundational → каркас
2. US1 → MVP (кнопка + голос + ответ)
3. US2 → + wake word
4. US3 → + автоиндексация документов
5. US4 → + автозапуск на RPi
6. Polish → + LLM генерация (Vikhr-1B)

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 36 |
| Phase 1 (Setup) | 7 tasks |
| Phase 2 (Foundational) | 4 tasks |
| Phase 3 (US1 - MVP) | 13 tasks |
| Phase 4 (US2 - Wake word) | 2 tasks |
| Phase 5 (US3 - Docs management) | 3 tasks |
| Phase 6 (US4 - Autostart) | 3 tasks |
| Phase 7 (Polish) | 4 tasks |
| Parallel opportunities | 10 tasks marked [P] |
| MVP scope | Phase 1 + 2 + 3 (24 tasks) |
