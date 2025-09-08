import React, {useEffect, useState} from 'react';

export default function App(){
  const [devices, setDevices] = useState([]);
  const [form, setForm] = useState({hostname:'', ip:'', username:'', password:''});
  const load = ()=> fetch('/api/v1/devices').then(r=>r.json()).then(setDevices);
  useEffect(()=>{ load(); },[]);
  const save = async (e)=>{
    e.preventDefault();
    await fetch('/api/v1/devices', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(form)});
    setForm({hostname:'', ip:'', username:'', password:''});
    load();
  };
  const del = async (id)=>{ await fetch('/api/v1/devices/'+id, {method:'DELETE'}); load(); };
  return (
    <div style={{fontFamily:'Inter, sans-serif', padding:20, maxWidth:900, margin:'0 auto'}}>
      <h1>MikroTik NOC</h1>
      <h2>Dispositivos</h2>
      <form onSubmit={save} style={{display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:8, marginBottom:16}}>
        <input placeholder="Hostname" value={form.hostname} onChange={e=>setForm({...form, hostname:e.target.value})}/>
        <input placeholder="IP" value={form.ip} onChange={e=>setForm({...form, ip:e.target.value})} required/>
        <input placeholder="Usuario" value={form.username} onChange={e=>setForm({...form, username:e.target.value})} required/>
        <input placeholder="Password" type="password" value={form.password} onChange={e=>setForm({...form, password:e.target.value})} required/>
        <button>Agregar</button>
      </form>
      <table border="1" cellPadding="6" style={{borderCollapse:'collapse', width:'100%'}}>
        <thead><tr><th>ID</th><th>Hostname</th><th>IP</th><th>Usuario</th><th>Enabled</th><th>Acciones</th></tr></thead>
        <tbody>
          {devices.map(d=>(
            <tr key={d.id}><td>{d.id}</td><td>{d.hostname||'-'}</td><td>{d.ip}</td><td>{d.username}</td><td>{String(d.enabled)}</td>
              <td><button onClick={()=>del(d.id)}>Eliminar</button></td></tr>
          ))}
        </tbody>
      </table>
      <h2 style={{marginTop:32}}>Eventos recientes</h2>
      <Events/>
    </div>
  )
}

function Events(){
  const [events, setEvents] = useState([]);
  useEffect(()=>{ fetch('/api/v1/events').then(r=>r.json()).then(setEvents); },[]);
  return (
    <ul>
      {events.map(e=>(
        <li key={e.ts + e.device + e.iface}><strong>{e.device}/{e.iface}</strong> — {new Date(e.ts*1000).toLocaleString()}: {e.event}</li>
      ))}
    </ul>
  )
}
