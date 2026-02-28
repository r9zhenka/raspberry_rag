import logging
import os
import numpy as np
from src.utils.memory import force_gc, log_memory_usage

logger = logging.getLogger(__name__)


class Embedder:
    """Sentence embedder using rubert-tiny2 via ONNX or transformers."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._tokenizer = None
        self._session = None
        self._use_onnx = False

    def load(self):
        """Load the embedding model into RAM."""
        log_memory_usage("before embedder load")

        onnx_path = os.path.join(self.model_path, "model.onnx")
        if os.path.exists(onnx_path):
            self._load_onnx(onnx_path)
        else:
            self._load_transformers()

        log_memory_usage("after embedder load")

    def _load_onnx(self, onnx_path: str):
        """Load ONNX model for fast inference."""
        import onnxruntime as ort
        from tokenizers import Tokenizer

        tokenizer_path = os.path.join(self.model_path, "tokenizer.json")
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_truncation(max_length=512)
        self._tokenizer.enable_padding(length=512)

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = 2
        self._session = ort.InferenceSession(onnx_path, sess_options)
        self._use_onnx = True
        logger.info("Embedder loaded (ONNX)")

    def _load_transformers(self):
        """Fallback: load via sentence-transformers / torch."""
        from transformers import AutoTokenizer, AutoModel
        import torch

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self._model = AutoModel.from_pretrained(self.model_path)
        self._model.eval()
        self._use_onnx = False
        logger.info("Embedder loaded (transformers)")

    def embed(self, texts: list[str]) -> np.ndarray:
        """Compute embeddings for a list of texts. Returns [N, dim] array."""
        if self._use_onnx:
            return self._embed_onnx(texts)
        else:
            return self._embed_transformers(texts)

    def _embed_onnx(self, texts: list[str]) -> np.ndarray:
        encodings = self._tokenizer.encode_batch(texts)

        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)

        outputs = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )
        # Use CLS token embedding (first token)
        embeddings = outputs[0][:, 0, :]
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        return embeddings / norms

    def _embed_transformers(self, texts: list[str]) -> np.ndarray:
        import torch

        encoded = self._tokenizer(
            texts, padding=True, truncation=True, max_length=512, return_tensors="pt"
        )
        with torch.no_grad():
            outputs = self._model(**encoded)
        embeddings = outputs.last_hidden_state[:, 0, :].numpy()
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        return embeddings / norms

    def unload(self):
        """Free model from RAM."""
        self._session = None
        self._tokenizer = None
        if hasattr(self, "_model"):
            del self._model
        force_gc()
        log_memory_usage("after embedder unload")
        logger.info("Embedder unloaded")
