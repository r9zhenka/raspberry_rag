#!/bin/bash
set -e

MODELS_DIR="$(dirname "$0")/../data/models"
mkdir -p "$MODELS_DIR"

echo "=== Downloading models for Voice Assistant ==="

# 1. Vosk Russian small model
if [ ! -d "$MODELS_DIR/vosk-model-small-ru-0.22" ]; then
    echo "[1/4] Downloading Vosk Russian model (46 MB)..."
    cd "$MODELS_DIR"
    wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
    unzip -q vosk-model-small-ru-0.22.zip
    rm vosk-model-small-ru-0.22.zip
    echo "  Done."
else
    echo "[1/4] Vosk model already exists, skipping."
fi

# 2. Piper TTS Russian voice
if [ ! -f "$MODELS_DIR/piper-ru_RU-irina-medium/ru_RU-irina-medium.onnx" ]; then
    echo "[2/4] Downloading Piper TTS Russian voice (~50 MB)..."
    mkdir -p "$MODELS_DIR/piper-ru_RU-irina-medium"
    cd "$MODELS_DIR/piper-ru_RU-irina-medium"
    wget -q --show-progress https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx
    wget -q --show-progress https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx.json
    echo "  Done."
else
    echo "[2/4] Piper TTS model already exists, skipping."
fi

# 3. rubert-tiny2 ONNX int8
if [ ! -d "$MODELS_DIR/rubert-tiny2-int8" ]; then
    echo "[3/4] Downloading rubert-tiny2 ONNX int8 (~50 MB)..."
    mkdir -p "$MODELS_DIR/rubert-tiny2-int8"
    cd "$MODELS_DIR/rubert-tiny2-int8"
    wget -q --show-progress https://huggingface.co/cointegrated/rubert-tiny2/resolve/main/tokenizer.json
    wget -q --show-progress https://huggingface.co/cointegrated/rubert-tiny2/resolve/main/tokenizer_config.json
    wget -q --show-progress https://huggingface.co/cointegrated/rubert-tiny2/resolve/main/vocab.txt
    wget -q --show-progress https://huggingface.co/cointegrated/rubert-tiny2/resolve/main/config.json
    wget -q --show-progress https://huggingface.co/cointegrated/rubert-tiny2/resolve/main/special_tokens_map.json
    # Export ONNX model (will be done during first indexing if not present)
    echo "  Note: ONNX model will be exported on first run."
    echo "  Done."
else
    echo "[3/4] rubert-tiny2 model already exists, skipping."
fi

# 4. Vikhr-1B LLM (optional, for enhanced mode)
if [ ! -f "$MODELS_DIR/vikhr-1b-q3_k_m.gguf" ]; then
    echo "[4/4] Downloading Vikhr-Llama-3.2-1B Q3_K_M (691 MB)..."
    echo "  This is optional (for enhanced LLM mode)."
    read -p "  Download? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$MODELS_DIR"
        wget -q --show-progress https://huggingface.co/Vikhrmodels/Vikhr-Llama-3.2-1B-instruct-GGUF/resolve/main/vikhr-llama-3.2-1b-instruct-q3_k_m.gguf -O vikhr-1b-q3_k_m.gguf
        echo "  Done."
    else
        echo "  Skipped. System will use template mode."
    fi
else
    echo "[4/4] Vikhr-1B model already exists, skipping."
fi

echo ""
echo "=== All models ready ==="
