async function findTrains(){
 const s=document.querySelector("#source").value.trim(),d=document.querySelector("#destination").value.trim(),box=document.querySelector("#trains");
 box.innerHTML="Searching...";
 const r=await fetch(`/api/trains?source=${encodeURIComponent(s)}&destination=${encodeURIComponent(d)}`),data=await r.json();
 if(!r.ok)return box.innerHTML=`<p class="error">${data.error}</p>`;
 box.innerHTML=data.trains.length?data.trains.map(t=>`<div class="train"><b>${t.number}</b> — ${t.name}<br>${t.source} → ${t.destination}</div>`).join(""):"<p>No trains in demo data.</p>";
}
async function checkVacancy(){
 const t=document.querySelector("#train").value.trim(),s=document.querySelector("#vfrom").value.trim().toUpperCase(),d=document.querySelector("#vto").value.trim().toUpperCase(),box=document.querySelector("#vacancy");
 box.innerHTML="Checking...";
 const r=await fetch(`/api/vacancy?train=${encodeURIComponent(t)}&source=${encodeURIComponent(s)}&destination=${encodeURIComponent(d)}`),data=await r.json();
 if(!r.ok)return box.innerHTML=`<p class="error">${data.error}</p>`;
 box.innerHTML=`<p><b>${data.train.number} ${data.train.name}</b> · ${s} → ${d}</p>`+
 (data.vacant_berths.length?`<div class="seats">${data.vacant_berths.map(x=>`<span>${x.coach}-${x.berth}</span>`).join("")}</div>`:"<p>No demo vacant berths found.</p>")+
 `<small>Mode: ${data.data_mode}</small>`;
}
async function status(){
 const n=document.querySelector("#statusTrain").value.trim(),box=document.querySelector("#status");
 const r=await fetch(`/api/status/${encodeURIComponent(n)}`);box.textContent=JSON.stringify(await r.json(),null,2);
}
findTrains();checkVacancy();