#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLCHAIN_DIR="${TOOLCHAIN_DIR:-$HERE/../usdaeco-toolchain}"
CORE_DIR="${CORE_DIR:-$HERE/../usdaeco-core}"
AXIS_DIR="${AXIS_DIR:-$HERE/../usdaeco-axis}"
BUILDUP_DIR="${BUILDUP_DIR:-$HERE/../usdaeco-buildup}"
exec bash "$TOOLCHAIN_DIR/build.sh" usdAecoRepeat "$HERE" \
    --dep "${CORE_PLUGIN_DIR:-$CORE_DIR/out/plugins/usdAeco/resources}" \
    --dep "${AXIS_PLUGIN_DIR:-$AXIS_DIR/out/plugins/usdAecoAxis/resources}" \
    --dep "${BUILDUP_PLUGIN_DIR:-$BUILDUP_DIR/usdAecoBuildUp}" "$@"
