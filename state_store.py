# state_store.py
import sqlite3
import json
import time
from typing import Optional

class StateStore:
    def __init__(self, path="state_api.db"):
        self.path = path
        self._init_db()

    def _init_db(self):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS iface_state (
            device text,
            iface text,
            ts integer,
            payload text,
            PRIMARY KEY (device, iface)
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device text,
            iface text,
            ts integer,
            event text
        )
        """)
        con.commit()
        con.close()

    def save_iface_snapshot(self, device, iface, payload: dict):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO iface_state(device, iface, ts, payload) VALUES (?,?,?,?)",
            (device, iface, int(time.time()), json.dumps(payload))
        )
        con.commit()
        con.close()

    def load_iface_snapshot(self, device, iface) -> Optional[dict]:
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute("SELECT payload FROM iface_state WHERE device=? AND iface=?", (device, iface))
        row = cur.fetchone()
        con.close()
        if not row:
            return None
        return json.loads(row[0])

    def append_event(self, device, iface, event_text):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute("INSERT INTO event_log(device, iface, ts, event) VALUES (?,?,?,?)",
                    (device, iface, int(time.time()), event_text))
        con.commit()
        con.close()


# helper for external tooling to get a connection (used by api_server)
def _connect_db(path):
    import sqlite3
    return sqlite3.connect(path)
