#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Legacy alias retained for compatibility. Docker-only 主流程請使用 ./start.sh。
exec ./start.sh
