#!/usr/bin/env python3
import argparse, sqlite3, os, sys, json

DB = os.environ.get('STATE_DB_PATH', 'state_api.db')

def conn():
    return sqlite3.connect(DB)

def add(args):
    with conn() as con:
        cur = con.cursor()
        cur.execute("INSERT INTO devices(hostname, ip, username, password, enabled) VALUES(?,?,?,?,?)",
                    (args.hostname, args.ip, args.user, args.password, 0 if args.disabled else 1))
        con.commit()
        print("Added device id", cur.lastrowid)

def list_cmd(args):
    with conn() as con:
        cur = con.cursor()
        cur.execute("SELECT id, hostname, ip, username, enabled FROM devices ORDER BY id")
        for row in cur.fetchall():
            print({"id":row[0], "hostname":row[1], "ip":row[2], "username":row[3], "enabled":bool(row[4])})

def update(args):
    fields = []
    params = []
    if args.hostname: fields += ["hostname=?"]; params += [args.hostname]
    if args.ip: fields += ["ip=?"]; params += [args.ip]
    if args.user: fields += ["username=?"]; params += [args.user]
    if args.password: fields += ["password=?"]; params += [args.password]
    if args.enable is not None: fields += ["enabled=?"]; params += [1 if args.enable else 0]
    if not fields:
        print("Nothing to update"); return
    params += [args.id]
    with conn() as con:
        con.execute("UPDATE devices SET " + ", ".join(fields) + " WHERE id=?", params)
        con.commit()
        print("Updated device id", args.id)

def delete(args):
    with conn() as con:
        con.execute("DELETE FROM devices WHERE id=?", (args.id,))
        con.commit()
        print("Deleted device id", args.id)

def main():
    p = argparse.ArgumentParser(description="Device manager (SQLite)")
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add"); pa.add_argument("--hostname"); pa.add_argument("--ip", required=True); pa.add_argument("--user", required=True); pa.add_argument("--password", required=True); pa.add_argument("--disabled", action="store_true"); pa.set_defaults(func=add)
    pl = sub.add_parser("list"); pl.set_defaults(func=list_cmd)
    pu = sub.add_parser("update"); pu.add_argument("id", type=int); pu.add_argument("--hostname"); pu.add_argument("--ip"); pu.add_argument("--user"); pu.add_argument("--password"); pu.add_argument("--enable", type=lambda s: s.lower() in ("1","true","yes","y")); pu.set_defaults(func=update)
    pd = sub.add_parser("delete"); pd.add_argument("id", type=int); pd.set_defaults(func=delete)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
