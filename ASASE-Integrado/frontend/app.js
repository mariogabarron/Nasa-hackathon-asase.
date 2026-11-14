"use strict";
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const t = (es, en) => (language === "en" ? en : es);
const iso = (d) =>
  new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10);
const ago = new Date();
ago.setDate(ago.getDate() - 30);
const yesterday = new Date();
yesterday.setDate(yesterday.getDate() - 1);
const future = new Date();
future.setFullYear(future.getFullYear() + 1);
future.setDate(future.getDate() - 1);
const initialRange = [iso(ago), iso(yesterday)];
let storageWarning = false;
function readStore(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}
function writeStore(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    storageWarning = true;
    return false;
  }
}
const storedParcels = readStore("asase.parcels.v3", []);
let parcels = storedParcels;
const validPoint = (p) =>
  Array.isArray(p) &&
  p.length === 2 &&
  p.every(Number.isFinite) &&
  Math.abs(p[0]) <= 90 &&
  Math.abs(p[1]) <= 180;
const validBox = (b) =>
  Array.isArray(b) &&
  b.length === 4 &&
  validPoint(b.slice(0, 2)) &&
  validPoint(b.slice(2)) &&
  b[0] < b[2] &&
  b[1] < b[3];
parcels = Array.isArray(parcels)
  ? parcels
      .filter(
        (p) =>
          p &&
          typeof p.id === "string" &&
          typeof p.name === "string" &&
          ((validPoint(p.point) && p.bbox == null) ||
            (validBox(p.bbox) && p.point == null)) &&
          Array.isArray(p.history) &&
          p.history.length <= 100 &&
          p.history.every((x) => Number.isInteger(x) && x > 0),
      )
      .map(({ cropId, ...parcel }) => parcel)
  : [];
// Migration in place: preserve location/history; never infer a planted crop.
if (
  Array.isArray(storedParcels) &&
  storedParcels.some((p) => p && Object.hasOwn(p, "cropId"))
)
  writeStore("asase.parcels.v3", parcels);
const tomorrow = () => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return iso(d);
};
const futureRange = () => {
  const start = tomorrow();
  const d = new Date(start + "T12:00:00");
  d.setFullYear(d.getFullYear() + 1);
  d.setDate(d.getDate() - 1);
  return [start, iso(d)];
};
const state = {
  user: null,
  view: "overview",
  catalog: [],
  catalogError: "",
  cropId: null,
  point: null,
  pointHistory: [],
  budgets: structuredClone(ECON_REFERENCES),
  range: [...initialRange],
  recRange: futureRange(),
  parcelRecRange: futureRange(),
  searches: {},
  historyCropId: null,
  parcelRange: [...initialRange],
  result: null,
  error: "",
  busy: false,
  menu: false,
  selectedParcel: null,
  draft: null,
  selection: "point",
  firstCorner: null,
  geoBusy: false,
};
let map = null,
  marker = null,
  rectangle = null,
  request = null,
  requestId = 0,
  geoId = 0;
const navItems = [
  ["overview", "map", "Mapa", "Map"],
  ["recommendations", "sprout", "Recomendaciones", "Recommendations"],
  ["parcels", "fields", "Parcelas", "Plots"],
  ["sources", "info", "Fuentes", "Sources"],
];
const cropName = (id) =>
  state.catalog.find((c) => c.id === +id)?.nombre || `#${id}`;
const cropLabel = (id) => translateString(cropName(id));
const activeParcel = () => parcels.find((p) => p.id === state.selectedParcel);
const ranges = (
  action = state.view === "recommendations" ? "rotaciones" : "iac",
) =>
  action === "rotaciones"
    ? state.view === "parcels"
      ? state.parcelRecRange
      : state.recRange
    : state.view === "parcels"
      ? state.parcelRange
      : state.range;
const coordText = (p) => p.map((v) => truncated(v, 5)).join(", ");
const placeText = (p) =>
  p.bbox ? `BBOX · ${coordText(p.bbox)}` : coordText(p.point);
const normalizeSearch = (value) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase(language);
const orderedCrops = (query = "") =>
  [...state.catalog]
    .filter((c) =>
      normalizeSearch(cropLabel(c.id)).includes(normalizeSearch(query.trim())),
    )
    .sort((a, b) =>
      cropLabel(a.id).localeCompare(cropLabel(b.id), language, {
        sensitivity: "base",
      }),
    );
function options(value = state.cropId, query = "") {
  const crops = orderedCrops(query),
    selected = crops.some((c) => c.id === value);
  return (
    `${selected ? "" : `<option value="">${crops.length ? t("Selecciona un cultivo", "Select a crop") : t("Sin resultados", "No matches")}</option>`}` +
    crops
      .map(
        (c) =>
          `<option value="${c.id}" ${c.id === value ? "selected" : ""}>${esc(cropLabel(c.id))}</option>`,
      )
      .join("")
  );
}
function cropPicker(id, label, value, extraClass = "") {
  return `<div class="field ${extraClass}"><label for="${id}">${label}</label>
 <input type="search" id="${id}-search" data-search-for="${id}" value="${esc(state.searches[id] || "")}" placeholder="${t("Buscar cultivo…", "Search crops…")}" aria-label="${t("Buscar cultivo", "Search crops")}" aria-controls="${id}">
 <select id="${id}" ${!state.catalog.length ? "disabled" : ""}>${options(value, state.searches[id] || "")}</select></div>`;
}
function recommendationDateError() {
  const [start, end] = ranges("rotaciones"),
    min = tomorrow();
  if (!start || !end)
    return t(
      "Completa las dos fechas para las recomendaciones.",
      "Enter both recommendation dates.",
    );
  if (start < min || end < min)
    return t(
      "Las recomendaciones requieren fechas futuras: desde mañana. Modifica las fechas.",
      "Recommendations require future dates, starting tomorrow. Please change the dates.",
    );
  if (start > end)
    return t(
      "La fecha final debe ser igual o posterior a la inicial.",
      "The end date must be on or after the start date.",
    );
  return "";
}
function validateRecommendationDates() {
  const el = $("#recommendation-date-error");
  if (!el) return;
  const error = recommendationDateError();
  el.textContent = error;
  const prefix = state.view === "parcels" ? "rec-" : "";
  for (const id of ["start-date", "end-date"]) {
    const input = $("#" + prefix + id);
    if (input) {
      input.min = tomorrow();
      input.setAttribute("aria-invalid", String(!!error));
    }
  }
}
function iacClass(value) {
  return typeof value !== "number" || !Number.isFinite(value)
    ? "iac-none"
    : value < 40
      ? "iac-low"
      : value < 70
        ? "iac-medium"
        : "iac-high";
}
function iacLegend() {
  return `<div class="iac-legend"><span class="iac-low">${t("Bajo", "Low")} &lt;40</span><span class="iac-medium">${t("Medio", "Medium")} 40–&lt;70</span><span class="iac-high">${t("Alto", "High")} ≥70</span></div>`;
}
function recommendationDates(prefix = "") {
  const range = ranges("rotaciones"),
    min = tomorrow();
  return `<div class="recommendation-dates"><label class="field">${t("Desde", "From")}<input id="${prefix}start-date" type="date" required min="${min}" value="${range[0]}" aria-describedby="recommendation-date-error"></label><label class="field">${t("Hasta (incluido)", "To (inclusive)")}<input id="${prefix}end-date" type="date" required min="${min}" value="${range[1]}" aria-describedby="recommendation-date-error"></label></div><p id="recommendation-date-error" class="form-error date-error" role="alert"></p>`;
}
function cancelResult() {
  requestId++;
  request?.abort();
  request = null;
  state.busy = false;
  state.result = null;
  state.error = "";
}
function toast(es, en = es) {
  const el = document.createElement("div");
  el.className = "toast";
  el.setAttribute("role", "status");
  el.textContent = t(es, en);
  document.body.append(el);
  setTimeout(() => el.remove(), 4500);
}
function rangeFields() {
  if (state.view === "recommendations")
    return `<div class="recommendation-filters">${recommendationDates()}<label class="field">${t("Número de propuestas", "Number of proposals")}<select id="rec-count">${[1, 2, 3, 4, 5].map((n) => `<option ${n === (state.recCount || 3) ? "selected" : ""}>${n}</option>`).join("")}</select></label></div><p class="period-note">${t("Fechas de plantación futuras. Propuestas ordenadas por IAC medio descendente, con días cultivados como desempate. Escenarios de 2025, no pronósticos.", "Future planting dates. Proposals ranked by descending mean IAC, with cropped days as a tiebreaker. Scenarios based on 2025, not forecasts.")}</p>`;
  const range = ranges("iac");
  return `<div class="filter-strip"><label class="field filter-field">${t("Histórico IAC · Desde", "Historical IAC · From")}<input id="start-date" type="date" required max="${pastLimit()}" value="${range[0]}"></label><label class="field filter-field">${t("Histórico IAC · Hasta (incluido)", "Historical IAC · To (inclusive)")}<input id="end-date" type="date" required max="${pastLimit()}" value="${range[1]}"></label>${cropPicker("crop", t("Cultivo para analizar", "Crop to analyse"), state.cropId, "filter-field crop-control")}</div><p class="period-note">${t("Consulta del histórico: selecciona fechas pasadas, hasta ayer, y un máximo de 365 días. El cultivo elegido solo se usa para este análisis.", "Historical data: select past dates, up to yesterday, and a maximum of 365 days. The selected crop is only used for this analysis.")}</p>`;
}
function coordinatesForm() {
  if (state.view === "parcels") return "";
  return `<form id="coordinates" class="coords"><label class="field">${t("Latitud", "Latitude")}<input name="lat" type="number" min="-90" max="90" step="any" required value="${state.point ? truncated(state.point[0], 5) : ""}" placeholder="9.4"></label><label class="field">${t("Longitud", "Longitude")}<input name="lon" type="number" min="-180" max="180" step="any" required value="${state.point ? truncated(state.point[1], 5) : ""}" placeholder="-0.84"></label><button class="muted-button" type="submit">${t("Ir al punto", "Go to point")}</button></form>`;
}
function mapCard() {
  const isParcel = state.view === "parcels",
    creating = isParcel && state.draft;
  const instruction = isParcel
    ? creating
      ? t(
          "Pulsa dos esquinas opuestas para delimitar un área dentro de Ghana.",
          "Click two opposite corners to define an area within Ghana.",
        )
      : t(
          "Crea o edita una parcela para delimitar su área.",
          "Create or edit a plot to define its area.",
        )
    : t(
        "Selecciona un punto dentro de Ghana. Puedes explorar todo el mapamundi.",
        "Select a point within Ghana. You can explore the whole world map.",
      );
  return `<section class="card"><div class="card-header"><div><h2 class="card-headline">${t("Explora el territorio", "Explore the land")}</h2><p class="card-sub">${instruction}</p></div><button class="muted-button" id="locate" ${state.geoBusy ? "disabled" : ""}>${t("◎ Mi ubicación", "◎ My location")}</button></div>${creating ? `<div class="map-tools"><button type="button" class="muted-button chosen" data-selection="bbox">${t("Dibujar área rectangular", "Draw rectangular area")}</button><span id="drawing-status" role="status"></span></div>` : ""}<div id="map" aria-label="${t("Mapa interactivo", "Interactive map")}" tabindex="0"></div><p id="map-status" role="status" class="map-status"></p><div class="map-bottom">${coordinatesForm()}${!isParcel ? `<p class="coordinate-readout" id="point-label">${state.point ? coordText(state.point) : t("Todavía no hay un punto seleccionado.", "No point selected yet.")}</p>` : ""}</div></section>`;
}
function resultPanel() {
  if (state.busy)
    return `<div class="loading" role="status"><span class="spinner"></span>${t("Consultando clima, suelo y motor agrícola…", "Querying climate, soil and crop engine…")}<p>${t("La consulta puede tardar varios minutos.", "This can take a few minutes.")}</p><button class="muted-button" id="cancel-query">${t("Cancelar consulta", "Cancel request")}</button></div>`;
  if (state.error)
    return `<div class="error" role="alert">${esc(state.error)}</div>`;
  if (!state.result)
    return `<div class="empty">${t("Selecciona una ubicación y solicita un análisis. Los resultados se obtienen de la API.", "Select a location and request an analysis. Results come from the API.")}</div>`;
  const { data, action, context } = state.result;
  const contextHtml = `<div class="result-context"><strong>${esc(context.name)}</strong><br>${esc(context.location)}<br>${esc(context.start)} → ${esc(context.end)}<br>${t("Historial previo", "Previous history")}: ${context.history.length ? context.history.map(cropLabel).map(esc).join(" → ") : t("Sin historial", "No history")}</div>`;
  if (action === "iac")
    return (
      contextHtml +
      `<div class="iac-result"><span>${esc(cropLabel(context.cropId))}</span><div class="iac-number ${iacClass(data.iac)}">${typeof data.iac === "number" ? truncated(data.iac) : "—"}<small>/100</small></div><h3>${t("Índice de aptitud del cultivo", "Crop suitability index")}</h3><p data-api-text>${esc(data.razon || t("Sin factor limitante señalado por la API.", "No limiting factor reported by the API."))}</p></div>`
    );
  const plans = [...(data.recomendaciones || [data])].sort(
    (a, b) =>
      (b.iac_medio_cultivado ?? -1) - (a.iac_medio_cultivado ?? -1) ||
      b.dias_cultivados - a.dias_cultivados,
  );
  return (
    contextHtml +
    economicsEditor(plans) +
    `<p class="notice">${t("Patrón mensual de 2025 repetido. No es un pronóstico meteorológico.", "Repeated monthly pattern of 2025. This is not a weather forecast.")}</p>${iacLegend()}${data.aviso_recomendaciones ? `<p data-api-text>${esc(data.aviso_recomendaciones)}</p>` : ""}${plans.map((p, i) => `<article class="plan"><h3>${t("Propuesta", "Proposal")} ${i + 1}</h3><div class="plan-metrics"><span><b>${p.dias_cultivados}</b> ${t("días cultivados", "days cropped")}</span><span><b>${truncated(p.porcentaje_ocupacion)}%</b> ${t("ocupación", "occupancy")}</span><span><b class="${iacClass(p.iac_medio_cultivado)}">${truncated(p.iac_medio_cultivado)}</b> IAC</span></div>${economicPanel(p, context)}<ol class="rotation">${(p.rotacion || []).map((r) => `<li><strong>${r.cultivo_id ? esc(cropLabel(r.cultivo_id)) : t("Barbecho / preparación", "Fallow / preparation")}</strong><span>${esc(r.fecha_inicio)} → ${esc(r.fecha_fin)} · ${r.dias} ${t("días", "days")}</span>${r.iac_estimado != null ? `<b class="${iacClass(r.iac_estimado)}">IAC ${truncated(r.iac_estimado)}</b>` : ""}<p data-api-text>${esc(r.justificacion || r.razon || "")}</p></li>`).join("")}</ol><p class="period-note">${t("El final de cada tramo es exclusivo.", "The end date of each segment is exclusive.")}</p><details><summary>${t("Justificación y supuestos", "Rationale and assumptions")}</summary><p data-api-text>${esc(p.justificacion)}</p><ul data-api-text>${(p.supuestos || []).map((s) => `<li>${esc(s)}</li>`).join("")}</ul></details></article>`).join("")}`
  );
}
function analysisCard() {
  const isRec = state.view === "recommendations",
    p = state.view === "parcels" ? activeParcel() : null;
  const enabled =
    state.catalog.length &&
    (state.view === "parcels"
      ? p?.bbox && boxInGhana(p.bbox)
      : state.point && inGhana(state.point)) &&
    !state.draft;
  const recButton = `<button class="primary-button" data-analyse="rotaciones" ${!enabled || state.busy || recommendationDateError() ? "disabled" : ""}>${t("Obtener recomendaciones", "Get recommendations")}</button>`;
  return `<aside class="card analysis"><div class="eyebrow">${t("ANÁLISIS DEL TERRITORIO", "LAND ANALYSIS")}</div><h2>${p ? esc(p.name) : isRec ? t("Qué cultivar aquí", "What to grow here") : t("Conoce su aptitud", "Understand its suitability")}</h2><p class="analysis-description">${isRec ? t("Consulta las secuencias de cultivos que propone el motor para este punto.", "Request crop sequences proposed by the engine for this point.") : t("Evalúa el cultivo seleccionado con el clima y el suelo de esta ubicación.", "Evaluate the selected crop using the climate and soil at this location.")}</p>
 ${state.view !== "parcels" ? `<details class="point-history" open><summary>${t("Historial de cultivos de este punto", "Crop history for this point")}</summary>${historyEditor({ history: state.pointHistory })}</details>` : p && !p.bbox ? `<p class="notice">${t("Edita esta parcela antigua y delimita un área para poder analizarla. Su historial se conserva.", "Edit this legacy plot and define an area before analysing it. Its history is preserved.")}</p>` : ""}
 ${!isRec ? `<section class="iac-actions"><button class="primary-button" data-analyse="iac" ${!enabled || state.busy || !state.cropId || historicalDateError() ? "disabled" : ""}>${t("Obtener IAC", "Get IAC")} ${I("arrow")}</button>${iacLegend()}<p id="historical-date-error" class="form-error" role="alert">${historicalDateError()}</p></section>` : `<div class="analysis-actions">${recButton}</div>`}
 ${p ? `<section class="parcel-recommendations"><h3>${t("Recomendaciones de cultivos", "Crop recommendations")}</h3>${recButton}${recommendationDates("rec-")}<p class="period-note">${t("Rango propio de plantación, desde mañana. Mayor IAC medio primero. Escenario basado en 2025, no un pronóstico.", "Separate planting range, starting tomorrow. Highest mean IAC first. Scenario based on 2025, not a forecast.")}</p></section>` : ""}<div id="results" aria-live="polite">${resultPanel()}</div></aside>`;
}
function historyEditor(d) {
  return `${cropPicker("history-crop", t("Cultivo anterior para añadir al historial", "Previous crop to add to history"), state.historyCropId)}<button type="button" id="add-history" class="muted-button">${t("Añadir al historial", "Add to history")}</button><p class="period-note">${t("Del más antiguo al más reciente. No incluyas el cultivo que vas a evaluar.", "Oldest to newest. Do not include the crop you are about to evaluate.")}</p><ol class="history-chips">${d.history.map((id, i) => `<li>${esc(cropLabel(id))}<button type="button" data-remove-history="${i}" aria-label="${t("Quitar", "Remove")}">×</button></li>`).join("")}</ol>`;
}
function parcelEditor() {
  const d = state.draft;
  return `<section class="card parcel-editor"><h2>${d.id ? t("Editar parcela", "Edit plot") : t("Crear parcela", "Create plot")}</h2><p>${t("Delimita un área rectangular dentro de Ghana y asigna un nombre.", "Define a rectangular area within Ghana and give it a name.")}</p><form id="parcel-form"><label class="field">${t("Nombre de la parcela", "Plot name")}<input id="parcel-name" required maxlength="80" value="${esc(d.name)}"></label><div id="draft-location" class="notice">${d.point || d.bbox ? esc(placeText(d)) : t("Selecciona la ubicación en el mapa.", "Select a location on the map.")}</div>${historyEditor(d)}<div class="analysis-actions"><button class="primary-button" type="submit" ${!state.catalog.length ? "disabled" : ""}>${t("Guardar parcela", "Save plot")}</button><button class="muted-button" id="cancel-parcel" type="button">${t("Cancelar", "Cancel")}</button></div><p class="form-error" id="parcel-error" role="alert"></p></form></section>`;
}
function parcelList() {
  return `<div class="parcel-toolbar"><p>${parcels.length} ${t("parcelas guardadas en este navegador", "plots saved in this browser")}</p><button class="primary-button" id="new-parcel" ${state.draft || !state.catalog.length ? "disabled" : ""}>+ ${t("Crear parcela", "Create plot")}</button></div>${parcels.length ? `<div class="parcel-list">${parcels.map((p) => `<button class="parcel-item ${state.selectedParcel === p.id ? "selected" : ""}" data-parcel="${esc(p.id)}" ${state.draft ? "disabled" : ""}><strong>${esc(p.name)}</strong><small>${esc(placeText(p))}</small></button>`).join("")}</div>` : `<div class="empty">${t("Crea tu primera parcela para guardar su ubicación e historial.", "Create your first plot to save its location and history.")}</div>`}${activeParcel() && !state.draft ? `<div class="parcel-tools"><span>${t("Historial previo", "Previous history")}: ${activeParcel().history.map(cropLabel).map(esc).join(" → ") || "—"}</span><button class="muted-button" id="edit-parcel">${t("Editar", "Edit")}</button><button class="muted-button danger" id="delete-parcel">${t("Eliminar", "Delete")}</button></div>` : ""}`;
}
function sources() {
  return `<div class="source-grid">${economicsSources()}<section class="card view-panel"><h2>${t("API y catálogo", "API and catalogue")}</h2><p>${t("Los selectores se cargan de GET /cultivos, generado desde cultivos.json. Los análisis usan POST /predecir, con IDs numéricos y coordenadas [latitud, longitud].", "Selectors load from GET /cultivos, generated from cultivos.json. Analyses use POST /predecir, with numeric IDs and [latitude, longitude] coordinates.")}</p><a href="/docs" target="_blank" rel="noopener">${t("Documentación de la API", "API documentation")} ↗</a></section><section class="card view-panel"><h2>${t("Clima y suelo", "Climate and soil")}</h2><p>NASA POWER · SMAP · SoilGrids · Google Earth Engine.</p><p>${t("Se requieren credenciales de Earth Engine en el servidor. La interfaz informa de los errores de configuración, datos incompletos o fuentes externas.", "Earth Engine credentials are required on the server. The interface reports configuration, incomplete-data and external-source errors.")}</p></section><section class="card view-panel"><h2>${t("Mapa y parcelas", "Map and plots")}</h2><p>Leaflet 1.9.4 · © OpenStreetMap contributors.</p><p>${t("Las parcelas se guardan en este navegador, sin sincronización por cuenta. Las parcelas son áreas rectangulares dentro de Ghana; no son límites catastrales. En áreas, POWER usa el centro y SMAP/SoilGrids promedian la caja.", "Plots are saved in this browser, without account sync. Plots are rectangular areas within Ghana; these are not cadastral boundaries. For areas, POWER uses the centre and SMAP/SoilGrids average the box.")}</p></section><section class="card view-panel"><h2>${t("Alcance del análisis", "Scope of analysis")}</h2><p>${t("El IAC es un índice heurístico, no un rendimiento garantizado. Las recomendaciones repiten el patrón mensual observado en 2025 y usan una búsqueda aproximada. La API responde en el idioma seleccionado (ES/EN). El acceso es de demostración y no autentica usuarios.", "IAC is a heuristic index, not a guaranteed yield. Recommendations repeat the monthly pattern observed in 2025 and use an approximate search. The API responds in the selected language (ES/EN). Access is a demonstration and does not authenticate users.")}</p></section></div>`;
}
function layout() {
  const item = navItems.find((n) => n[0] === state.view);
  return `<div class="app"><aside class="sidebar ${state.menu ? "open" : ""}"><div class="brand"><div class="brand-symbol">${I("fields")}</div><div><div class="brand-name">asase.</div><div class="brand-sub">Agricultural intelligence</div></div></div><div class="sidebar-label">${t("PLATAFORMA", "PLATFORM")}</div><nav class="nav">${navItems.map(([id, ic, es, en]) => `<button class="nav-btn ${state.view === id ? "active" : ""}" data-view="${id}" title="${t(es, en)}" ${state.view === id ? 'aria-current="page"' : ""}>${I(ic)}<span>${t(es, en)}</span></button>`).join("")}</nav><div class="sidebar-spacer"></div><div class="sidebar-foot"><strong>${t("De la tierra a la decisión", "From land to decisions")}</strong><p>${t("Clima, suelo y cultivos en un mismo lugar.", "Climate, soil and crops in one place.")}</p></div></aside><main class="page"><header class="topbar"><div class="crumbs"><button class="icon-btn mobile-menu" id="menu" aria-label="${t("Menú", "Menu")}">${I("menu")}</button>asase. <span>/</span><b>${t(item[2], item[3])}</b></div><div class="top-actions">${languageSwitcher()}<span class="demo">${t("Acceso demo", "Demo access")}</span><button class="icon-btn" data-logout title="${t("Cerrar sesión", "Log out")}">${I("user")}</button></div></header><div class="main"><div class="eyebrow">${t("INTELIGENCIA AGRÍCOLA", "AGRICULTURAL INTELLIGENCE")}</div><div class="heading"><div><h1>${state.view === "overview" ? t("Conocer la tierra. Decidir mejor.", "Know the land. Decide better.") : t(item[2], item[3])}</h1><p>${t("Cada parcela, su cultivo. Cada decisión, un motivo.", "Every plot, its crop. Every decision, a reason.")}</p></div></div>${state.catalogError ? `<div class="error" role="alert">${esc(state.catalogError)} <button id="retry-catalog" class="muted-button">${t("Reintentar", "Retry")}</button></div>` : !state.catalog.length ? `<p role="status">${t("Cargando catálogo…", "Loading catalogue…")}</p>` : ""}${state.view === "sources" ? sources() : `${rangeFields()}${state.view === "parcels" ? parcelList() : ""}<div class="workspace-grid">${mapCard()}${state.draft ? parcelEditor() : analysisCard()}</div>`}${storageWarning ? `<p class="error" role="alert">${t("No se ha podido guardar en el navegador. Los cambios solo están en memoria; no cierres esta página.", "Could not save in the browser. Changes are only in memory; do not close this page.")}</p>` : ""}<footer class="foot">${t("IAC heurístico · No representa rendimiento garantizado.", "Heuristic IAC · Does not represent guaranteed yield.")}</footer></div></main></div>`;
}
function render() {
  if (map) {
    map.remove();
    map = null;
  }
  marker = null;
  rectangle = null;
  $("#app").innerHTML = state.user ? layout() : login();
  if (!state.user) translateUI($("#app"));
  document.documentElement.lang = language;
  attach();
  validateRecommendationDates();
  if (state.user && state.view !== "sources") initMap();
}
function updateResults() {
  const el = $("#results");
  if (el) el.innerHTML = resultPanel();
  document
    .querySelectorAll("[data-analyse]")
    .forEach(
      (b) =>
        (b.disabled =
          state.busy ||
          !state.catalog.length ||
          !(state.view === "parcels"
            ? activeParcel()?.bbox && boxInGhana(activeParcel().bbox)
            : state.point && inGhana(state.point)) ||
          !!state.draft ||
          (b.dataset.analyse === "iac" &&
            (!state.cropId || !!historicalDateError())) ||
          (b.dataset.analyse === "rotaciones" && !!recommendationDateError())),
    );
  attachEconomics();
  const dateError = $("#historical-date-error");
  if (dateError) dateError.textContent = historicalDateError();
  $("#cancel-query")?.addEventListener("click", () => {
    cancelResult();
    updateResults();
  });
}
function setPoint(point, { pan = false } = {}) {
  if (!validPoint(point) || !inGhana(point)) {
    ghanaWarning();
    return;
  }
  if (state.view === "parcels") {
    if (pan) map?.setView(point, Math.max(map.getZoom(), 12));
    return;
  }
  state.point = point;
  cancelResult();
  drawLocation();
  const label = $("#point-label");
  if (label) label.textContent = coordText(point);
  const f = $("#coordinates");
  if (f) {
    f.elements.lat.value = truncated(point[0], 5);
    f.elements.lon.value = truncated(point[1], 5);
  }
  if (pan) map?.setView(point, Math.max(map.getZoom(), 12));
  updateResults();
}
function drawLocation() {
  if (!map) return;
  if (marker) {
    map.removeLayer(marker);
    marker = null;
  }
  if (rectangle) {
    map.removeLayer(rectangle);
    rectangle = null;
  }
  const p = state.draft || (state.view === "parcels" ? activeParcel() : null);
  if (p?.bbox)
    rectangle = L.rectangle(
      [
        [p.bbox[0], p.bbox[1]],
        [p.bbox[2], p.bbox[3]],
      ],
      { color: "#245844", weight: 2 },
    ).addTo(map);
  else if (state.view !== "parcels" && state.point)
    marker = L.circleMarker(p?.point || state.point, {
      radius: 9,
      color: "#fff",
      weight: 3,
      fillColor: "#245844",
      fillOpacity: 1,
    }).addTo(map);
}
function initMap() {
  if (!window.L) {
    $("#map").innerHTML =
      `<div class="empty map-fallback">${t("No se ha podido cargar Leaflet. Revisa tu conexión; puedes introducir las coordenadas debajo.", "Leaflet could not load. Check your connection; you can enter coordinates below.")}</div>`;
    return;
  }
  map = L.map("map", { worldCopyJump: true }).setView(
    state.point || [9.4, -0.84],
    state.point ? 11 : 7,
  );
  L.geoJSON(GHANA_BOUNDARY, {
    interactive: false,
    style: { color: "#245844", weight: 2, fillOpacity: 0.04 },
  }).addTo(map);
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  tiles.on("tileerror", () => {
    const el = $("#map-status");
    if (el)
      el.textContent = t(
        "No se pueden cargar algunas teselas. Revisa tu conexión.",
        "Some map tiles could not load. Check your connection.",
      );
  });
  map.on("click", (e) => {
    const point = [
      e.latlng.lat,
      Math.abs(e.latlng.lng) <= 180 ? e.latlng.lng : e.latlng.wrap().lng,
    ];
    if (state.view === "parcels" && !state.draft) return;
    if (!inGhana(point)) {
      ghanaWarning();
      return;
    }
    if (state.draft) {
      if (!state.firstCorner) {
        state.firstCorner = point;
        state.draft.point = null;
        state.draft.bbox = null;
        drawLocation();
        $("#draft-location").textContent = t(
          "Falta seleccionar la segunda esquina.",
          "Select the second corner.",
        );
        $("#drawing-status").textContent = t(
          "Selecciona la segunda esquina.",
          "Select the second corner.",
        );
        marker = L.circleMarker(point, { radius: 4, interactive: false }).addTo(
          map,
        );
        return;
      }
      const a = state.firstCorner,
        b = point,
        box = [
          Math.min(a[0], b[0]),
          Math.min(a[1], b[1]),
          Math.max(a[0], b[0]),
          Math.max(a[1], b[1]),
        ];
      if (!validBox(box)) {
        toast(
          "El área debe tener ancho y alto.",
          "The area must have width and height.",
        );
        return;
      }
      if (!boxInGhana(box)) {
        ghanaWarning();
        return;
      }
      state.draft.bbox = box;
      state.draft.point = null;
      state.point = [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2];
      state.firstCorner = null;
      cancelResult();
      render();
      return;
    }
    setPoint(point);
  });
  drawLocation();
  const p = state.draft || (state.view === "parcels" ? activeParcel() : null);
  if (p?.bbox)
    map.fitBounds(
      [
        [p.bbox[0], p.bbox[1]],
        [p.bbox[2], p.bbox[3]],
      ],
      { padding: [25, 25], maxZoom: 16 },
    );
}
async function fetchJSON(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new Error(
      t(
        "No se puede conectar con la API. Comprueba que el servidor está iniciado.",
        "Cannot connect to the API. Check that the server is running.",
      ),
    );
  }
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error(
      t(
        "La API no ha devuelto JSON válido.",
        "The API did not return valid JSON.",
      ),
    );
  }
  if (!response.ok) {
    const detail = body.detail;
    const msg = Array.isArray(detail)
      ? detail.map((x) => `${x.loc?.join(".") || ""}: ${x.msg}`).join("\n")
      : typeof detail === "object"
        ? detail?.mensaje
        : detail;
    throw new Error(
      `${response.status} · ${msg || t("Error de la API", "API error")}`,
    );
  }
  return body;
}
async function loadCatalog() {
  state.catalogError = "";
  try {
    const list = await fetchJSON("/cultivos");
    if (
      !Array.isArray(list) ||
      !list.length ||
      !list.every((c) => Number.isInteger(c.id) && typeof c.nombre === "string")
    )
      throw new Error(
        t("Catálogo de cultivos inválido.", "Invalid crop catalogue."),
      );
    state.catalog = list;
    if (!list.some((c) => c.id === state.cropId))
      state.cropId = orderedCrops()[0].id;
  } catch (e) {
    state.catalogError = e.message;
  }
  if (state.user) render();
}
async function analyse(action) {
  cancelResult();
  const p = state.view === "parcels" ? activeParcel() : null,
    location = p
      ? { ...(p.bbox ? { bbox: [...p.bbox] } : { point: [...p.point] }) }
      : state.point
        ? { point: [...state.point] }
        : null;
  const [start, end] = ranges(action);
  if (state.view === "parcels" && !p?.bbox) {
    state.error = t(
      "Delimita un área para esta parcela.",
      "Define an area for this plot.",
    );
    updateResults();
    return;
  }
  if (
    location &&
    !(location.bbox ? boxInGhana(location.bbox) : inGhana(location.point))
  ) {
    ghanaWarning();
    updateResults();
    return;
  }
  if (!location) {
    state.error = t("Selecciona una ubicación.", "Select a location.");
    updateResults();
    return;
  }
  if (action === "iac" && historicalDateError()) {
    state.error = historicalDateError();
    updateResults();
    return;
  }
  if (action === "rotaciones" && recommendationDateError()) {
    validateRecommendationDates();
    updateResults();
    return;
  }
  if (!start || !end || start > end) {
    state.error = t(
      "Introduce un rango de fechas válido.",
      "Enter a valid date range.",
    );
    updateResults();
    return;
  }
  if (
    action === "iac" &&
    (Date.parse(end) - Date.parse(start)) / 86400000 + 1 > 365
  ) {
    state.error = t(
      "El IAC admite un máximo de 365 días.",
      "IAC allows a maximum of 365 days.",
    );
    updateResults();
    return;
  }
  if (action === "iac" && !state.catalog.some((c) => c.id === state.cropId)) {
    state.error = t("Selecciona un cultivo válido.", "Select a valid crop.");
    updateResults();
    return;
  }
  const history = [...(p?.history || state.pointHistory)];
  const payload = {
    start_date: start,
    end_date: end,
    ...location,
    historial: history,
    accion: action,
    language,
    ...(action === "iac"
      ? { cultivo_id: state.cropId }
      : { n_recomendaciones: state.recCount || 3 }),
  };
  const context = {
    areaHa: location.bbox ? hectares(location.bbox) : null,
    name: p?.name || t("Punto seleccionado", "Selected point"),
    location: location.bbox
      ? `BBOX · ${coordText(location.bbox)}`
      : coordText(location.point),
    start,
    end,
    history,
    cropId: state.cropId,
  };
  const id = requestId;
  request = new AbortController();
  const controller = request;
  const timeout = setTimeout(() => controller.abort("timeout"), 240000);
  state.busy = true;
  updateResults();
  try {
    const data = await fetchJSON("/predecir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (id !== requestId) return;
    state.result = { action, data, context };
  } catch (e) {
    if (id !== requestId) return;
    state.error = controller.signal.aborted
      ? t(
          "La consulta ha superado cuatro minutos. Inténtalo de nuevo o reduce el período.",
          "The request exceeded four minutes. Retry or shorten the period.",
        )
      : e.message;
  } finally {
    clearTimeout(timeout);
    if (id === requestId) {
      state.busy = false;
      request = null;
      updateResults();
    }
  }
}
function startDraft(p = null) {
  cancelResult();
  state.draft = p
    ? structuredClone(p)
    : {
        name: "",
        point: null,
        bbox: null,
        history: [],
      };
  state.draft.point = null;
  state.selection = "bbox";
  state.firstCorner = null;
  render();
}
function attach() {
  document.querySelectorAll("[data-language]").forEach(
    (el) =>
      (el.onclick = () => {
        if (language === el.dataset.language) return;
        cancelResult();
        language = el.dataset.language;
        state.searches = {};
        try {
          localStorage.setItem("asase.language", language);
        } catch {
          storageWarning = true;
        }
        render();
      }),
  );
  $("#login-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    e.target.reset();
    state.user = "tech";
    render();
  });
  $("[data-demo]")?.addEventListener("click", () => {
    state.user = "demo";
    render();
  });
  $("[data-logout]")?.addEventListener("click", () => {
    cancelResult();
    geoId++;
    state.geoBusy = false;
    state.user = null;
    state.draft = null;
    state.view = "overview";
    render();
  });
  document.querySelectorAll("[data-view]").forEach(
    (el) =>
      (el.onclick = () => {
        if (
          state.draft &&
          !confirm(
            t(
              "Hay cambios sin guardar. ¿Descartarlos?",
              "There are unsaved changes. Discard them?",
            ),
          )
        )
          return;
        cancelResult();
        geoId++;
        state.geoBusy = false;
        state.draft = null;
        state.view = el.dataset.view;
        state.menu = false;
        render();
      }),
  );
  $("#menu")?.addEventListener("click", () => {
    state.menu = !state.menu;
    render();
  });
  $("#retry-catalog")?.addEventListener("click", loadCatalog);
  ["rec-start-date", "rec-end-date"].forEach((id, i) =>
    $("#" + id)?.addEventListener("change", (e) => {
      state.parcelRecRange[i] = e.target.value;
      cancelResult();
      validateRecommendationDates();
      updateResults();
    }),
  );
  $("#history-crop")?.addEventListener(
    "change",
    (e) => (state.historyCropId = e.target.value ? +e.target.value : null),
  );
  document.querySelectorAll("[data-search-for]").forEach((input) =>
    input.addEventListener("input", () => {
      const id = input.dataset.searchFor,
        select = $("#" + id),
        previous = Number(select.value) || null;
      state.searches[id] = input.value;
      select.innerHTML = options(previous, input.value);
      if ((Number(select.value) || null) !== previous)
        select.dispatchEvent(new Event("change", { bubbles: true }));
    }),
  );

  ["start-date", "end-date"].forEach((id, i) =>
    $("#" + id)?.addEventListener("change", (e) => {
      ranges()[i] = e.target.value;
      cancelResult();
      validateRecommendationDates();
      updateResults();
    }),
  );
  $("#crop")?.addEventListener("change", (e) => {
    state.cropId = e.target.value ? +e.target.value : null;
    cancelResult();
    updateResults();
  });
  $("#rec-count")?.addEventListener("change", (e) => {
    state.recCount = +e.target.value;
    cancelResult();
    updateResults();
  });
  document
    .querySelectorAll("[data-analyse]")
    .forEach((el) => (el.onclick = () => analyse(el.dataset.analyse)));
  $("#coordinates")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target;
    setPoint([Number(f.elements.lat.value), Number(f.elements.lon.value)], {
      pan: true,
    });
  });
  $("#locate")?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      toast(
        "Tu navegador no ofrece geolocalización.",
        "Your browser does not support geolocation.",
      );
      return;
    }
    const token = ++geoId;
    state.geoBusy = true;
    $("#locate").disabled = true;
    navigator.geolocation.getCurrentPosition(
      (p) => {
        if (token !== geoId || !state.user) return;
        state.geoBusy = false;
        if ($("#locate")) $("#locate").disabled = false;
        setPoint([p.coords.latitude, p.coords.longitude], { pan: true });
      },
      () => {
        if (token !== geoId) return;
        state.geoBusy = false;
        if ($("#locate")) $("#locate").disabled = false;
        toast(
          "No se pudo obtener tu ubicación. Revisa los permisos y usa HTTPS o localhost.",
          "Could not get your location. Check permissions and use HTTPS or localhost.",
        );
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  });
  $("#new-parcel")?.addEventListener("click", () => startDraft());
  $("#edit-parcel")?.addEventListener("click", () =>
    startDraft(activeParcel()),
  );
  $("#cancel-parcel")?.addEventListener("click", () => {
    state.draft = null;
    state.firstCorner = null;
    render();
  });
  document.querySelectorAll("[data-selection]").forEach(
    (el) =>
      (el.onclick = () => {
        state.selection = el.dataset.selection;
        state.firstCorner = null;
        state.draft.point = null;
        state.draft.bbox = null;
        render();
      }),
  );
  $("#parcel-name")?.addEventListener(
    "input",
    (e) => (state.draft.name = e.target.value),
  );
  $("#add-history")?.addEventListener("click", () => {
    if (editableHistory().length >= 100) {
      toast(
        "El historial admite hasta 100 cultivos.",
        "History allows up to 100 crops.",
      );
      return;
    }
    const id = +$("#history-crop").value;
    if (!state.catalog.some((c) => c.id === id)) return;
    editableHistory().push(id);
    cancelResult();
    render();
  });
  document.querySelectorAll("[data-remove-history]").forEach(
    (el) =>
      (el.onclick = () => {
        editableHistory().splice(+el.dataset.removeHistory, 1);
        cancelResult();
        render();
      }),
  );
  $("#parcel-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const d = state.draft;
    if (
      !d.name.trim() ||
      !boxInGhana(d.bbox) ||
      !d.history.every((id) => state.catalog.some((c) => c.id === id))
    ) {
      $("#parcel-error").textContent = t(
        "Revisa el nombre, el área dentro de Ghana y el historial.",
        "Check the name, the area within Ghana and the history.",
      );
      return;
    }
    if (
      parcels.some(
        (p) =>
          p.id !== d.id &&
          p.name.trim().toLocaleLowerCase() ===
            d.name.trim().toLocaleLowerCase(),
      )
    ) {
      $("#parcel-error").textContent = t(
        "Ya existe una parcela con ese nombre.",
        "A plot with that name already exists.",
      );
      return;
    }
    const saved = {
      ...d,
      id: d.id || crypto.randomUUID(),
      name: d.name.trim(),
    };
    const i = parcels.findIndex((p) => p.id === saved.id);
    if (i >= 0) parcels[i] = saved;
    else parcels.push(saved);
    const persisted = writeStore("asase.parcels.v3", parcels);
    state.selectedParcel = saved.id;
    state.draft = null;
    cancelResult();
    render();
    toast(
      persisted ? "Parcela guardada." : "Parcela conservada solo en memoria.",
      persisted ? "Plot saved." : "Plot kept in memory only.",
    );
  });
  document.querySelectorAll("[data-parcel]").forEach(
    (el) =>
      (el.onclick = () => {
        cancelResult();
        state.selectedParcel = el.dataset.parcel;
        const p = activeParcel();
        state.point = p.point || [
          (p.bbox[0] + p.bbox[2]) / 2,
          (p.bbox[1] + p.bbox[3]) / 2,
        ];
        render();
      }),
  );
  $("#delete-parcel")?.addEventListener("click", () => {
    if (
      !confirm(
        t(
          "¿Eliminar esta parcela y su historial?",
          "Delete this plot and its history?",
        ),
      )
    )
      return;
    parcels = parcels.filter((p) => p.id !== state.selectedParcel);
    writeStore("asase.parcels.v3", parcels);
    state.selectedParcel = null;
    cancelResult();
    render();
  });
  attachEconomics();
  const dateError = $("#historical-date-error");
  if (dateError) dateError.textContent = historicalDateError();
  $("#cancel-query")?.addEventListener("click", () => {
    cancelResult();
    updateResults();
  });
}
render();
loadCatalog();
