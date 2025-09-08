import sqlite3, os

DB = os.environ.get('STATE_DB_PATH', 'state_api.db')
con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT,
    ip TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_ts INTEGER DEFAULT (strftime('%s','now'))
)''')

# indices útiles
cur.execute('CREATE INDEX IF NOT EXISTS idx_devices_enabled ON devices(enabled)')
con.commit()
con.close()
print("Devices migration applied to", DB)
