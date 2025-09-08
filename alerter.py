# alerter.py
import requests
import json
import time
import logging

log = logging.getLogger("alerter")

def notify_console(device, iface, state, details):
    log_func = log.info if state in ("UP","DEGRADED") else log.warning
    log_func(f"[ALERT] {time.ctime()} - {device}/{iface} -> {state} : {details}")

def notify_webhook(url, payload, timeout=7):
    try:
        headers = {'Content-Type': 'application/json'}
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

def alert_for_event(device, iface, state, details, config):
    """Send alert to console and (optional) webhook.
    Supports providers: discord | slack | generic
    """
    # always print
    notify_console(device, iface, state, details)

    alerting = (config or {}).get('alerting', {}) or {}
    webhook = alerting.get('webhook')
    provider = (alerting.get('provider') or 'generic').lower()

    if webhook:
        if provider == 'discord':
            payload = { "content": f"[{device}/{iface}] {state} - {details}" }
        elif provider == 'slack':
            payload = { "text": f"[{device}/{iface}] {state} - {details}" }
        else:
            payload = {
                "time": int(time.time()),
                "device": device,
                "iface": iface,
                "state": state,
                "details": details
            }
        code, text = notify_webhook(webhook, payload)
        log.info(f"[WEBHOOK] provider={provider} status={code} resp={(text or '')[:200]}")



# --- Integraciones premium: Opsgenie y PagerDuty (Events API v2) ---
def notify_opsgenie(routing_key, message, note=None, priority="P3", tags=None, details=None, timeout=7):
    """Send alert to Opsgenie using Events API v2 (simple payload)."""
    url = "https://api.opsgenie.com/v2/alerts"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"GenieKey {routing_key}"
    }
    payload = {
        "message": message,
        "description": note or message,
        "priority": priority,
    }
    if tags:
        payload["tags"] = tags
    if details:
        payload["details"] = details
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        return r.status_code, r.text
    except Exception as e:
        log.exception("notify_opsgenie failed: %s", e)
        return None, str(e)

def notify_pagerduty(routing_key, summary, severity='error', source='mikrotik_collector', details=None, timeout=7):
    """Send event to PagerDuty Events API v2 (trigger event)."""
    url = "https://events.pagerduty.com/v2/enqueue"
    payload = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": source,
        }
    }
    if details:
        payload["payload"]["custom_details"] = details
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        return r.status_code, r.text
    except Exception as e:
        log.exception("notify_pagerduty failed: %s", e)
        return None, str(e)

# Helper to dispatch based on provider type
def alert_for_event_extended(device, iface, state, details, config):
    """Extended alert dispatcher supporting webhook, slack, discord, opsgenie, pagerduty."""
    alert_cfg = (config or {}).get('alerting') or {}
    provider = alert_cfg.get('provider') or alert_cfg.get('type') or 'webhook'
    if provider == 'opsgenie':
        key = alert_cfg.get('opsgenie_api_key') or alert_cfg.get('opsgenie_key') or alert_cfg.get('routing_key')
        if not key:
            log.error('Opsgenie routing key not configured')
            return
        msg = f"[{device}/{iface}] {state} - {details}"
        code, text = notify_opsgenie(key, msg, note=str(details), details={'device':device,'iface':iface,'state':state})
        log.info("[OPSGENIE] status=%s resp=%s", code, (text or '')[:200])
    elif provider == 'pagerduty':
        key = alert_cfg.get('pagerduty_routing_key') or alert_cfg.get('pagerduty_key') or alert_cfg.get('routing_key')
        if not key:
            log.error('PagerDuty routing key not configured')
            return
        summary = f"[{device}/{iface}] {state}"
        code, text = notify_pagerduty(key, summary, severity='critical' if state != 'UP' else 'info',
                                     source=device, details=details)
        log.info("[PAGERDUTY] status=%s resp=%s", code, (text or '')[:200])
    else:
        # fallback to original webhook-based behavior
        provider = provider or alert_cfg.get('provider')
        webhook = alert_cfg.get('webhook') or alert_cfg.get('url')
        if webhook:
            payload = {
                "time": int(time.time()),
                "device": device,
                "iface": iface,
                "state": state,
                "details": details
            }
            code, text = notify_webhook(webhook, payload)
            log.info(f"[WEBHOOK] provider={provider} status={code} resp={(text or '')[:200]}")
        else:
            # console fallback
            notify_console(device, iface, state, details)
