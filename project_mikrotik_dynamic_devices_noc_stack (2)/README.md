# MikroTik NOC Collector - Entregable

Proyecto que monitoriza interfaces de dispositivos MikroTik, expone métricas para Prometheus y envía alertas vía webhook.

## Contenido del paquete
- Código Python del collector.
- `mi_config.json` — configuración de ejemplo.
- `requirements.txt` — dependencias.
- `Dockerfile`, `docker-compose.yml`.
- `tests/` — tests unitarios (pytest).
- `.github/workflows/ci.yml` — CI para ejecutar tests.
- `extras/systemd/mikrotik_collector.service` — Ejemplo unit para systemd.

## Instalación (Ubuntu)
1. Instalar sistema y crear venv:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configuración
- Editar `mi_config.json` para añadir dispositivos y credenciales.
- Keys admitidas: `host`/`ip`, `port`/`api_port`, `password`/`pass`.
- **No** subir credenciales a repositorio público.

3. Ejecución local
```bash
python run_api_collector.py --config mi_config.json
```

4. Docker
```bash
docker build -t mikrotik_collector .
docker run -v $(pwd)/mi_config.json:/app/mi_config.json:ro -p 9102:9102 mikrotik_collector
```
o con docker-compose:
```bash
docker-compose up -d --build
```

5. systemd
Copiar `extras/systemd/mikrotik_collector.service` a `/etc/systemd/system/` y habilitar:
```bash
sudo cp extras/systemd/mikrotik_collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mikrotik_collector.service
```

## Desarrollo y CI
- Tests con `pytest` (ver `tests/`).
- GitHub Actions workflow incluido en `.github/workflows/ci.yml`.

## Monetización: propuesta de roadmap
1. Paquete "appliance" (Docker image) + panel SaaS: ofrecer servicio en la nube que centralice métricas y alertas.
2. Paquetes de integración: PagerDuty, Opsgenie, Slack, Discord, email.
3. Módulos premium: historic baseline, anomaly detection, reports y SLAs.
4. Servicios gestionados: despliegue, soporte y tuning.

## Notas finales
He realizado validaciones básicas y tests unitarios. Si quieres, puedo:
- Implementar integración Opsgenie/PagerDuty.
- Crear UI básica (React) y endpoints REST para multi-tenant.
- Añadir Vault/.env parsing avanzado para credenciales.


## Nuevas features añadidas
- Integración Opsgenie y PagerDuty (configurar en `mi_config.json` o via .env).
- API REST (Flask) en `api_server.py` para exponer eventos/estados.
- UI básica React en `ui/` (Vite). Use `npm install` y `npm run dev`.
- Soporte para .env y ejemplo `.env.example`.
- Docker multi-stage y `docker-compose.prod.yml`.
- Scaffold para SaaS: `migrate_saas.py`.

## Gestión de dispositivos (sin editar archivos)
1) Crear tabla y agregar un equipo:
```bash
python migrate_devices.py
python device_manager.py add --ip 192.168.88.1 --user admin --password mypass --hostname RB1
python device_manager.py list
```
2) El collector leerá automáticamente desde la base (`STATE_DB_PATH=state_api.db`).

## One-command
```bash
./run.sh
```
- Lanza API (`:5000`) y collector (exporta Prometheus en `:9102`).

