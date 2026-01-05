#!/bin/bash
# Start SAM Brain MLX Server

cd "$(dirname "$0")"

# Activate venv
source ~/.sam/mlx_venv/bin/activate

# Start server
exec python3 mlx_server.py "$@"
