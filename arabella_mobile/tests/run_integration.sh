#!/usr/bin/env bash
# Phase 1 Step 9 — FFI integration test runner.
#
# Starts the Python fan simulator, compiles ffi_test.c against the Rust
# staticlib, runs the driver, and reports the result.
#
# Usage (from anywhere inside the repo):
#   arabella_mobile/tests/run_integration.sh
#
# Options:
#   --no-rebuild   skip recompiling ffi_test (use existing binary)
#   --keep-sim     leave the simulator running after the test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$MOBILE_DIR/../.." && pwd)"

PROTOCOL_DIR="$MOBILE_DIR/protocol"
INCLUDE_DIR="$PROTOCOL_DIR/include"
STATICLIB="$PROTOCOL_DIR/target/debug/libarabella_protocol.a"
DRIVER_SRC="$SCRIPT_DIR/ffi_test.c"
DRIVER_BIN="$SCRIPT_DIR/ffi_test"

REBUILD=1
KEEP_SIM=0
for arg in "$@"; do
    case "$arg" in
        --no-rebuild) REBUILD=0 ;;
        --keep-sim)   KEEP_SIM=1 ;;
    esac
done

# ── 1. Build the Rust staticlib ──────────────────────────────────────────────
echo "==> Building Rust protocol library..."
(cd "$PROTOCOL_DIR" && cargo build 2>&1)

# ── 2. Compile the C driver ──────────────────────────────────────────────────
if [[ "$REBUILD" -eq 1 ]]; then
    echo "==> Compiling ffi_test.c..."
    gcc "$DRIVER_SRC" \
        -I "$INCLUDE_DIR" \
        "$STATICLIB" \
        -lpthread -ldl -lm \
        -o "$DRIVER_BIN"
    echo "    Compiled: $DRIVER_BIN"
fi

# ── 3. Start the Python simulator ───────────────────────────────────────────
echo "==> Starting fan simulator..."
cd "$REPO_ROOT"
python3 -m ventocontrol.simulator &
SIM_PID=$!
echo "    Simulator PID: $SIM_PID"
sleep 1   # allow socket to open

# ── 4. Run the C driver ──────────────────────────────────────────────────────
echo ""
"$DRIVER_BIN" 127.0.0.1 SIMFAN0000000001 1111
RESULT=$?

# ── 5. Cleanup ───────────────────────────────────────────────────────────────
if [[ "$KEEP_SIM" -eq 0 ]]; then
    kill "$SIM_PID" 2>/dev/null || true
    echo ""
    echo "==> Simulator stopped."
fi

exit $RESULT
