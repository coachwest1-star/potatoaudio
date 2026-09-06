window.hubSettings={
  weather_location:'Cookeville, TN',
  weather_lat:36.1628,
  weather_lon:-85.5016,
  quote:'Whatever the mind can conceive and believe, it can achieve.',
  quote_enabled:true,
  slideshow_seconds:10,
  calendar_events:3,
  photos_enabled:true,
  calendar_enabled:true,
  radio_enabled:true
};

const $ = s => document.querySelector(s);

const fmt = s => {
  s=Math.max(0,Math.floor(Number(s)||0));
  return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`;
};

function updateClock(){
  const d=new Date();

  $("#clock").textContent=d.toLocaleTimeString([],{
    hour:"numeric",
    minute:"2-digit"
  });

  $("#date").textContent=d.toLocaleDateString([],{
    weekday:"long",
    month:"long",
    day:"numeric",
    year:"numeric"
  }).toUpperCase();
}

function weatherIcon(code){

  if(code===0) return "☀️";

  if([1,2].includes(code)) return "🌤️";

  if(code===3) return "☁️";

  if([45,48].includes(code)) return "🌫️";

  if(code>=51 && code<=67) return "🌧️";

  if(code>=71 && code<=77) return "❄️";

  if(code>=80 && code<=82) return "🌦️";

  if(code>=95) return "⛈️";

  return "🌤️";
}

function weatherText(code){

  if(code===0) return "Clear";

  if(code===1) return "Mostly Clear";

  if(code===2) return "Partly Cloudy";

  if(code===3) return "Cloudy";

  if([45,48].includes(code)) return "Fog";

  if(code>=51 && code<=67) return "Rain";

  if(code>=71 && code<=77) return "Snow";

  if(code>=80 && code<=82) return "Rain Showers";

  if(code>=95) return "Thunderstorms";

  return "Current Conditions";
}

async function loadWeather(){

  try{

    // Cookeville, Tennessee
    const lat=Number(window.hubSettings.weather_lat)||36.1628;
    const lon=Number(window.hubSettings.weather_lon)||-85.5016;

    const url=
      `https://api.open-meteo.com/v1/forecast`+
      `?latitude=${lat}`+
      `&longitude=${lon}`+
      `&current=temperature_2m,weather_code`+
      `&daily=weather_code,temperature_2m_max,temperature_2m_min`+
      `&temperature_unit=fahrenheit`+
      `&timezone=auto`;

    const r=await fetch(url);

    const w=await r.json();

    const temp=Math.round(w.current.temperature_2m);

    const icon=weatherIcon(w.current.weather_code);

    $("#temp").textContent=temp+"°";
    $("#bigTemp").textContent=temp+"°";

    $("#weatherIcon").textContent=icon;
    $("#bigWeatherIcon").textContent=icon;

    $("#weatherDescription").textContent=
      weatherText(w.current.weather_code);

    let html="";

    for(let i=0;i<Math.min(4,w.daily.time.length);i++){

      const d=new Date(w.daily.time[i]+"T12:00:00");

      const day=d.toLocaleDateString([],{
        weekday:"short"
      });

      html+=`
        <div class="forecast-day">
          <strong>${day}</strong>
          <div>${weatherIcon(w.daily.weather_code[i])}</div>
          <span>
            ${Math.round(w.daily.temperature_2m_max[i])}°
            /
            ${Math.round(w.daily.temperature_2m_min[i])}°
          </span>
        </div>
      `;
    }

    $("#forecast").innerHTML=html;

  }catch(e){

    $("#weatherDescription").textContent=
      "Weather temporarily unavailable";

  }

}

async function loadAudio(){

  try{

    const r=await fetch("/api/status");

    const s=await r.json();

    const x=s.song||{};

    const isRadio=(x.file||"").startsWith("http");

    $("#playMode").textContent=
      isRadio
      ? "LIVE RADIO"
      : s.state==="play"
      ? "NOW PLAYING"
      : "POTATO AUDIO";

    $("#playTitle").textContent=
      x.title||
      x.name||
      x.file?.split("/").pop()||
      "Potato Audio";

    $("#playArtist").textContent=
      x.artist||
      x.name||
      (isRadio ? "Internet Radio" : "Ready");

    const q=[];

    if(s.audio)
      q.push(s.audio.replace(/:/g," • "));

    if(s.bitrate)
      q.push(s.bitrate+" kbps");

    $("#playMeta").textContent=q.join(" • ");

    $("#elapsed").textContent=fmt(s.elapsed);

    $("#duration").textContent=
      s.duration
      ? fmt(s.duration)
      : isRadio
      ? "LIVE"
      : "0:00";

    $("#playProgress").style.width=
      s.duration
      ? Math.min(100,s.elapsed/s.duration*100)+"%"
      : "0%";

  }catch(e){

    $("#playMode").textContent="POTATO AUDIO";
    $("#playTitle").textContent="Connecting…";

  }

}

updateClock();

loadWeather();

loadAudio();

setInterval(updateClock,1000);

setInterval(loadAudio,1500);

setInterval(loadWeather,10*60*1000);

async function loadCalendar(){
  try{
    const r = await fetch('/api/calendar');
    const events = await r.json();

    if(!Array.isArray(events)){
      throw new Error('Calendar unavailable');
    }

    if(events.length === 0){
      $('#news').innerHTML =
        '<div class="news-item">No upcoming events.</div>';
      return;
    }

    $('#news').innerHTML = events.slice(0,Number(window.hubSettings.calendar_events)||3).map(e => {
      let label = '';

      if(e.allDay){
        const d = new Date(e.start + 'T12:00:00');
        label = d.toLocaleDateString([], {
          weekday:'short',
          month:'short',
          day:'numeric'
        });
      }else{
        const d = new Date(e.start);

        const date = d.toLocaleDateString([], {
          weekday:'short'
        });

        const time = d.toLocaleTimeString([], {
          hour:'numeric',
          minute:'2-digit'
        });

        label = `${date} ${time}`;
      }

      return `
        <div class="news-item">
          <strong>${label}</strong><br>
          ${e.summary}
        </div>
      `;
    }).join('');

  }catch(e){
    $('#news').innerHTML =
      '<div class="news-item">Calendar temporarily unavailable.</div>';
  }
}

loadCalendar();
setInterval(loadCalendar, 5*60*1000);

let smartHubPhotos = [];
let photoOrder = [];
let photoIndex = 0;
let frontPhoto = 'A';
let photoTimerStarted = false;

async function loadPhotoList(){
  try{
    const r = await fetch('/api/photos/status');
    const status = await r.json();

    const count = Number(status.cached)||0;

    smartHubPhotos = Array.from(
      {length:count},
      (_,i)=>`/photos/photo-${String(i+1).padStart(3,'0')}.jpg?v=${Date.now()}`
    );

    photoOrder = [...smartHubPhotos];

    for(let i=photoOrder.length-1;i>0;i--){
      const j=Math.floor(Math.random()*(i+1));
      [photoOrder[i],photoOrder[j]]=[photoOrder[j],photoOrder[i]];
    }

    photoIndex=0;

    if(photoOrder.length){
      showNextPhoto();

      if(!photoTimerStarted){
        photoTimerStarted=true;
        schedulePhoto();
      }
    }else{
      const a=document.querySelector('#photoA');
      const b=document.querySelector('#photoB');
      if(a) a.removeAttribute('src');
      if(b) b.removeAttribute('src');
    }

  }catch(e){
    console.log('Photo list unavailable',e);
  }
}


function preloadPhoto(src){
  const img=new Image();
  img.src=src;
}

function showNextPhoto(){

  if(!photoOrder.length) return;

  const currentImg =
    frontPhoto==='A'
      ? document.querySelector('#photoA')
      : document.querySelector('#photoB');

  const nextImg =
    frontPhoto==='A'
      ? document.querySelector('#photoB')
      : document.querySelector('#photoA');

  const currentBg =
    frontPhoto==='A'
      ? document.querySelector('#bgA')
      : document.querySelector('#bgB');

  const nextBg =
    frontPhoto==='A'
      ? document.querySelector('#bgB')
      : document.querySelector('#bgA');

  const src=photoOrder[photoIndex];

  nextImg.src=src;
  nextBg.style.backgroundImage=`url("${src}")`;

  nextImg.onload=()=>{

    nextBg.classList.add('active');
    currentBg.classList.remove('active');

    nextImg.classList.add('active');
    currentImg.classList.remove('active');

    frontPhoto=frontPhoto==='A'?'B':'A';

    document.querySelector('#photoCaption').textContent =
      `Photo ${photoIndex+1} of ${photoOrder.length}`;

    photoIndex++;

    if(photoIndex>=photoOrder.length){
      photoIndex=0;

      for(let i=photoOrder.length-1;i>0;i--){
        const j=Math.floor(Math.random()*(i+1));
        [photoOrder[i],photoOrder[j]]=[photoOrder[j],photoOrder[i]];
      }
    }

    preloadPhoto(photoOrder[photoIndex]);
  };
}

function schedulePhoto(){
  const seconds=
    Number(window.hubSettings.slideshow_seconds)||10;

  setTimeout(()=>{
    if(
      window.hubSettings.photos_enabled!==false &&
      photoOrder.length
    ){
      showNextPhoto();
    }

    schedulePhoto();

  },seconds*1000);
}


async function loadSmartHubSettings(){

  try{

    const r=await fetch('/api/hub-settings');

    window.hubSettings=await r.json();

    const quote=document.querySelector('.inspiration-quote');

    if(quote){
      quote.textContent=
        `“${window.hubSettings.quote||''}”`;

      quote.style.display=
        window.hubSettings.quote_enabled===false
        ? 'none'
        : '';
    }

    const location=document.querySelector('#weatherLocation');

    if(location){
      location.textContent=
        window.hubSettings.weather_location||
        'Cookeville, TN';
    }

    const photos=document.querySelector('.photo-panel');

    if(photos){
      photos.style.display=
        window.hubSettings.photos_enabled===false
        ? 'none'
        : '';
    }

    const calendar=document.querySelector('.news-panel');

    if(calendar){
      calendar.style.display=
        window.hubSettings.calendar_enabled===false
        ? 'none'
        : '';
    }

    const radio=document.querySelector('.playing-panel');

    if(radio){
      radio.style.display=
        window.hubSettings.radio_enabled===false
        ? 'none'
        : '';
    }

    loadWeather();
    loadCalendar();

  }catch(e){
    console.log('Hub settings unavailable',e);
  }
}

loadSmartHubSettings();


loadPhotoList();
