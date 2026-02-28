# Pipeline Contracts: Голосовой ассистент кафедры

**Branch**: `001-voice-assistant` | **Date**: 2026-02-28

## Module Interfaces

Каждый модуль имеет чётко определённый вход/выход. Модули связываются через main pipeline.

### ASR Module (`src/asr/`)

```python
class Recognizer:
    def __init__(self, model_path: str): ...
    def recognize(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Распознаёт речь из аудио-буфера. Возвращает текст."""
        ...

class WakeWordDetector:
    def __init__(self, model_path: str, wake_words: list[str]): ...
    def listen(self, callback: Callable[[], None]) -> None:
        """Непрерывно слушает wake word. Вызывает callback при детекции."""
        ...
    def stop(self) -> None: ...
```

### RAG Module (`src/rag/`)

```python
class DocumentLoader:
    def load(self, filepath: str) -> list[str]:
        """Загружает документ, возвращает список текстовых чанков."""
        ...

class Embedder:
    def __init__(self, model_path: str): ...
    def embed(self, texts: list[str]) -> np.ndarray:
        """Возвращает матрицу embeddings [N, 312]."""
        ...
    def unload(self) -> None:
        """Освобождает RAM."""
        ...

class Retriever:
    def __init__(self, index_path: str, db_path: str): ...
    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> list[dict]:
        """Возвращает [{text, score, document_name}, ...]."""
        ...

class Generator:
    def __init__(self, model_path: str | None = None): ...
    def generate(self, query: str, context: list[str]) -> str:
        """Генерирует ответ. Если model_path=None — template mode."""
        ...
    def unload(self) -> None:
        """Освобождает RAM."""
        ...
```

### TTS Module (`src/tts/`)

```python
class Synthesizer:
    def __init__(self, model_path: str): ...
    def synthesize(self, text: str) -> np.ndarray:
        """Возвращает аудио-массив (int16, 22050 Hz)."""
        ...
```

### Audio Module (`src/audio/`)

```python
class Recorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1): ...
    def record_until_silence(self, silence_threshold: float, silence_duration: float) -> np.ndarray:
        """Записывает аудио до паузы. Возвращает numpy array."""
        ...

class Player:
    def play(self, audio: np.ndarray, sample_rate: int = 22050) -> None:
        """Воспроизводит аудио через динамик. Блокирующий вызов."""
        ...
    def play_sound(self, sound_name: str) -> None:
        """Воспроизводит системный звук (activate, error)."""
        ...
```

### Hardware Module (`src/hardware/`)

```python
class Button:
    def __init__(self, gpio_pin: int): ...
    def on_press(self, callback: Callable[[], None]) -> None:
        """Регистрирует callback на нажатие кнопки."""
        ...
    def cleanup(self) -> None: ...
```

## Main Pipeline Contract

```python
# src/main.py — высокоуровневый flow

def handle_query():
    """Полный цикл обработки голосового вопроса."""
    player.play_sound("activate")        # Звуковой сигнал
    audio = recorder.record_until_silence()  # Запись
    text = recognizer.recognize(audio)    # ASR
    if not text:
        player.play_sound("error")
        tts_and_play("Извините, не удалось распознать вопрос.")
        return
    embedder.load()                       # Загрузка модели
    query_vec = embedder.embed([text])    # Embedding
    embedder.unload()                     # Выгрузка
    chunks = retriever.search(query_vec)  # Поиск
    generator.load()                      # Загрузка LLM
    answer = generator.generate(text, chunks)  # Генерация
    generator.unload()                    # Выгрузка
    tts_and_play(answer)                  # TTS + воспроизведение
```
