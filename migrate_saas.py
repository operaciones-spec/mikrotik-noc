# simple migration script to create tables for multi-tenant event store
import sqlite3, os
DB = os.environ.get('SAAS_DB', 'saas.db')
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_ts INTEGER DEFAULT (strftime('%s','now'))
)''')
cur.execute('''CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    device TEXT,
    iface TEXT,
    ts INTEGER,
    event TEXT,
    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
)''')
con.commit()
con.close()
print("Migrations applied to", DB)
