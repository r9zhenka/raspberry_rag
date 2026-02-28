# Data Model: Голосовой ассистент кафедры

**Branch**: `001-voice-assistant` | **Date**: 2026-02-28

## Entities

### Document

Исходный файл с информацией о кафедре.

| Field | Type | Description |
|-------|------|-------------|
| id | str (UUID) | Уникальный идентификатор |
| filename | str | Имя файла (например, "расписание.pdf") |
| filepath | str | Полный путь к файлу |
| format | enum | PDF / DOCX / TXT |
| hash | str (SHA256) | Хэш содержимого для детекции изменений |
| indexed_at | datetime | Время последней индексации |
| chunk_count | int | Количество чанков после разбиения |

### Chunk

Фрагмент документа, единица поиска.

| Field | Type | Description |
|-------|------|-------------|
| id | int | Автоинкрементный ID |
| document_id | str (UUID) | FK → Document.id |
| text | str | Текст фрагмента (~200-500 символов) |
| chunk_index | int | Порядковый номер чанка в документе |
| embedding_id | int | Индекс вектора в FAISS |

### Query (in-memory, не персистируется)

Запрос пользователя, существует только во время обработки.

| Field | Type | Description |
|-------|------|-------------|
| audio | bytes | Сырой аудио-буфер с микрофона |
| text | str | Распознанный текст (ASR output) |
| embedding | float[312] | Вектор запроса (rubert-tiny2 output) |
| retrieved_chunks | list[Chunk] | Найденные релевантные фрагменты |
| answer_text | str | Сгенерированный ответ |
| answer_audio | bytes | Синтезированное аудио (TTS output) |

## Storage Layout

```
SQLite: data/index/chunks.db
├── documents (id, filename, filepath, format, hash, indexed_at, chunk_count)
└── chunks (id, document_id, text, chunk_index, embedding_id)

FAISS: data/index/faiss.index
└── Flat index of float32[312] vectors, ID maps to chunks.embedding_id
```

## State Transitions

### Document Lifecycle

```
File added to data/documents/
        │
        ▼
   [DETECTED] ← watchdog / manual trigger
        │
        ▼
   [PARSING] → extract text → split into chunks
        │
        ▼
   [EMBEDDING] → compute vectors via rubert-tiny2
        │
        ▼
   [INDEXED] → stored in FAISS + SQLite
        │
        ▼
   [AVAILABLE] → ready for retrieval
```

### Query Lifecycle

```
Button press / Wake word
        │
        ▼
   [LISTENING] → recording audio
        │
        ▼
   [RECOGNIZING] → Vosk ASR
        │
        ▼
   [RETRIEVING] → embed + FAISS search
        │
        ▼
   [GENERATING] → LLM / template
        │
        ▼
   [SPEAKING] → Piper TTS + playback
        │
        ▼
   [IDLE]
```
