#!/usr/bin/env bash
# Pre-download AI models for Animetta (offline/Docker use)
#
# Models:
#   - Kokoro TTS:      hexgrad/Kokoro-82M       (~300MB, 82M params)
#   - Qwen3 TTS:       Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice (~3.4GB, 1.7B params)
#   - Whisper ASR:     Systran/faster-whisper-distil-large-v3 (~3GB)
#
# Usage:
#   bash scripts/download-models.sh              # Download all models
#   bash scripts/download-models.sh kokoro       # Download Kokoro only
#   bash scripts/download-models.sh qwen3        # Download Qwen3 only
#   bash scripts/download-models.sh whisper      # Download Whisper only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="${MODELS_DIR:-$PROJECT_ROOT/data/models}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
# Kokoro TTS (hexgrad/Kokoro-82M)
# ---------------------------------------------------------------------------
download_kokoro() {
    log_info "=== Downloading Kokoro TTS (hexgrad/Kokoro-82M) ==="
    log_info "Target: $MODELS_DIR/kokoro/"

    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'hexgrad/Kokoro-82M',
    local_dir='$MODELS_DIR/kokoro',
    local_dir_use_symlinks=False,
)
print('Kokoro download complete.')
"
    log_info "Kokoro TTS downloaded to $MODELS_DIR/kokoro/"
}

# ---------------------------------------------------------------------------
# Qwen3 TTS (Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)
# ---------------------------------------------------------------------------
download_qwen3() {
    log_info "=== Downloading Qwen3 TTS (Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) ==="
    log_info "Target: $MODELS_DIR/qwen3/"
    log_warn "This model is ~3.4GB. Ensure you have enough disk space."

    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
    local_dir='$MODELS_DIR/qwen3',
    local_dir_use_symlinks=False,
)
print('Qwen3 TTS download complete.')
"
    log_info "Qwen3 TTS downloaded to $MODELS_DIR/qwen3/"
}

# ---------------------------------------------------------------------------
# Whisper ASR (Systran/faster-whisper-distil-large-v3)
# ---------------------------------------------------------------------------
download_whisper() {
    log_info "=== Downloading Whisper ASR (Systran/faster-whisper-distil-large-v3) ==="
    log_info "Target: $MODELS_DIR/whisper/"

    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    'Systran/faster-whisper-distil-large-v3',
    local_dir='$MODELS_DIR/whisper',
    local_dir_use_symlinks=False,
)
print('Whisper download complete.')
"
    log_info "Whisper ASR downloaded to $MODELS_DIR/whisper/"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    local target="${1:-all}"

    log_info "Models directory: $MODELS_DIR"
    mkdir -p "$MODELS_DIR"/{kokoro,qwen3,whisper}

    case "$target" in
        kokoro)  download_kokoro ;;
        qwen3)   download_qwen3 ;;
        whisper) download_whisper ;;
        all)
            download_kokoro
            download_qwen3
            download_whisper
            ;;
        *)
            log_error "Unknown target: $target"
            echo "Usage: $0 [kokoro|qwen3|whisper|all]"
            exit 1
            ;;
    esac

    log_info "=== All requested models downloaded successfully ==="
}

main "$@"
