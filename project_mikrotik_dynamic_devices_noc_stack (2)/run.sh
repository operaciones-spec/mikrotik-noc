#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1
export STATE_DB_PATH=${STATE_DB_PATH:-state_api.db}

# venv
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# migraciones
python migrate_devices.py
python migrate_saas.py || true  # opcional

# arrancar API y Collector en background simple
# (para producción usar systemd o docker-compose)
( python api_server.py & echo $! > .api.pid ) &
( python run_api_collector.py --config mi_config.json & echo $! > .collector.pid ) &

echo "API en http://127.0.0.1:5000  |  Prometheus exporter en :9102"
echo "Para detener: kill $(cat .api.pid) $(cat .collector.pid)"
