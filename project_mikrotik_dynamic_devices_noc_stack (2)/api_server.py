from flask import Flask, jsonify, request, abort
from state_store import StateStore
import sqlite3
import os

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY")

from flask import abort
@app.before_request
def _auth_middleware():
    if not API_KEY:
        return  # no auth enforced if not set
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        abort(401)

DB_PATH = os.environ.get('STATE_DB_PATH', 'state_api.db')
store = StateStore(DB_PATH)

@app.route('/api/v1/health', methods=['GET'])
def health():
    return jsonify({'status':'ok'})

@app.route('/api/v1/devices', methods=['GET'])
def list_devices():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, hostname, ip, username, enabled FROM devices ORDER BY id")
    rows = [{"id": r[0], "hostname": r[1], "ip": r[2], "username": r[3], "enabled": bool(r[4])} for r in cur.fetchall()]
    con.close()
    return jsonify(rows)

@app.route('/api/v1/devices', methods=['POST'])
def create_device():
    data = request.get_json(force=True)
    for k in ('ip','username','password'):
        if k not in data: return jsonify({"error": f"missing {k}"}), 400
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO devices(hostname, ip, username, password, enabled) VALUES(?,?,?,?,?)",
                (data.get('hostname'), data['ip'], data['username'], data['password'], 1 if data.get('enabled', True) else 0))
    con.commit()
    did = cur.lastrowid
    con.close()
    return jsonify({"id": did}), 201

@app.route('/api/v1/devices/<int:did>', methods=['PUT'])
def update_device(did):
    data = request.get_json(force=True)
    fields, params = [], []
    for k in ('hostname','ip','username','password'):
        if k in data: fields.append(f"{k}=?"); params.append(data[k])
    if 'enabled' in data: fields.append("enabled=?"); params.append(1 if data['enabled'] else 0)
    if not fields: return jsonify({"error":"nothing to update"}), 400
    params.append(did)
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE devices SET " + ", ".join(fields) + " WHERE id=?", params)
    con.commit()
    con.close()
    return jsonify({"id": did})

@app.route('/api/v1/devices/<int:did>', methods=['DELETE'])
def delete_device(did):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM devices WHERE id=?", (did,))
    con.commit()
    con.close()
    return jsonify({"deleted": did})

def list_devices():
    # Return list of devices from iface_state table (simple)
    con = store._connect()
    cur = con.cursor()
    cur.execute("SELECT DISTINCT device FROM iface_state")
    rows = [r[0] for r in cur.fetchall()]
    con.close()
    return jsonify({'devices': rows})

@app.route('/api/v1/device/<device>/ifaces', methods=['GET'])
def list_ifaces(device):
    con = store._connect()
    cur = con.cursor()
    cur.execute("SELECT iface, payload FROM iface_state WHERE device=?", (device,))
    rows = [{'iface': r[0], 'payload': r[1]} for r in cur.fetchall()]
    con.close()
    return jsonify(rows)

@app.route('/api/v1/events', methods=['GET'])
def events():
    con = store._connect()
    cur = con.cursor()
    cur.execute("SELECT device, iface, ts, event FROM event_log ORDER BY ts DESC LIMIT 200")
    rows = [{'device': r[0], 'iface': r[1], 'ts': r[2], 'event': r[3]} for r in cur.fetchall()]
    con.close()
    return jsonify(rows)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('API_PORT', 5000)))
