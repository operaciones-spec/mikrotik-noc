# collector_api.py
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from routeros_api import RouterOsApiPool
from state_store import StateStore
from classifier import classify_interface
from alerter import alert_for_event, alert_for_event_extended
from prometheus_client import start_http_server, Gauge

log = logging.getLogger("collector")

# Prometheus metrics
IF_UP = Gauge('noc_interface_up', '1 if interface is up (UP), 0 otherwise', ['device','iface','state'])
IF_RX_BPS = Gauge('noc_interface_rx_bps', 'Interface rx bits/sec', ['device','iface'])
IF_TX_BPS = Gauge('noc_interface_tx_bps', 'Interface tx bits/sec', ['device', 'iface'])
IF_ERR_RATE = Gauge('noc_interface_err_per_sec', 'Interface errors per second', ['device','iface'])

def _parse_speed_to_mbps(speed):
    # Keep in sync with classifier
    if isinstance(speed, int):
        return speed
    from classifier import _parse_speed_to_mbps as _p
    return _p(speed)

def poll_device(dev_cfg):
    """Return dict: { 'device': name, 'ifaces': {iface: snapshot, ...} }"""
    name = dev_cfg['name']
    host = dev_cfg['host']
    user = dev_cfg['user']
    password = dev_cfg['password']
    port = dev_cfg.get('port', 8728)
    expected_speed = dev_cfg.get('expected_speed_mbps')
    disabled_if = set(dev_cfg.get('disabled_ifaces', []) or [])

    # try to create API connection with small retry
    api_pool = None
    for _retry in range(2):
        try:
            api_pool = RouterOsApiPool(host, username=user, password=password, port=port, plaintext_login=True)
            break
        except Exception as _e:
            log.warning("RouterOS API pool creation failed for %s: %s - retrying", host, _e)
            time.sleep(0.5)
    if not api_pool:
        log.error("Could not create RouterOS API pool for %s", host)
        raise
    api = api_pool.get_api()
    try:
        # Fetch interfaces
        iface_res = api.get_resource('/interface')
        eth_res = api.get_resource('/interface/ethernet')

        ifaces = {}
        now = int(time.time())
        for i in iface_res.get():
            ifname = i.get('name')
            if not ifname or ifname in disabled_if:
                continue
            # Basic fields
            snap = {
                'ts': now,
                'name': ifname,
                'disabled': i.get('disabled', 'false') in ('true', True),
                'carrier': i.get('running', 'false') in ('true', True),
                'rx_bytes': int(i.get('rx-byte', 0) or 0),
                'tx_bytes': int(i.get('tx-byte', 0) or 0),
                'rx_errors': int(i.get('rx-error', 0) or 0),
                'tx_errors': int(i.get('tx-error', 0) or 0),
                'rx_drops': int(i.get('rx-drop', 0) or 0),
                'tx_drops': int(i.get('tx-drop', 0) or 0),
                'link_downs': int(i.get('link-downs', 0) or 0),
            }
            # Ethernet-specific
            try:
                e = eth_res.get(**{'name': ifname})
                if e:
                    e = e[0]
                    snap['speed_mbps'] = _parse_speed_to_mbps(e.get('speed'))
            except Exception:
                pass
            if expected_speed:
                snap['expected_speed_mbps'] = int(expected_speed)
            ifaces[ifname] = snap
        return {'device': name, 'ifaces': ifaces}
    finally:
        try:
            api_pool.disconnect()
        except Exception:
            pass

def start_collector(config):
    logging.basicConfig(
        level=getattr(logging, (config.get('logging',{}).get('level','INFO')).upper()),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )
    devices = config['devices']
    poll_interval = int(config.get('poll_interval', 15))
    thresholds = config.get('thresholds', {}) or {}
    prom = config.get('prometheus', {}) or {}
    db_path = config.get('db_path', 'iface_state.db')

    db = StateStore(db_path)

    if prom.get('enabled'):
        prom_port = int(prom.get('port') or prom.get('listen_port') or 8000)
        prom_addr = prom.get('listen_addr') or prom.get('addr') or '0.0.0.0'
        try:
            # start_http_server signature may vary; try (port, addr)
            start_http_server(prom_port, prom_addr)
        except TypeError:
            start_http_server(prom_port)
        log.info(f"Prometheus exporter on {prom_addr}:{prom_port}")

    executor = ThreadPoolExecutor(max_workers=min(16, max(1, len(devices))))

    while not shutdown_event.is_set():
        start = time.time()

        futures = [executor.submit(poll_device, d) for d in devices]
        results = []
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                log.exception("poll_device failed: %s", e)

        for r in results:
            device_name = r['device']
            for ifname, cur in (r.get('ifaces') or {}).items():
                prev = db.get_last_state(device_name, ifname)

                # maintain downs_ts window list in current snapshot
                downs_ts = list((prev or {}).get('downs_ts') or [])
                # If link_downs increased, push timestamps now (collector-level safety as well)
                if prev:
                    inc = max(0, int(cur.get('link_downs',0)) - int(prev.get('link_downs',0)))
                    if inc:
                        downs_ts.extend([cur['ts']]*inc)
                    # Purge old entries (> 24h, conservative; classifier prunes again by window)
                    downs_ts = [x for x in downs_ts if cur['ts'] - x <= 86400]
                cur['downs_ts'] = downs_ts

                state, info = classify_interface(cur, prev, thresholds)

                # metrics (derive rates against prev)
                try:
                    IF_UP.labels(device=device_name, iface=ifname, state=state).set(1 if state == 'UP' else 0)
                    if prev:
                        interval = max(1, cur['ts'] - prev.get('ts', cur['ts']))
                        rx_bps = ((cur.get('rx_bytes',0) - prev.get('rx_bytes',0)) * 8) / interval
                        tx_bps = ((cur.get('tx_bytes',0) - prev.get('tx_bytes',0)) * 8) / interval
                        err_per_sec = ((cur.get('rx_errors',0) - prev.get('rx_errors',0)) + (cur.get('tx_errors',0) - prev.get('tx_errors',0))) / interval
                        IF_RX_BPS.labels(device=device_name, iface=ifname).set(max(0, rx_bps))
                        IF_TX_BPS.labels(device=device_name, iface=ifname).set(max(0, tx_bps))
                        IF_ERR_RATE.labels(device=device_name, iface=ifname).set(max(0, err_per_sec))
                except Exception as e:
                    log.warning("Prom metric update error: %s", e)

                # store current snapshot
                db.save_state(device_name, ifname, cur)

                # transitions and initial alert logic
                if prev:
                    from classifier import classify_interface as _cf
                    prev_state, _ = _cf(prev, None, thresholds)  # classify previous in isolation
                    if prev_state != state:
                        db.append_event(device_name, ifname, f"state_change {prev_state} -> {state} : {info}")
                        alert_for_event_extended(device_name, ifname, state, info, config)
                else:
                    # First time seen: if not UP, alert
                    if state != "UP":
                        db.append_event(device_name, ifname, f"initial_state {state} : {info}")
                        alert_for_event_extended(device_name, ifname, state, info, config)

        # sleep until next poll
        duration = time.time() - start
        to_sleep = max(1, poll_interval - duration)
        time.sleep(to_sleep)
