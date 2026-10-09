const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
}[c]));
const today = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
$("journeyDate").value = today();
$("availabilityDate").value = today();

function debounce(fn, wait = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}
function stationCode(station) {
  return String(station?.code ?? station?.stationCode ?? station?.station_code ?? station?.id ?? "").toUpperCase();
}
function stationName(station) {
  return String(station?.name ?? station?.stationName ?? station?.station_name ?? station?.label ?? stationCode(station));
}
function trainNumber(train) {
  return String(train?.number ?? train?.trainNumber ?? train?.train_number ?? train?.no ?? "");
}
function trainName(train) {
  return String(train?.name ?? train?.trainName ?? train?.train_name ?? "Train");
}
function showError(target, message) {
  target.innerHTML = '<p class="error">' + esc(message) + '</p>';
}
async function api(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  let data;
  try { data = await response.json(); }
  catch { throw new Error("The server returned an unreadable response. Please retry."); }
  if (!response.ok) throw new Error(data.message || data.error || "Request failed (HTTP " + response.status + ").");
  return data;
}
function wireStationAutocomplete(inputId, codeId, suggestionsId) {
  const input = $(inputId), code = $(codeId), box = $(suggestionsId);
  input.addEventListener("input", debounce(async () => {
    code.value = "";
    const query = input.value.trim();
    if (query.length < 2) { box.innerHTML = ""; return; }
    box.innerHTML = '<div class="suggestion">Searching stations…</div>';
    try {
      const data = await api("/api/stations?q=" + encodeURIComponent(query));
      const stations = Array.isArray(data.stations) ? data.stations : [];
      box.innerHTML = stations.map((s, i) =>
        '<button type="button" class="suggestion" data-index="' + i + '"><b>' +
        esc(stationName(s)) + '</b><span>' + esc(stationCode(s)) +
        (s.city ? " · " + esc(s.city) : "") + '</span></button>'
      ).join("") || '<div class="suggestion">No matching stations found.</div>';
      box.querySelectorAll("button[data-index]").forEach((button) => {
        button.addEventListener("click", () => {
          const s = stations[Number(button.dataset.index)];
          input.value = stationName(s);
          code.value = stationCode(s);
          box.innerHTML = "";
        });
      });
    } catch (error) { showError(box, error.message); }
  }, 300));
  input.addEventListener("change", () => {
    if (!code.value) input.dataset.unselected = "true";
  });
}
wireStationAutocomplete("source", "sourceCode", "sourceSuggestions");
wireStationAutocomplete("destination", "destinationCode", "destinationSuggestions");

$("trainSearch").addEventListener("input", debounce(async () => {
  const query = $("trainSearch").value.trim(), box = $("trainSuggestions");
  if (query.length < 2) { box.innerHTML = ""; return; }
  box.innerHTML = '<div class="suggestion">Searching trains…</div>';
  try {
    const data = await api("/api/train-search?q=" + encodeURIComponent(query));
    const trains = Array.isArray(data.trains) ? data.trains : [];
    box.innerHTML = trains.map((t, i) =>
      '<button type="button" class="suggestion" data-index="' + i + '"><b>' +
      esc(trainNumber(t) + " — " + trainName(t)) + '</b><span>' +
      esc(t.source ?? t.from ?? "") + " → " + esc(t.destination ?? t.to ?? "") +
      '</span></button>'
    ).join("") || '<div class="suggestion">No matching trains found.</div>';
    box.querySelectorAll("button[data-index]").forEach((button) => {
      button.addEventListener("click", () => {
        const t = trains[Number(button.dataset.index)], n = trainNumber(t);
        $("trainSearch").value = n + " — " + trainName(t);
        $("statusTrain").value = n;
        $("availabilityTrain").value = n;
        box.innerHTML = "";
      });
    });
  } catch (error) { showError(box, error.message); }
}, 300));

async function findTrains() {
  const source = $("sourceCode").value.trim().toUpperCase();
  const destination = $("destinationCode").value.trim().toUpperCase();
  const box = $("trains");
  if (!source || !destination) {
    showError(box, "Choose both stations from the autocomplete suggestions so their station codes are valid.");
    return;
  }
  if (source === destination) { showError(box, "Choose two different stations."); return; }
  box.innerHTML = '<p>Searching trains…</p>';
  try {
    const data = await api("/api/trains?" + new URLSearchParams({
      source, destination, date: $("journeyDate").value
    }));
    const trains = Array.isArray(data.trains) ? data.trains : [];
    box.innerHTML = trains.map((t, i) => {
      const train = t.train ?? t;
      const from = t.from ?? train.from ?? {};
      const to = t.to ?? train.to ?? {};
      const n = trainNumber(train), name = trainName(train);
      return '<article class="train"><b>' + esc(n + " — " + name) +
        '</b><div>' + esc(from.departure ?? from.departureTime ?? "") + " → " +
        esc(to.arrival ?? to.arrivalTime ?? "") + '</div><button type="button" data-index="' +
        i + '">Use this train</button></article>';
    }).join("") || '<p>No trains found for this route/date.</p>';
    box.querySelectorAll("button[data-index]").forEach((button) => {
      button.addEventListener("click", () => {
        const t = trains[Number(button.dataset.index)];
        const train = t.train ?? t;
        selectTrain(trainNumber(train), source, destination);
      });
    });
  } catch (error) { showError(box, error.message); }
}
function selectTrain(number, source, destination) {
  $("availabilityTrain").value = number;
  $("availabilityFrom").value = source;
  $("availabilityTo").value = destination;
  $("statusTrain").value = number;
}
async function status() {
  const number = $("statusTrain").value.trim(), box = $("status");
  if (!number) { showError(box, "Enter a train number first."); return; }
  box.innerHTML = "<p>Loading live running status…</p>";
  try {
    const data = await api("/api/status/" + encodeURIComponent(number));
    box.innerHTML = '<pre>' + esc(JSON.stringify(data.status, null, 2)) + '</pre>';
  } catch (error) { showError(box, error.message); }
}
async function checkAvailability() {
  const number = $("availabilityTrain").value.trim();
  const source = $("availabilityFrom").value.trim().toUpperCase();
  const destination = $("availabilityTo").value.trim().toUpperCase();
  const journeyDate = $("availabilityDate").value;
  const box = $("availability");
  if (!number || !source || !destination || !journeyDate) {
    showError(box, "Fill in train number, source, destination, and journey date.");
    return;
  }
  box.innerHTML = "<p>Checking seat availability…</p>";
  const query = new URLSearchParams({
    train: number, source, destination, journeyDate,
    classCode: $("classCode").value, quotaCode: $("quotaCode").value
  });
  try {
    const data = await api("/api/availability?" + query);
    box.innerHTML = '<pre>' + esc(JSON.stringify(data.availability, null, 2)) + '</pre>';
  } catch (error) { showError(box, error.message); }
}
window.findTrains = findTrains;
window.status = status;
window.checkAvailability = checkAvailability;
