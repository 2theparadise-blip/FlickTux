#!/usr/bin/env bash
# FlickTux ARM64 (Raspberry Pi OS / Cyberdeck) Cross Build Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

TARGET="${1:-aarch64-unknown-linux-musl}"

echo "=========================================================="
echo "  🐧 FlickTux: ARM64 Build -> Target: ${TARGET}"
echo "=========================================================="

# Check if target is installed
if ! rustup target list | grep "${TARGET} (installed)" >/dev/null 2>&1; then
    echo "📥 Adding target ${TARGET}..."
    rustup target add "${TARGET}"
fi

# Build release binary
echo "🔨 Building release binary for ${TARGET}..."
cargo build --release --target "${TARGET}"

OUTPUT="target/${TARGET}/release/flktux"
if [[ -f "${OUTPUT}" ]]; then
    echo "=========================================================="
    echo "✅ Build successful!"
    echo "Binary location: ${OUTPUT}"
    ls -lh "${OUTPUT}"
    echo "=========================================================="
fi
