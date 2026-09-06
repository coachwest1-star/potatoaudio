let state={state:'stop'};const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])),fmt=s=>{s=Math.max(0,Math.floor(+s||0));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`};async function api(u,o={}){let r=await fetch(u,{headers:{'Content-Type':'application/json'},...o}),d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||'Request failed');return d}async function refresh(){try{state=await api('/api/status');let x=state.song||{},radio=(x.file||'').startsWith('http');$('#connection').textContent='● Connected';$('#title').textContent=x.title||x.name||x.file?.split('/').pop()||'Nothing playing';$('#artist').textContent=x.artist||x.name||(radio?'Internet Radio':'Potato Audio');$('#play').textContent=state.state==='play'?'❚❚':'▶';$('#vol').value=state.volume;$('#elapsed').textContent=fmt(state.elapsed);$('#duration').textContent=state.duration?fmt(state.duration):(radio?'LIVE':'0:00');$('#progress').style.width=(state.duration?Math.min(100,state.elapsed/state.duration*100):0)+'%';$('#nowMeta').textContent=[state.audio?state.audio.replace(/:/g,' • '):'',state.bitrate?state.bitrate+' kbps':''].filter(Boolean).join(' • ')}catch(e){$('#connection').textContent='● MPD unavailable'}}async function ctl(a){await api('/api/control/'+a,{method:'POST'});refresh()}async function togglePlay(){ctl(state.state==='play'?'pause':'play')}$('#vol').onchange=e=>api('/api/volume',{method:'POST',body:JSON.stringify({volume:+e.target.value})});document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>{document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));$('#'+b.dataset.view).classList.remove('hidden');if(b.dataset.view==='library')loadLibrary();if(b.dataset.view==='queue')loadQueue();if(b.dataset.view==='radio'){loadRadio();loadPopularRadio();}if(b.dataset.view==='settings')loadDevices();if(b.dataset.view==='hubsettings'){loadHubSettings();loadPhotoStatus()}if(b.dataset.view==='server'){loadServerStatus()}});function row(x,q=false){return `<div class="row"><div><div class="song">${esc(x.title||x.file?.split('/').pop()||'Unknown')}</div><div class="sub">${esc(x.artist||'Unknown artist')}</div></div><div class="album">${esc(x.album||'')}</div>${q?'<div></div>':`<div class="actions"><button onclick='playFile(${JSON.stringify(x.file)})'>▶</button><button onclick='addFile(${JSON.stringify(x.file)})'>＋</button></div>`}</div>`}async function loadLibrary(q=''){let d=await api('/api/library?q='+encodeURIComponent(q));$('#libraryList').innerHTML=d.map(x=>row(x)).join('')||'<p class=muted>No music found.</p>'}async function loadQueue(){let d=await api('/api/queue');$('#queueList').innerHTML=d.map(x=>row(x,true)).join('')||'<p class=muted>Queue empty.</p>'}async function playFile(f){await api('/api/play/file',{method:'POST',body:JSON.stringify({file:f})});document.querySelector('[data-view="now"]').click()}async function addFile(f){api('/api/queue/add',{method:'POST',body:JSON.stringify({file:f})})}async function clearQueue(){await api('/api/queue',{method:'DELETE'});loadQueue()}async function scan(){await api('/api/update',{method:'POST'});setTimeout(loadLibrary,1000)}async function loadRadio(){
  let d=await api('/api/radio');

  if(!d.length){
    $('#radioList').innerHTML='<p class="muted">No stations saved yet.</p>';
    return;
  }

  d.sort((a,b)=>{
    const ca=(a.category||'Other').toLowerCase();
    const cb=(b.category||'Other').toLowerCase();

    if(ca!==cb) return ca.localeCompare(cb);

    return (a.name||'').localeCompare(b.name||'');
  });

  const groups={};

  d.forEach(s=>{
    const cat=s.category||'Other';
    if(!groups[cat]) groups[cat]=[];
    groups[cat].push(s);
  });

  $('#radioList').innerHTML=Object.entries(groups).map(([category,stations])=>`
    <div class="radio-category">
      <div class="radio-category-title">${esc(category)}</div>

      <div class="radio-category-grid">
        ${stations.map(s=>`
          <div class="radio-card">

            <div class="radio-card-top">
              ${
                s.logo
                ? `<img class="station-logo" src="${esc(s.logo)}" alt="" onerror="this.style.display='none'">`
                : `<div class="station-logo station-placeholder">📻</div>`
              }

              <div class="station-info">
                <div class="station-name">${esc(s.name)}</div>
                <div class="station-category">${esc(s.category||'Internet Radio')}</div>
              </div>
            </div>

            <div class="station-actions">
              <button class="primary" onclick="playStation(${s.id})">▶ Play</button>
              <button onclick="editStation(${s.id})">Edit</button>
              <button class="danger" onclick="deleteStation(${s.id})">Delete</button>
            </div>

          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}function showAddStation(){$('#stationForm').classList.remove('hidden')}function cancelStation(){$('#stationForm').classList.add('hidden')}async function saveStation(){
  try{
    await api('/api/radio',{
      method:'POST',
      body:JSON.stringify({
        name:$('#stationName').value,
        url:$('#stationUrl').value,
        logo:$('#stationLogo').value,
        category:$('#stationCategory').value
      })
    });

    $('#stationName').value='';
    $('#stationUrl').value='';
    $('#stationLogo').value='';
    $('#stationCategory').value='';

    cancelStation();
    loadRadio();

  }catch(e){
    alert(e.message);
  }
}async function playStation(i){await api(`/api/radio/${i}/play`,{method:'POST'});document.querySelector('[data-view="now"]').click()}async function deleteStation(i){
  const stations = await api('/api/radio');
  const station = stations.find(s => Number(s.id) === Number(i));
  const name = station ? station.name : 'this station';

  if(!confirm(`Delete "${name}" from your radio presets?`)) return;

  try{
    await api(`/api/radio/${i}`,{
      method:'DELETE'
    });

    loadRadio();

  }catch(e){
    alert(e.message);
  }
}async function loadDevices(){let d=await api('/api/audio-devices'),a=[{alsa:'default',kind:'Automatic',card_name:'System default',device_name:'ALSA default'},...d.devices];$('#devices').innerHTML=a.map(x=>`<div class="card"><b>${esc(x.kind)} — ${esc(x.card_name)}</b><div class="muted">${esc(x.device_name)} • ${esc(x.alsa)}</div><br><button onclick="testOutput('${x.alsa}')">Test</button> <button class="primary" onclick="selectOutput('${x.alsa}')">${d.selected===x.alsa?'Selected':'Use Output'}</button></div>`).join('')}async function selectOutput(d){try{await api('/api/audio-output',{method:'POST',body:JSON.stringify({device:d})});loadDevices()}catch(e){alert(e.message)}}async function testOutput(d){try{await api('/api/audio-test',{method:'POST',body:JSON.stringify({device:d})})}catch(e){alert(e.message)}}let t;$('#search').oninput=e=>{clearTimeout(t);t=setTimeout(()=>loadLibrary(e.target.value),250)};refresh();setInterval(refresh,1500);

let editingStationId = null;

async function editStation(i){
  try{
    const stations = await api('/api/radio');
    const station = stations.find(s => Number(s.id) === Number(i));

    if(!station){
      alert('Station not found.');
      return;
    }

    editingStationId = i;

    $('#stationName').value = station.name || '';
    $('#stationCategory').value = station.category || '';
    $('#stationUrl').value = station.url || '';
    $('#stationLogo').value = station.logo || '';

    $('#stationForm').classList.remove('hidden');

    const btn = $('#stationSaveBtn');
    if(btn) btn.textContent = 'Update Station';

    $('#stationName').focus();

  }catch(e){
    alert(e.message);
  }
}

async function saveStationV2(){
  try{
    const payload = {
      name: $('#stationName').value,
      url: $('#stationUrl').value,
      logo: $('#stationLogo').value,
      category: $('#stationCategory').value
    };

    if(editingStationId !== null){
      await api(`/api/radio/${editingStationId}`,{
        method:'PUT',
        body:JSON.stringify(payload)
      });
    }else{
      await api('/api/radio',{
        method:'POST',
        body:JSON.stringify(payload)
      });
    }

    editingStationId = null;

    $('#stationName').value='';
    $('#stationUrl').value='';
    $('#stationLogo').value='';
    $('#stationCategory').value='';

    const btn = $('#stationSaveBtn');
    if(btn) btn.textContent='Save Station';

    $('#stationForm').classList.add('hidden');

    loadRadio();

  }catch(e){
    alert(e.message);
  }
}

saveStation = saveStationV2;

async function loadHubSettings(){
  try{
    const s=await api('/api/hub-settings');

    $('#hubWeather').value=s.weather_location||'';
    $('#hubQuote').value=s.quote||'';

    $('#hubSlideSeconds').value=
      s.slideshow_seconds||10;

    $('#hubCalendarEvents').value=
      s.calendar_events||3;

    $('#hubQuoteEnabled').checked=
      s.quote_enabled!==false;

    $('#hubPhotosEnabled').checked=
      s.photos_enabled!==false;

    $('#hubCalendarEnabled').checked=
      s.calendar_enabled!==false;

    $('#hubRadioEnabled').checked=
      s.radio_enabled!==false;

  }catch(e){
    alert('Unable to load Smart Hub settings: '+e.message);
  }
}

async function saveHubSettings(){
  try{

    const payload={
      weather_location:$('#hubWeather').value,

      quote:$('#hubQuote').value,

      slideshow_seconds:
        Number($('#hubSlideSeconds').value)||10,

      calendar_events:
        Number($('#hubCalendarEvents').value)||3,

      quote_enabled:
        $('#hubQuoteEnabled').checked,

      photos_enabled:
        $('#hubPhotosEnabled').checked,

      calendar_enabled:
        $('#hubCalendarEnabled').checked,

      radio_enabled:
        $('#hubRadioEnabled').checked
    };

    const result=await api('/api/hub-settings',{
      method:'POST',
      body:JSON.stringify(payload)
    });

    $('#hubWeather').value=
      result.weather_location||payload.weather_location;

    alert('Smart Hub settings saved.');

  }catch(e){
    alert(e.message);
  }
}


let photoPickerTimer=null;

async function loadPhotoStatus(){
  try{
    const s=await api('/api/photos/status');

    $('#photoStatus').textContent =
      `${s.cached} photos cached • ${s.selected} photos selected`;

  }catch(e){
    $('#photoStatus').textContent =
      'Unable to read Google Photos status';
  }
}


async function selectGooglePhotos(){

  // Open immediately so browser popup blocking
  // does not interfere after the API request.
  const pickerWindow=window.open(
    'about:blank',
    '_blank'
  );

  try{

    $('#photoStatus').textContent =
      'Starting Google Photos Picker…';

    const session=await api(
      '/api/photos/picker/start',
      {method:'POST'}
    );

    if(!session.pickerUri || !session.id){
      throw new Error(
        'Google did not return a Picker session.'
      );
    }

    pickerWindow.location=session.pickerUri;

    $('#photoStatus').textContent =
      'Select your photos in the Google Photos window…';

    if(photoPickerTimer){
      clearInterval(photoPickerTimer);
    }

    photoPickerTimer=setInterval(async()=>{

      try{

        const status=await api(
          `/api/photos/picker/status/${session.id}`
        );

        if(status.complete){

          clearInterval(photoPickerTimer);
          photoPickerTimer=null;

          $('#photoStatus').textContent =
            `${status.count} photos selected • ready to download`;

          alert(
            `${status.count} Google Photos selected.\n\n`+
            `Now click "Refresh / Download Selected Photos".`
          );

        }

      }catch(e){
        console.log(
          'Photo Picker status:',
          e.message
        );
      }

    },3000);

  }catch(e){

    if(pickerWindow){
      pickerWindow.close();
    }

    $('#photoStatus').textContent =
      'Google Photos Picker failed';

    alert(e.message);
  }
}


async function downloadGooglePhotos(){

  if(!confirm(
    'Replace the Smart Hub photo cache with your current Google Photos selection?'
  )){
    return;
  }

  try{

    $('#photoStatus').textContent =
      'Downloading photos to Smart Hub…';

    const result=await api(
      '/api/photos/download',
      {method:'POST'}
    );

    $('#photoStatus').textContent =
      `${result.count} photos cached • ready for slideshow`;

    alert(
      `${result.count} Google Photos downloaded successfully.`
    );

  }catch(e){

    $('#photoStatus').textContent =
      'Photo download failed';

    alert(e.message);
  }
}


function bytesFmt(n){
  n=Number(n)||0;
  if(n>=1024**3) return (n/1024**3).toFixed(1)+' GB';
  if(n>=1024**2) return (n/1024**2).toFixed(1)+' MB';
  if(n>=1024) return (n/1024).toFixed(1)+' KB';
  return n+' B';
}

function uptimeFmt(sec){
  sec=Math.floor(Number(sec)||0);
  const d=Math.floor(sec/86400);
  const h=Math.floor((sec%86400)/3600);
  const m=Math.floor((sec%3600)/60);
  return [
    d ? d+'d' : '',
    h ? h+'h' : '',
    m+'m'
  ].filter(Boolean).join(' ');
}

function serviceText(ok){
  return ok ? '● Running' : '● Offline';
}

async function loadServerStatus(){
  try{
    const s=await api('/api/server/status');

    $('#serverDriveStatus').textContent=
      s.mounted ? `${s.label||'Music Drive'} Connected` : 'Music Drive Not Mounted';

    $('#serverDrivePath').textContent=s.path||'';

    $('#serverUsed').textContent=bytesFmt(s.used);
    $('#serverFree').textContent=bytesFmt(s.free);
    $('#serverTotal').textContent=bytesFmt(s.total);
    $('#serverSongs').textContent=s.songs??0;

    const pct=s.total ? Math.min(100,(s.used/s.total)*100) : 0;
    $('#serverStorageBar').style.width=pct+'%';

    $('#serverMpd').textContent=serviceText(s.mpd);
    $('#serverSamba').textContent=serviceText(s.samba);
    $('#serverScanner').textContent=serviceText(s.scanner);

    $('#serverIp').textContent=s.ip||'Unavailable';
    $('#serverSmb').textContent=
      s.ip ? `smb://${s.ip}/Music` : 'Unavailable';

    $('#serverUptime').textContent=uptimeFmt(s.uptime);

  }catch(e){
    $('#serverDriveStatus').textContent='Unable to load server status';
  }
}

async function serverScan(){
  const el=$('#serverScanStatus');

  try{
    el.textContent='Scanning music library…';

    await api('/api/server/scan',{
      method:'POST'
    });

    el.textContent='Scan started successfully.';

    setTimeout(()=>{
      loadServerStatus();
      el.textContent='Library updated.';
    },3000);

  }catch(e){
    el.textContent='Scan failed: '+e.message;
  }
}

function directoryStationCard(s){
  const meta=[
    s.country||'',
    s.codec||'',
    s.bitrate ? s.bitrate+' kbps' : '',
    s.tags ? s.tags.split(',').slice(0,3).join(' • ') : ''
  ].filter(Boolean).join(' • ');

  const logo=s.favicon
    ? `<img class="directory-logo" src="${esc(s.favicon)}" alt="" onerror="this.style.display='none'">`
    : `<div class="directory-logo directory-placeholder">📻</div>`;

  return `
    <div class="directory-card">
      <div class="directory-card-top">
        ${logo}

        <div class="directory-info">
          <div class="station-name">${esc(s.name||'Unknown Station')}</div>
          <div class="muted">${esc(meta)}</div>
        </div>
      </div>

      <div class="directory-actions">
        <button class="primary"
          onclick='playDirectoryStation(${JSON.stringify(s)})'>
          ▶ Play
        </button>

        <button
          onclick='favoriteDirectoryStation(${JSON.stringify(s)})'>
          ★ Save
        </button>
      </div>
    </div>
  `;
}

async function loadPopularRadio(){
  const status=$('#radioDirectoryStatus');
  const results=$('#radioDirectoryResults');

  status.textContent='Loading popular stations…';
  results.innerHTML='';

  try{
    const d=await api('/api/radio-directory/popular');

    results.innerHTML=d.map(directoryStationCard).join('') ||
      '<p class="muted">No stations found.</p>';

    status.textContent=`${d.length} popular stations`;

  }catch(e){
    status.textContent='Unable to load radio directory: '+e.message;
  }
}

async function loadRadioTag(tag){
  const status=$('#radioDirectoryStatus');
  const results=$('#radioDirectoryResults');

  status.textContent=`Loading ${tag} stations…`;
  results.innerHTML='';

  try{
    const d=await api(
      '/api/radio-directory/search?tag='+encodeURIComponent(tag)
    );

    results.innerHTML=d.map(directoryStationCard).join('') ||
      '<p class="muted">No stations found.</p>';

    status.textContent=`${d.length} stations • ${tag}`;

  }catch(e){
    status.textContent='Unable to load stations: '+e.message;
  }
}

async function searchRadioDirectory(){
  const q=$('#radioDirectorySearch').value.trim();
  const status=$('#radioDirectoryStatus');
  const results=$('#radioDirectoryResults');

  if(!q){
    loadPopularRadio();
    return;
  }

  status.textContent='Searching…';
  results.innerHTML='';

  try{
    const d=await api(
      '/api/radio-directory/search?q='+encodeURIComponent(q)
    );

    results.innerHTML=d.map(directoryStationCard).join('') ||
      '<p class="muted">No stations found.</p>';

    status.textContent=`${d.length} results for "${q}"`;

  }catch(e){
    status.textContent='Search failed: '+e.message;
  }
}

async function playDirectoryStation(s){
  try{
    await api('/api/radio-directory/play',{
      method:'POST',
      body:JSON.stringify({
        uuid:s.uuid,
        url:s.url
      })
    });

    document.querySelector('[data-view="now"]').click();

  }catch(e){
    alert(e.message);
  }
}

async function favoriteDirectoryStation(s){
  try{
    const result=await api('/api/radio-directory/favorite',{
      method:'POST',
      body:JSON.stringify(s)
    });

    if(result.already){
      alert('This station is already saved.');
    }else{
      alert(`${s.name} added to My Stations.`);
    }

    loadRadio();

  }catch(e){
    alert(e.message);
  }
}

const radioDirectorySearch=$('#radioDirectorySearch');

if(radioDirectorySearch){
  radioDirectorySearch.addEventListener('keydown',e=>{
    if(e.key==='Enter') searchRadioDirectory();
  });
}
