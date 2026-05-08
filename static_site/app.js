const state = { data: null };

function fmtTime(iso){ if(!iso) return '-'; return new Date(iso).toLocaleString(); }
function setClock(){ document.getElementById('clock').textContent = new Date().toLocaleString(); }
setInterval(setClock,1000); setClock();

const API_URL = window.WEATHERDASH_API_URL || '/api/dashboard';

async function loadDashboard(){
  try{
    const res = await fetch(API_URL);
    state.data = await res.json();
    render();
  }catch(e){ console.error(e); }
}

function render(){
  const d=state.data; if(!d) return;
  const obs=d.observations?.properties||{};
  const tempC=obs.temperature?.value; const tempF=tempC==null?'-':(tempC*9/5+32).toFixed(1);
  const wind=obs.windSpeed?.value? (obs.windSpeed.value*2.23694).toFixed(1):'-';
  document.getElementById('summary').innerHTML=`<strong>${tempF}°F</strong> · Wind ${wind} mph`;
  document.getElementById('current').innerHTML=`<p>${obs.textDescription||'N/A'}</p>`;

  const hourly=(d.hourly?.properties?.periods||[]).slice(0,12).map(p=>`<div class='hour'><b>${p.startTime.slice(11,16)}</b><div>${p.temperature}°${p.temperatureUnit}</div><div>${p.shortForecast}</div><div>💧${p.probabilityOfPrecipitation?.value||0}%</div></div>`).join('');
  document.getElementById('hourly').innerHTML=hourly;

  const daily=(d.forecast?.properties?.periods||[]).slice(0,7).map(p=>`<div class='day'><b>${p.name}</b><div>${p.temperature}°${p.temperatureUnit}</div><div>${p.shortForecast}</div></div>`).join('');
  document.getElementById('daily').innerHTML=daily;

  const alerts=d.alerts?.features||[];
  document.getElementById('alerts').innerHTML=`<h3>Severe Alerts (${alerts.length})</h3>`+alerts.map(a=>`<article><b>${a.properties.event}</b><div>${a.properties.severity}</div><small>${fmtTime(a.properties.onset)} - ${fmtTime(a.properties.ends)}</small></article>`).join('');
  const banner=document.getElementById('alertBanner');
  if(alerts.length){banner.classList.remove('hidden');banner.textContent=`⚠ ${alerts[0].properties.headline}`;} else {banner.classList.add('hidden');}

  const aqi=(d.air_quality||[]).find(x=>x.ParameterName==='PM2.5')||d.air_quality?.[0];
  document.getElementById('aqi').innerHTML=`<h3>AQI</h3><div>${aqi?`${aqi.AQI} (${aqi.Category?.Name||''})`:'No API key/data'}</div>`;
  document.getElementById('wind').innerHTML=`<h3>Wind</h3><div>${wind} mph</div>`;
  document.getElementById('sun').innerHTML=`<h3>Sunrise/Sunset</h3><div>From NWS day/night periods in forecast.</div>`;

  const series=d.river_levels?.value?.timeSeries||[];
  document.getElementById('river').innerHTML='<h3>River Levels</h3>'+series.map(s=>`<div>${s.sourceInfo.siteName}: ${s.values?.[0]?.value?.[0]?.value||'-'} ${s.variable.unit?.unitCode||''}</div>`).join('');

  const tides=d.tides?.predictions||[];
  document.getElementById('tides').innerHTML='<h3>Tides (Olympia)</h3>'+tides.map(t=>`<div>${t.t} ${t.type} ${t.v}ft</div>`).join('');

  const cams=d.traffic_cams||[];
  document.getElementById('camsGrid').innerHTML=cams.map(c=>`<div class='cam'><div>${c.Title}</div><img src='${c.ImageUrl}' referrerpolicy='no-referrer'></div>`).join('');

  const health=Object.entries(d.health||{}).map(([k,v])=>`<div><span class='health-pill ${v.status}'>${k}: ${v.status}</span> <small>${v.last_success?fmtTime(v.last_success):v.error||''}</small></div>`).join('');
  document.getElementById('health').innerHTML='<h3>Data Health</h3>'+health;
}

loadDashboard();
setInterval(loadDashboard,60000);
setInterval(()=>{const f=document.getElementById('radarFrame'); if(f) f.src=f.src;},300000);
