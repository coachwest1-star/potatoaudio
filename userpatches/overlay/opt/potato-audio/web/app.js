let state={state:"stop"};
const $=s=>document.querySelector(s);
const fmt=s=>{s=Math.max(0,Math.floor(Number(s)||0));return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`};
async function api(url,opt={}){let r=await fetch(url,{headers:{"Content-Type":"application/json"},...opt});if(!r.ok)throw new Error(await r.text());return r.json()}
async function refresh(){
  try{
    state=await api("/api/status");
    $("#connection").textContent="● Connected";
    let x=state.song||{};
    $("#title").textContent=x.title||x.file?.split("/").pop()||"Nothing playing";
    $("#artist").textContent=x.artist||x.album||"Potato Audio";
    $("#play").textContent=state.state==="play"?"❚❚":"▶";
    $("#vol").value=state.volume;
    $("#elapsed").textContent=fmt(state.elapsed);
    $("#duration").textContent=fmt(state.duration);
    $("#progress").style.width=(state.duration?Math.min(100,state.elapsed/state.duration*100):0)+"%";
  }catch(e){$("#connection").textContent="● MPD unavailable"}
}
async function ctl(a){await api("/api/control/"+a,{method:"POST"});setTimeout(refresh,100)}
async function togglePlay(){await ctl(state.state==="play"?"pause":"play")}
$("#vol").addEventListener("change",e=>api("/api/volume",{method:"POST",body:JSON.stringify({volume:+e.target.value})}));
document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>{document.querySelectorAll(".nav").forEach(x=>x.classList.remove("active"));b.classList.add("active");document.querySelectorAll(".view").forEach(x=>x.classList.add("hidden"));$("#"+b.dataset.view).classList.remove("hidden");if(b.dataset.view==="library")loadLibrary();if(b.dataset.view==="queue")loadQueue();if(b.dataset.view==="settings")loadDevices()});
function row(x,queue=false){let title=x.title||x.file?.split("/").pop()||"Unknown";let artist=x.artist||"Unknown artist";return `<div class="row"><div><div class="song">${esc(title)}</div><div class="sub">${esc(artist)}</div></div><div class="album">${esc(x.album||"")}</div>${queue?"<div></div>":`<div class="actions"><button onclick='playFile(${JSON.stringify(x.file)})'>▶</button><button onclick='addFile(${JSON.stringify(x.file)})'>＋</button></div>`}</div>`}
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
async function loadLibrary(q=""){let d=await api("/api/library?q="+encodeURIComponent(q));$("#libraryList").innerHTML=d.map(x=>row(x)).join("")||"<p class=muted>No music found. Put music in /var/lib/mpd/music and click Rescan.</p>"}
async function loadQueue(){let d=await api("/api/queue");$("#queueList").innerHTML=d.map(x=>row(x,true)).join("")||"<p class=muted>Queue is empty.</p>"}
async function playFile(f){await api("/api/play/file",{method:"POST",body:JSON.stringify({file:f})});document.querySelector('[data-view="now"]').click()}
async function addFile(f){await api("/api/queue/add",{method:"POST",body:JSON.stringify({file:f})})}
async function clearQueue(){await api("/api/queue",{method:"DELETE"});loadQueue()}
async function scan(){await api("/api/update",{method:"POST"});setTimeout(()=>loadLibrary($("#search").value),1200)}
async function loadDevices(){let d=await api("/api/audio-devices");$("#devices").innerHTML=d.devices.map(x=>`<div class=card><div class=device>${esc(x.card_name)} — ${esc(x.device_name)}</div><div class=muted>${esc(x.alsa)}</div></div>`).join("")||`<pre>${esc(d.raw||"No ALSA devices found")}</pre>`}
let t;$("#search").addEventListener("input",e=>{clearTimeout(t);t=setTimeout(()=>loadLibrary(e.target.value),250)});
refresh();setInterval(refresh,1500);
