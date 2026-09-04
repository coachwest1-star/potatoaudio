#!/usr/bin/env python3
from flask import Flask,jsonify,request,send_from_directory
from mpd import MPDClient
import os,subprocess,re,json,tempfile
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); WEB=os.path.join(BASE,'web'); DATA='/var/lib/potato-audio'; RADIO=f'{DATA}/radio.json'; OUTPUT=f'{DATA}/audio-output.json'
app=Flask(__name__,static_folder=WEB,static_url_path='')
def cli():
 c=MPDClient(); c.timeout=5; c.connect('127.0.0.1',6600); return c
def call(fn):
 c=cli()
 try:return fn(c)
 finally:
  try:c.close();c.disconnect()
  except:pass
def rj(p,d):
 try:return json.load(open(p,encoding='utf-8'))
 except:return d
def wj(p,d):
 os.makedirs(os.path.dirname(p),exist_ok=True); fd,t=tempfile.mkstemp(dir=os.path.dirname(p)); f=os.fdopen(fd,'w'); json.dump(d,f,indent=2); f.close(); os.replace(t,p)
def devices():
 p=subprocess.run(['aplay','-l'],capture_output=True,text=True,timeout=6); out=[]
 rx=re.compile(r'card\s+(\d+):\s*([^\[]+)\[([^\]]+)\],\s*device\s+(\d+):\s*([^\[]+)\[([^\]]+)\]',re.I)
 for line in (p.stdout+p.stderr).splitlines():
  m=rx.search(line)
  if m:
   name=' '.join(m.groups()).lower(); kind='HDMI' if 'hdmi' in name else ('USB DAC' if 'usb' in name else 'ALSA')
   out.append({'card':int(m.group(1)),'device':int(m.group(4)),'card_name':m.group(3).strip(),'device_name':m.group(6).strip(),'alsa':f'hw:{m.group(1)},{m.group(4)}','kind':kind})
 return out
@app.get('/')
def index():return send_from_directory(WEB,'index.html')
@app.get('/display')
def display():return send_from_directory(WEB,'display.html')
@app.get('/api/status')
def status():
 def f(c):
  s=c.status(); x=c.currentsong(); return {'state':s.get('state','stop'),'volume':int(s.get('volume',0)) if str(s.get('volume','')).lstrip('-').isdigit() else 0,'elapsed':float(s.get('elapsed',0) or 0),'duration':float(s.get('duration',0) or 0),'audio':s.get('audio',''),'bitrate':s.get('bitrate',''),'song':x}
 return jsonify(call(f))
@app.post('/api/control/<a>')
def control(a):
 if a not in {'play','pause','stop','next','previous'}:return jsonify(error='Unknown action'),400
 def f(c): c.pause(1 if c.status().get('state')=='play' else 0) if a=='pause' else getattr(c,a)()
 call(f); return jsonify(ok=True)
@app.post('/api/volume')
def volume():
 v=max(0,min(100,int((request.get_json(silent=True) or {}).get('volume',50)))); call(lambda c:c.setvol(v)); return jsonify(ok=True,volume=v)
@app.get('/api/queue')
def queue():return jsonify(call(lambda c:c.playlistinfo()))
@app.delete('/api/queue')
def clear():call(lambda c:c.clear());return jsonify(ok=True)
@app.get('/api/library')
def library():
 q=request.args.get('q','').lower()
 def f(c):return [x for x in c.listallinfo() if x.get('file') and (not q or q in ' '.join(str(x.get(k,'')) for k in ('title','artist','album','file')).lower())][:2000]
 return jsonify(call(f))
@app.post('/api/queue/add')
def add():
 u=(request.get_json(silent=True) or {}).get('file'); call(lambda c:c.add(u)); return jsonify(ok=True)
@app.post('/api/play/file')
def playfile():
 u=(request.get_json(silent=True) or {}).get('file')
 def f(c):c.clear();c.add(u);c.play()
 call(f);return jsonify(ok=True)
@app.post('/api/update')
def update():call(lambda c:c.update());return jsonify(ok=True)
@app.get('/api/radio')
def radios():return jsonify(rj(RADIO,[]))
@app.post('/api/radio')
def addradio():
 b=request.get_json(silent=True) or {}; name=str(b.get('name','')).strip(); url=str(b.get('url','')).strip()
 if not name or not re.match(r'^https?://',url,re.I):return jsonify(error='Station name and direct http/https stream URL required'),400
 a=rj(RADIO,[]); s={'id':max([int(x.get('id',0)) for x in a]+[0])+1,'name':name,'url':url,'logo':str(b.get('logo','')).strip(),'category':str(b.get('category','')).strip()};a.append(s);wj(RADIO,a);return jsonify(s),201
@app.delete('/api/radio/<int:i>')
def delradio(i):wj(RADIO,[s for s in rj(RADIO,[]) if int(s.get('id',-1))!=i]);return jsonify(ok=True)
@app.post('/api/radio/<int:i>/play')
def playradio(i):
 s=next((s for s in rj(RADIO,[]) if int(s.get('id',-1))==i),None)
 if not s:return jsonify(error='Station not found'),404
 def f(c):c.clear();c.add(s['url']);c.play()
 call(f);return jsonify(ok=True)
@app.get('/api/audio-devices')
def audio():return jsonify(devices=devices(),selected=rj(OUTPUT,{'device':'default'}).get('device','default'))
@app.post('/api/audio-output')
def setaudio():
 d=str((request.get_json(silent=True) or {}).get('device','')).strip(); valid={'default'}|{x['alsa'] for x in devices()}
 if d not in valid:return jsonify(error='Audio device not detected'),400
 p=subprocess.run(['sudo','/usr/local/sbin/potato-audio-set-output',d],capture_output=True,text=True,timeout=20)
 if p.returncode:return jsonify(error=(p.stderr or p.stdout).strip()),500
 wj(OUTPUT,{'device':d});return jsonify(ok=True,device=d)
@app.post('/api/audio-test')
def testaudio():
 d=str((request.get_json(silent=True) or {}).get('device','default'));p=subprocess.run(['sudo','/usr/local/sbin/potato-audio-test-output',d],capture_output=True,text=True,timeout=20)
 return (jsonify(ok=True) if p.returncode==0 else (jsonify(error=(p.stderr or p.stdout).strip()),500))
@app.get('/api/health')
def health():
 try:return jsonify(ok=True,mpd=call(lambda c:c.mpd_version),version='2.0.0')
 except Exception as e:return jsonify(ok=False,error=str(e)),503
if __name__=='__main__':app.run(host='0.0.0.0',port=8080)
