# classifier.py
from datetime import datetime, timezone

# thresholds come from config or defaults
DEFAULTS = {
    "err_per_sec": 1.0,
    "flaps_window": 300,
    "flaps_count": 3
}

def _counter_delta(prev, cur, max_counter=None):
    """Return non-negative delta with optional wrap handling."""
    if prev is None or cur is None:
        return 0
    d = cur - prev
    if d < 0 and max_counter:
        # wrap: add max range
        d = (max_counter - prev) + cur + 1
    return max(0, d)

def compute_deltas(prev, cur, interval_seconds):
    """Compute deltas for counters and error rates. prev/cur are dicts with counters."""
    deltas = {}
    if not prev:
        return deltas
    # Assume 64-bit counters unless explicitly small; use non-negative clamps
    for k in ['rx_errors','tx_errors','rx_drops','tx_drops','rx_bytes','tx_bytes','link_downs']:
        p = int(prev.get(k, 0) or 0)
        c = int(cur.get(k, 0) or 0)
        deltas[k] = _counter_delta(p, c)
    deltas['err_rate'] = (deltas['rx_errors'] + deltas['tx_errors']) / max(1, interval_seconds)
    return deltas

def _parse_speed_to_mbps(speed_str):
    """Robust speed parser: '1Gbps','2.5Gbps','1000Mbps','10G','100M' -> Mbps (int).
    Returns 0 if unknown.
    """
    if not speed_str:
        return 0
    s = str(speed_str).strip().lower().replace('bps','').replace('b/s','')
    s = s.replace('mbit','m').replace('gbit','g')
    # Extract number and unit
    import re
    m = re.match(r'^\s*([0-9]+(?:\.[0-9]+)?)\s*([gm]?)\s*$', s)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2)
    if unit == 'g':
        val *= 1000.0
    elif unit in ('m',''):
        val *= 1.0
    try:
        return int(round(val))
    except Exception:
        return 0

def classify_interface(cur_snapshot, prev_snapshot, thresholds):
    t = DEFAULTS.copy()
    t.update(thresholds or {})

    # quick checks
    if cur_snapshot.get('disabled'):
        return "ADMIN_DOWN", {"reason":"admin disabled"}

    if not cur_snapshot.get('carrier', True):
        return "DOWN", {"reason":"no carrier"}

    # compute error rate
    err_rate = 0.0
    if prev_snapshot:
        dt = max(1, cur_snapshot.get('ts',0) - prev_snapshot.get('ts',0))
        deltas = compute_deltas(prev_snapshot, cur_snapshot, dt)
        err_rate = deltas.get('err_rate', 0.0)
        # windowed flapping: we use downs_ts list within cur_snapshot
        downs_ts = list(cur_snapshot.get('downs_ts') or [])
        now = cur_snapshot.get('ts', 0)
        window = int(t.get('flaps_window', 300))
        # purge old
        downs_ts = [x for x in downs_ts if now - x <= window]
        # If link_downs increased this interval, add events now
        ld_cur = int(cur_snapshot.get('link_downs', 0) or 0)
        ld_prev = int(prev_snapshot.get('link_downs', 0) or 0)
        inc = max(0, ld_cur - ld_prev)
        if inc:
            downs_ts.extend([now]*inc)
        flap_detected = len(downs_ts) >= int(t.get('flaps_count', 3))
    else:
        flap_detected = False

    if flap_detected:
        return "DOWN", {"reason": f"flapping", "err_rate": err_rate}

    if err_rate > float(t['err_per_sec']):
        return "DOWN", {"reason": f"high_error_rate {err_rate:.2f}/s", "err_rate": err_rate}

    # optional speed mismatch (if expected provided)
    expected = cur_snapshot.get('expected_speed_mbps')
    # derive speed_mbps if string
    speed_actual = cur_snapshot.get('speed_mbps')
    if isinstance(speed_actual, str):
        speed_actual = _parse_speed_to_mbps(speed_actual)
    speed_actual = int(speed_actual or 0)
    if expected and speed_actual and int(expected) != speed_actual:
        return "DEGRADED", {"reason": f"speed_mismatch {speed_actual} != expected {expected}"}

    # else OK
    return "UP", {"reason":"carrier OK", "err_rate": err_rate}
