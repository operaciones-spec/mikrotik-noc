# run_api_collector.py
import json
import sys
import argparse
from dotenv import load_dotenv
from collector_api import start_collector

def main():
    # load environment variables from .env (if present)
    load_dotenv()

    parser = argparse.ArgumentParser(description="MikroTik NOC collector")
    parser.add_argument("--config", "-c", default="mi_config.json",
                        help="Ruta al archivo de configuración JSON (default: mi_config.json)")
    args = parser.parse_args()
    cfg_path = args.config
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    start_collector(cfg)

if __name__ == "__main__":
    main()
