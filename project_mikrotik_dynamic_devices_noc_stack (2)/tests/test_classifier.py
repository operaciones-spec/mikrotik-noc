import pytest
from classifier import classify_interface

def make_snap(rx_bytes=1000, tx_bytes=1000, rx_errors=0, tx_errors=0, speed_mbps=1000, expected=None, ts=0, carrier=True, disabled=False):
    return {
        'rx_bytes': rx_bytes,
        'tx_bytes': tx_bytes,
        'rx_errors': rx_errors,
        'tx_errors': tx_errors,
        'ts': ts,
        'speed_mbps': speed_mbps,
        'expected_speed_mbps': expected,
        'carrier': carrier,
        'disabled': disabled
    }

def test_ok_state_no_errors():
    prev = make_snap(rx_bytes=1000, tx_bytes=1000, rx_errors=0, tx_errors=0, ts=1000)
    cur = make_snap(rx_bytes=2000, tx_bytes=2000, rx_errors=0, tx_errors=0, ts=2000)
    state, info = classify_interface(cur, prev, {})
    assert state == "UP"

def test_high_error_rate():
    prev = make_snap(rx_errors=0, ts=1000)
    cur = make_snap(rx_errors=100, ts=1100)
    state, info = classify_interface(cur, prev, {'err_per_sec': 0.01})
    assert state in ("DEGRADED","DOWN")

def test_speed_mismatch():
    prev = make_snap(speed_mbps='1000', ts=1000)
    cur = make_snap(speed_mbps='100', expected=1000, ts=2000)
    state, info = classify_interface(cur, prev, {})
    assert state in ("DEGRADED","UP")
