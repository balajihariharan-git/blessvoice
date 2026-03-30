#!/usr/bin/env bash
# BlessVoice — Model Download Script
# Downloads PersonaPlex 7B and Llama 3.1 8B to /opt/blessvoice/models/
#
# Prerequisites:
#   - huggingface-cli installed: pip install huggingface_hub[cli]
#   - HF token with access to gated models: huggingface-cli login
#   - Accept PersonaPlex license at https://huggingface.co/nvidia/personaplex-7b-v1
#   - ~25 GB free disk space
#
# Usage:
#   chmod +x download-models.sh
#   sudo ./download-models.sh          # downloads both models
#   sudo ./download-models.sh --llama  # downloads only Llama
#   sudo ./download-models.sh --voice  # downloads only PersonaPlex

set -euo pipefail

# --- Configuration ---
MODEL_DIR="/opt/blessvoice/models"
PERSONAPLEX_REPO="nvidia/personaplex-7b-v1"
PERSONAPLEX_DIR="${MODEL_DIR}/personaplex-7b-v1"
LLAMA_REPO="bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
LLAMA_FILE="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
LLAMA_DIR="${MODEL_DIR}/llama-3.1-8b-instruct"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# --- Preflight checks ---
check_prerequisites() {
    log_info "Running preflight checks..."

    # Check huggingface-cli
    if ! command -v huggingface-cli &> /dev/null; then
        log_error "huggingface-cli not found. Install with: pip install huggingface_hub[cli]"
        exit 1
    fi

    # Check HF authentication
    if ! huggingface-cli whoami &> /dev/null; then
        log_error "Not logged in to HuggingFace. Run: huggingface-cli login"
        exit 1
    fi

    HF_USER=$(huggingface-cli whoami 2>/dev/null | head -1)
    log_info "Authenticated as: ${HF_USER}"

    # Check disk space (need ~25GB)
    AVAILABLE_GB=$(df -BG "${MODEL_DIR%/*}" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G')
    if [ -n "${AVAILABLE_GB}" ] && [ "${AVAILABLE_GB}" -lt 25 ]; then
        log_warn "Only ${AVAILABLE_GB}GB free. Need ~25GB for both models."
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] || exit 1
    fi

    log_info "Preflight checks passed."
}

# --- Create model directory ---
setup_dirs() {
    log_info "Setting up model directory: ${MODEL_DIR}"
    mkdir -p "${MODEL_DIR}"
    mkdir -p "${PERSONAPLEX_DIR}"
    mkdir -p "${LLAMA_DIR}"
}

# --- Download PersonaPlex 7B ---
download_personaplex() {
    log_info "=== Downloading PersonaPlex 7B v1 ==="
    log_info "Source: https://huggingface.co/${PERSONAPLEX_REPO}"
    log_info "Destination: ${PERSONAPLEX_DIR}"
    log_info "Expected size: ~14 GB"
    echo

    if [ -f "${PERSONAPLEX_DIR}/config.json" ]; then
        log_warn "PersonaPlex already exists at ${PERSONAPLEX_DIR}"
        read -p "Re-download? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping PersonaPlex download."
            return 0
        fi
    fi

    huggingface-cli download "${PERSONAPLEX_REPO}" \
        --local-dir "${PERSONAPLEX_DIR}" \
        --local-dir-use-symlinks False \
        --resume-download

    # Verify download
    if [ -f "${PERSONAPLEX_DIR}/config.json" ]; then
        log_info "PersonaPlex download verified (config.json present)"
        TOTAL_SIZE=$(du -sh "${PERSONAPLEX_DIR}" | cut -f1)
        log_info "PersonaPlex total size: ${TOTAL_SIZE}"
    else
        log_error "PersonaPlex download failed — config.json not found"
        exit 1
    fi
}

# --- Download Llama 3.1 8B Instruct (GGUF Q4_K_M) ---
download_llama() {
    log_info "=== Downloading Llama 3.1 8B Instruct (GGUF Q4_K_M) ==="
    log_info "Source: https://huggingface.co/${LLAMA_REPO}"
    log_info "File: ${LLAMA_FILE}"
    log_info "Destination: ${LLAMA_DIR}"
    log_info "Expected size: ~4.9 GB"
    echo

    LLAMA_PATH="${LLAMA_DIR}/${LLAMA_FILE}"

    if [ -f "${LLAMA_PATH}" ]; then
        log_warn "Llama GGUF already exists at ${LLAMA_PATH}"
        read -p "Re-download? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping Llama download."
            return 0
        fi
    fi

    huggingface-cli download "${LLAMA_REPO}" \
        "${LLAMA_FILE}" \
        --local-dir "${LLAMA_DIR}" \
        --local-dir-use-symlinks False \
        --resume-download

    # Verify download
    if [ -f "${LLAMA_PATH}" ]; then
        FILE_SIZE=$(du -sh "${LLAMA_PATH}" | cut -f1)
        log_info "Llama download verified: ${LLAMA_PATH} (${FILE_SIZE})"
    else
        log_error "Llama download failed — GGUF file not found"
        exit 1
    fi
}

# --- Verify all models ---
verify_all() {
    echo
    log_info "=== Verification Summary ==="

    local all_ok=true

    if [ -f "${PERSONAPLEX_DIR}/config.json" ]; then
        PP_SIZE=$(du -sh "${PERSONAPLEX_DIR}" | cut -f1)
        log_info "PersonaPlex 7B v1: OK (${PP_SIZE})"
    else
        log_error "PersonaPlex 7B v1: MISSING"
        all_ok=false
    fi

    if [ -f "${LLAMA_DIR}/${LLAMA_FILE}" ]; then
        LL_SIZE=$(du -sh "${LLAMA_DIR}/${LLAMA_FILE}" | cut -f1)
        log_info "Llama 3.1 8B Q4_K_M: OK (${LL_SIZE})"
    else
        log_error "Llama 3.1 8B Q4_K_M: MISSING"
        all_ok=false
    fi

    echo
    if [ "${all_ok}" = true ]; then
        log_info "All models downloaded and verified."
        log_info "Model directory: ${MODEL_DIR}"
        echo
        log_info "Next steps:"
        log_info "  1. Start PersonaPlex: python -m moshi.server --hf-repo ${PERSONAPLEX_REPO}"
        log_info "  2. Start BlessVoice:  python run.py --gpu"
    else
        log_error "Some models are missing. Re-run the script to retry."
        exit 1
    fi
}

# --- Main ---
main() {
    echo
    echo "======================================"
    echo "  BlessVoice Model Download Script"
    echo "======================================"
    echo

    local download_voice=true
    local download_llama=true

    # Parse arguments
    for arg in "$@"; do
        case ${arg} in
            --voice)
                download_llama=false
                ;;
            --llama)
                download_voice=false
                ;;
            --help|-h)
                echo "Usage: $0 [--voice] [--llama]"
                echo "  --voice   Download only PersonaPlex (voice model)"
                echo "  --llama   Download only Llama 3.1 8B (intelligence model)"
                echo "  (default) Download both models"
                exit 0
                ;;
        esac
    done

    check_prerequisites
    setup_dirs

    if [ "${download_voice}" = true ]; then
        download_personaplex
    fi

    if [ "${download_llama}" = true ]; then
        download_llama
    fi

    verify_all
}

main "$@"
