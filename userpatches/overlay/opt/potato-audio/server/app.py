#!/usr/bin/env python3
from flask import Flask,jsonify,request,send_from_directory
from mpd import MPDClient
import os,subprocess,re,json,tempfile,urllib.request,urllib.parse
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); WEB=os.path.join(BASE,'web'); DATA='/var/lib/potato-audio'; RADIO=f'{DATA}/radio.json'; OUTPUT=f'{DATA}/audio-output.json'; HUB=f'{DATA}/hub-settings.json'

HUB_DEFAULTS={
    'weather_location':'Cookeville, TN',
    'weather_lat':36.1628,
    'weather_lon':-85.5016,
    'quote':'Whatever the mind can conceive and believe, it can achieve.',
    'quote_enabled':True,
    'slideshow_seconds':10,
    'calendar_events':3,
    'photos_enabled':True,
    'calendar_enabled':True,
    'radio_enabled':True
}
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

def radio_browser_request(path,params=None):
    params=params or {}
    query=urllib.parse.urlencode(params)

    url='https://de1.api.radio-browser.info'+path
    if query:
        url+='?'+query

    req=urllib.request.Request(
        url,
        headers={
            'User-Agent':'PotatoAudio/2.1',
            'Accept':'application/json'
        }
    )

    with urllib.request.urlopen(req,timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))


def clean_directory_station(x):
    return {
        'uuid':x.get('stationuuid',''),
        'name':x.get('name','').strip(),
        'url':x.get('url_resolved') or x.get('url',''),
        'homepage':x.get('homepage',''),
        'favicon':x.get('favicon',''),
        'country':x.get('country',''),
        'countrycode':x.get('countrycode',''),
        'state':x.get('state',''),
        'language':x.get('language',''),
        'tags':x.get('tags',''),
        'codec':x.get('codec',''),
        'bitrate':x.get('bitrate',0),
        'votes':x.get('votes',0),
        'clickcount':x.get('clickcount',0)
    }


@app.get('/api/radio-directory/search')
def radio_directory_search():
    q=request.args.get('q','').strip()
    tag=request.args.get('tag','').strip()
    country=request.args.get('country','').strip()

    params={
        'limit':40,
        'hidebroken':'true',
        'order':'votes',
        'reverse':'true'
    }

    if q:
        params['name']=q

    if tag:
        params['tag']=tag

    if country:
        params['country']=country

    try:
        rows=radio_browser_request(
            '/json/stations/search',
            params
        )

        stations=[
            clean_directory_station(x)
            for x in rows
            if (x.get('url_resolved') or x.get('url'))
        ]

        return jsonify(stations)

    except Exception as e:
        return jsonify(error=str(e)),500


@app.get('/api/radio-directory/popular')
def radio_directory_popular():
    try:
        rows=radio_browser_request(
            '/json/stations/search',
            {
                'limit':40,
                'hidebroken':'true',
                'order':'votes',
                'reverse':'true'
            }
        )

        return jsonify([
            clean_directory_station(x)
            for x in rows
            if (x.get('url_resolved') or x.get('url'))
        ])

    except Exception as e:
        return jsonify(error=str(e)),500


@app.post('/api/radio-directory/play')
def radio_directory_play():
    b=request.get_json(silent=True) or {}

    url=str(b.get('url','')).strip()
    uuid=str(b.get('uuid','')).strip()

    if not re.match(r'^https?://',url,re.I):
        return jsonify(error='Invalid stream URL'),400

    try:
        def f(c):
            c.clear()
            c.add(url)
            c.play()

        call(f)

        if uuid:
            try:
                radio_browser_request(
                    f'/json/url/{urllib.parse.quote(uuid)}'
                )
            except:
                pass

        return jsonify(ok=True)

    except Exception as e:
        return jsonify(error=str(e)),500


@app.post('/api/radio-directory/favorite')
def radio_directory_favorite():
    b=request.get_json(silent=True) or {}

    name=str(b.get('name','')).strip()
    url=str(b.get('url','')).strip()

    if not name or not re.match(r'^https?://',url,re.I):
        return jsonify(error='Station name and URL required'),400

    stations=rj(RADIO,[])

    if any(
        str(x.get('url','')).strip()==url
        for x in stations
    ):
        return jsonify(ok=True,already=True)

    station={
        'id':max([int(x.get('id',0)) for x in stations]+[0])+1,
        'name':name,
        'url':url,
        'logo':str(b.get('favicon','')).strip(),
        'category':str(b.get('tags','')).split(',')[0].strip() or 'Internet Radio'
    }

    stations.append(station)
    wj(RADIO,stations)

    return jsonify(ok=True,station=station),201


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

def get_hub_settings():
    cfg=HUB_DEFAULTS.copy()
    cfg.update(rj(HUB,{}))
    return cfg

@app.get('/api/hub-settings')
def hubsettings():
    return jsonify(get_hub_settings())

@app.post('/api/hub-settings')
def save_hub_settings():
    b=request.get_json(silent=True) or {}
    cfg=get_hub_settings()

    old_location=cfg.get('weather_location','')
    location=str(b.get('weather_location',old_location)).strip()

    if location:
        cfg['weather_location']=location

    cfg['quote']=str(
        b.get('quote',cfg.get('quote',''))
    ).strip()

    cfg['quote_enabled']=bool(
        b.get('quote_enabled',cfg.get('quote_enabled',True))
    )

    cfg['photos_enabled']=bool(
        b.get('photos_enabled',cfg.get('photos_enabled',True))
    )

    cfg['calendar_enabled']=bool(
        b.get('calendar_enabled',cfg.get('calendar_enabled',True))
    )

    cfg['radio_enabled']=bool(
        b.get('radio_enabled',cfg.get('radio_enabled',True))
    )

    try:
        cfg['slideshow_seconds']=max(
            5,min(120,int(b.get(
                'slideshow_seconds',
                cfg.get('slideshow_seconds',10)
            )))
        )
    except:
        cfg['slideshow_seconds']=10

    try:
        cfg['calendar_events']=max(
            1,min(6,int(b.get(
                'calendar_events',
                cfg.get('calendar_events',3)
            )))
        )
    except:
        cfg['calendar_events']=3

    # Automatically geocode a changed weather location.
    if location and location != old_location:
        try:
            q=urllib.parse.quote(location)

            url=(
                'https://geocoding-api.open-meteo.com/v1/search'
                f'?name={q}&count=1&language=en&format=json'
            )

            with urllib.request.urlopen(url,timeout=10) as r:
                result=json.loads(r.read().decode('utf-8'))

            matches=result.get('results') or []

            if matches:
                place=matches[0]

                cfg['weather_lat']=place['latitude']
                cfg['weather_lon']=place['longitude']

                name=place.get('name',location)
                region=place.get('admin1','')

                cfg['weather_location']=(
                    f'{name}, {region}' if region else name
                )

        except Exception as e:
            print('Weather geocode warning:',e)

    wj(HUB,cfg)

    return jsonify(cfg)



def photos_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token=f'{DATA}/google-photos-token.json'

    scopes=[
        'https://www.googleapis.com/auth/photospicker.mediaitems.readonly'
    ]

    creds=Credentials.from_authorized_user_file(token,scopes)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

        with open(token,'w') as f:
            f.write(creds.to_json())

    return creds


def photos_request(url,method='GET',payload=None):
    creds=photos_credentials()

    headers={
        'Authorization':f'Bearer {creds.token}',
        'Content-Type':'application/json'
    }

    data=None

    if payload is not None:
        data=json.dumps(payload).encode('utf-8')

    req=urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method
    )

    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


@app.post('/api/photos/picker/start')
def photos_picker_start():
    try:
        session=photos_request(
            'https://photospicker.googleapis.com/v1/sessions',
            method='POST',
            payload={}
        )

        return jsonify(
            ok=True,
            id=session.get('id'),
            pickerUri=session.get('pickerUri')
        )

    except Exception as e:
        return jsonify(error=str(e)),500


@app.get('/api/photos/picker/status/<sid>')
def photos_picker_status(sid):
    try:
        session=photos_request(
            f'https://photospicker.googleapis.com/v1/sessions/{sid}'
        )

        complete=bool(session.get('mediaItemsSet'))

        if not complete:
            return jsonify(
                ok=True,
                complete=False
            )

        all_items=[]
        page_token=None

        while True:
            params={
                'sessionId':sid,
                'pageSize':'100'
            }

            if page_token:
                params['pageToken']=page_token

            query=urllib.parse.urlencode(params)

            result=photos_request(
                'https://photospicker.googleapis.com/v1/mediaItems?'+query
            )

            all_items.extend(
                result.get('mediaItems',[])
            )

            page_token=result.get('nextPageToken')

            if not page_token:
                break

        selected={
            'mediaItems':all_items
        }

        wj(
            f'{DATA}/google-selected-photos.json',
            selected
        )

        return jsonify(
            ok=True,
            complete=True,
            count=len(all_items)
        )

    except Exception as e:
        return jsonify(error=str(e)),500


@app.post('/api/photos/download')
def photos_download():
    try:
        selected=f'{DATA}/google-selected-photos.json'
        photos=f'{DATA}/photos'

        if not os.path.exists(selected):
            return jsonify(
                error='No Google Photos selection found.'
            ),400

        os.makedirs(photos,exist_ok=True)

        # Remove old cached slideshow files so stale
        # photos do not remain after a smaller selection.
        for name in os.listdir(photos):
            if name.startswith('photo-'):
                try:
                    os.remove(os.path.join(photos,name))
                except:
                    pass

        script=os.path.join(
            BASE,
            'download_google_photos.py'
        )

        p=subprocess.run(
            [
                os.path.join(BASE,'.venv','bin','python'),
                script
            ],
            capture_output=True,
            text=True,
            timeout=600
        )

        if p.returncode:
            return jsonify(
                error=(p.stderr or p.stdout).strip()
            ),500

        count=len([
            x for x in os.listdir(photos)
            if x.startswith('photo-')
        ])

        return jsonify(
            ok=True,
            count=count,
            message=f'{count} photos downloaded'
        )

    except subprocess.TimeoutExpired:
        return jsonify(
            error='Photo download took too long.'
        ),500

    except Exception as e:
        return jsonify(error=str(e)),500


@app.get('/api/photos/status')
def photos_status():
    try:
        photos=f'{DATA}/photos'

        count=0

        if os.path.isdir(photos):
            count=len([
                x for x in os.listdir(photos)
                if x.startswith('photo-')
            ])

        selected=rj(
            f'{DATA}/google-selected-photos.json',
            {}
        )

        selected_count=len(
            selected.get('mediaItems',[])
        )

        return jsonify(
            ok=True,
            cached=count,
            selected=selected_count
        )

    except Exception as e:
        return jsonify(error=str(e)),500



@app.get('/api/server/status')
def server_status():
    music='/mnt/musicusb'

    mounted=os.path.ismount(music)

    total=used=free=0
    if mounted:
        st=os.statvfs(music)
        total=st.f_blocks*st.f_frsize
        free=st.f_bavail*st.f_frsize
        used=total-free

    try:
        songs=call(lambda c: int(c.stats().get('songs',0)))
    except:
        songs=0

    def service_active(name):
        try:
            p=subprocess.run(
                ['systemctl','is-active',name],
                capture_output=True,
                text=True,
                timeout=3
            )
            return p.stdout.strip()=='active'
        except:
            return False

    try:
        uptime_seconds=float(
            open('/proc/uptime').read().split()[0]
        )
    except:
        uptime_seconds=0

    try:
        ip=subprocess.run(
            ['hostname','-I'],
            capture_output=True,
            text=True,
            timeout=3
        ).stdout.strip().split()[0]
    except:
        ip=''

    return jsonify(
        mounted=mounted,
        label='POTATOMUSIC',
        path=music,
        total=total,
        used=used,
        free=free,
        songs=songs,
        samba=service_active('smbd'),
        scanner=service_active('potato-music-watch'),
        mpd=service_active('mpd'),
        ip=ip,
        uptime=uptime_seconds
    )


@app.post('/api/server/scan')
def server_scan():
    try:
        job=call(lambda c:c.update())
        return jsonify(ok=True,job=job)
    except Exception as e:
        return jsonify(error=str(e)),500


@app.get('/api/health')
def health():
 try:return jsonify(ok=True,mpd=call(lambda c:c.mpd_version),version='2.0.0')
 except Exception as e:return jsonify(ok=False,error=str(e)),503
if __name__=='__main__':app.run(host='0.0.0.0',port=8080)



@app.get('/api/calendar')
def calendar_events():
    try:
        from datetime import datetime, timezone
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        creds = Credentials.from_authorized_user_file(
            '/var/lib/potato-audio/google-token.json',
            scopes
        )

        service = build('calendar', 'v3', credentials=creds)

        now = datetime.now(timezone.utc).isoformat()

        items = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=8,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])

        out = []
        for e in items:
            start = e.get('start', {})
            out.append({
                'id': e.get('id'),
                'summary': e.get('summary', '(No title)'),
                'start': start.get('dateTime') or start.get('date'),
                'allDay': 'date' in start
            })

        return jsonify(out)

    except Exception as e:
        return jsonify(error=str(e)), 500

@app.put('/api/radio/<int:i>')
def editradio(i):
    b=request.get_json(silent=True) or {}

    name=str(b.get('name','')).strip()
    url=str(b.get('url','')).strip()

    if not name or not re.match(r'^https?://',url,re.I):
        return jsonify(error='Station name and direct http/https stream URL required'),400

    stations=rj(RADIO,[])

    for s in stations:
        if int(s.get('id',-1)) == i:
            s['name']=name
            s['url']=url
            s['logo']=str(b.get('logo','')).strip()
            s['category']=str(b.get('category','')).strip()

            wj(RADIO,stations)
            return jsonify(s)

    return jsonify(error='Station not found'),404
