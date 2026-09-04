#!/usr/bin/env python3
from flask import Flask, jsonify, request, send_from_directory
from mpd import MPDClient, CommandError
import os, subprocess, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web")
MPD_HOST = os.environ.get("MPD_HOST", "127.0.0.1")
MPD_PORT = int(os.environ.get("MPD_PORT", "6600"))

app = Flask(__name__, static_folder=WEB, static_url_path="")

def client():
    c = MPDClient()
    c.timeout = 5
    c.idletimeout = None
    c.connect(MPD_HOST, MPD_PORT)
    return c

def mpd_call(fn):
    c = client()
    try:
        return fn(c)
    finally:
        try: c.close()
        except: pass
        try: c.disconnect()
        except: pass

@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")

@app.get("/api/status")
def status():
    def work(c):
        s = c.status()
        song = c.currentsong()
        return {
            "state": s.get("state", "stop"),
            "volume": int(s.get("volume", 0)) if s.get("volume","").lstrip("-").isdigit() else 0,
            "elapsed": float(s.get("elapsed", 0) or 0),
            "duration": float(s.get("duration", 0) or 0),
            "song": song
        }
    return jsonify(mpd_call(work))

@app.post("/api/control/<action>")
def control(action):
    allowed = {"play","pause","stop","next","previous"}
    if action not in allowed:
        return jsonify(error="Unknown action"), 400
    def work(c):
        if action == "pause":
            c.pause(1 if c.status().get("state") == "play" else 0)
        else:
            getattr(c, action)()
        return True
    mpd_call(work)
    return jsonify(ok=True)

@app.post("/api/volume")
def volume():
    v = max(0, min(100, int(request.json.get("volume", 50))))
    mpd_call(lambda c: c.setvol(v))
    return jsonify(ok=True, volume=v)

@app.get("/api/queue")
def queue():
    return jsonify(mpd_call(lambda c: c.playlistinfo()))

@app.delete("/api/queue")
def clear_queue():
    mpd_call(lambda c: c.clear())
    return jsonify(ok=True)

@app.get("/api/library")
def library():
    q = request.args.get("q", "").strip().lower()
    def work(c):
        songs = c.listallinfo()
        out = []
        for x in songs:
            if x.get("file"):
                hay = " ".join(str(x.get(k,"")) for k in ("title","artist","album","file")).lower()
                if not q or q in hay:
                    out.append(x)
        return out[:2000]
    return jsonify(mpd_call(work))

@app.post("/api/queue/add")
def add():
    uri = request.json.get("file")
    if not uri:
        return jsonify(error="file required"), 400
    mpd_call(lambda c: c.add(uri))
    return jsonify(ok=True)

@app.post("/api/play/file")
def play_file():
    uri = request.json.get("file")
    if not uri:
        return jsonify(error="file required"), 400
    def work(c):
        c.clear()
        c.add(uri)
        c.play()
    mpd_call(work)
    return jsonify(ok=True)

@app.post("/api/update")
def update():
    mpd_call(lambda c: c.update())
    return jsonify(ok=True)

@app.get("/api/audio-devices")
def audio_devices():
    try:
        p = subprocess.run(["aplay","-l"], capture_output=True, text=True, timeout=5)
        txt = p.stdout + p.stderr
    except Exception as e:
        return jsonify(error=str(e), devices=[])
    devices = []
    rx = re.compile(r"card\s+(\d+):\s*([^\[]+)\[([^\]]+)\],\s*device\s+(\d+):\s*([^\[]+)\[([^\]]+)\]")
    for line in txt.splitlines():
        m = rx.search(line)
        if m:
            devices.append({
                "card": int(m.group(1)), "card_id": m.group(2).strip(),
                "card_name": m.group(3).strip(), "device": int(m.group(4)),
                "device_id": m.group(5).strip(), "device_name": m.group(6).strip(),
                "alsa": f"hw:{m.group(1)},{m.group(4)}"
            })
    return jsonify(devices=devices, raw=txt)


@app.get("/api/system")
def system_info():
    def read(path, default=""):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return default
    return jsonify({
        "hostname": read("/etc/hostname", "potatoaudio"),
        "version": read("/etc/potato-audio-version", "1.0.0"),
        "model": read("/proc/device-tree/model", "Libre Computer Le Potato").replace("\x00",""),
    })

@app.get("/api/health")
def health():
    try:
        v = mpd_call(lambda c: c.mpd_version)
        return jsonify(ok=True, mpd=v)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
