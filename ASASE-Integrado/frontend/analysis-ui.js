"use strict";
function pastLimit() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return iso(d);
}
function historicalDateError() {
  const [start, end] = ranges("iac");
  if (!start || !end)
    return t(
      "Completa las dos fechas del histórico.",
      "Enter both historical dates.",
    );
  if (start > pastLimit() || end > pastLimit())
    return t(
      "El histórico requiere fechas pasadas, hasta ayer. Modifica las fechas.",
      "Historical data requires past dates, up to yesterday. Please change the dates.",
    );
  if (start > end)
    return t(
      "La fecha final debe ser igual o posterior a la inicial.",
      "The end date must be on or after the start date.",
    );
  return "";
}
const editableHistory = () =>
  state.draft ? state.draft.history : state.pointHistory;
function ghanaWarning() {
  toast(
    "Selecciona un punto o un área completamente dentro de Ghana.",
    "Select a point or an area entirely within Ghana.",
  );
}
function referenceLabel(id) {
  const c = ECONOMIC_DATA.crops[id],
    src = ECONOMIC_DATA.sources[c.source];
  return `${t("Referencia histórica", "Historical reference")} · ${src.year} · ${c.basis[language]}`;
}
function economicsEditor(plans) {
  const ids = [
    ...new Set(
      plans.flatMap((p) =>
        (p.rotacion || []).map((r) => r.cultivo_id).filter(Boolean),
      ),
    ),
  ].sort((a, b) => cropLabel(a).localeCompare(cropLabel(b), language));
  if (!ids.length) return "";
  return `<details class="economic-editor"><summary>${t("Presupuesto económico · ajustar ingresos y costes", "Economic budget · adjust revenue and costs")}</summary><p>${t("GHS por hectárea y ciclo completo. Los 12 cultivos tienen valores iniciales. Actualízalos con tus ingresos y costes previstos; son referencias de distintos años y sistemas agrícolas.", "GHS per hectare and complete cycle. All 12 crops have initial values. Update them with your expected revenue and costs; references come from different years and farming systems.")}</p><form id="economic-budget">${ids
    .map((id) => {
      const b = state.budgets[id],
        ref = ECON_REFERENCES[id];
      const original =
        ref && b?.revenue === ref.revenue && b?.cost === ref.cost;
      return `<fieldset><legend>${esc(cropLabel(id))}</legend><p class="period-note">${original ? esc(referenceLabel(id)) : b ? t("Presupuesto propio", "Custom budget") : t("Sin referencia: introduce tu presupuesto", "No reference: enter your budget")}</p><div class="economic-fields"><label class="field">${t("Ingresos (GHS/ha/ciclo)", "Revenue (GHS/ha/cycle)")}<input type="number" min="0" max="1000000000" step="0.01" data-budget-crop="${id}" data-budget-field="revenue" value="${b?.revenue ?? ""}"></label><label class="field">${t("Costes variables (GHS/ha/ciclo)", "Variable costs (GHS/ha/cycle)")}<input type="number" min="0" max="1000000000" step="0.01" data-budget-crop="${id}" data-budget-field="cost" value="${b?.cost ?? ""}"></label></div></fieldset>`;
    })
    .join(
      "",
    )}<button type="submit" class="muted-button">${t("Guardar y actualizar beneficio", "Save and update benefit")}</button><p class="form-error" id="budget-error" role="alert"></p></form><p class="period-note">${t("Los ajustes se guardan en este navegador, sin sincronización entre dispositivos. Consulta el método, los años y las referencias de cada cultivo en Fuentes.", "Edits are saved in this browser, without syncing across devices. See Sources for each crop’s method, years and references.")}</p></details>`;
}
function economicPanel(plan, context) {
  const e = estimateEconomics(
    plan,
    state.budgets,
    state.catalog,
    context.areaHa ?? 1,
  );
  const label = t("Beneficio económico estimado", "Estimated economic benefit");
  if (!e.complete)
    return `<section class="economic-result"><h4>${label}</h4><p>${e.missing.length ? t("Completa ingresos y costes en el presupuesto para: ", "Complete revenue and costs in the budget for: ") + e.missing.map(cropLabel).map(esc).join(", ") : e.incomplete.length ? t("No calculable: la propuesta incluye ciclos incompletos o desconocidos.", "Cannot estimate: the proposal contains incomplete or unknown cycles.") : t("Sin ciclos de cultivo completos que valorar.", "No complete crop cycles to value.")}</p></section>`;
  const historical = (plan.rotacion || []).some((r) => {
    const b = state.budgets[r.cultivo_id],
      ref = ECON_REFERENCES[r.cultivo_id];
    return ref && b?.revenue === ref.revenue && b?.cost === ref.cost;
  });
  const external = (plan.rotacion || []).some((r) => {
    const b = state.budgets[r.cultivo_id],
      ref = ECON_REFERENCES[r.cultivo_id];
    return (
      ECONOMIC_DATA.crops[r.cultivo_id]?.external &&
      b?.revenue === ref?.revenue &&
      b?.cost === ref?.cost
    );
  });
  return `<section class="economic-result"><h4>${label}</h4>${external ? `<p class="notice">${t("Incluye guisante con referencia de Australia: estimación provisional sin validación económica en Ghana.", "Includes pea using an Australian reference: provisional estimate without economic validation in Ghana.")}</p>` : ""}<strong class="economic-value ${e.margin < 0 ? "economic-negative" : ""}">${truncated(e.margin)} GHS${context.areaHa ? "" : t("/ha", "/ha")}</strong><p>${t("Margen antes de costes fijos", "Margin before fixed costs")} · ${e.cycles} ${t("ciclos", "cycles")}${context.areaHa ? " · " + truncated(context.areaHa) + " ha " + t("aproximadas", "approximately") : ""}</p><p>${t("Ingresos", "Revenue")}: ${truncated(e.revenue)} · ${t("Costes variables", "Variable costs")}: ${truncated(e.cost)} GHS${context.areaHa ? "" : "/ha"}</p>${context.areaHa ? `<p>${truncated(e.perHa)} GHS/ha · ${t("Se supone cultivada toda el área seleccionada.", "Assumes the entire selected area is cultivated.")}</p>` : ""}<p class="period-note">${historical ? t("Escenario con referencias históricas de distintos años, no precios actuales. ", "Scenario using historical references from different years, not current prices. ") : t("Escenario con tu presupuesto. ", "Scenario using your budget. ")}${t("No es beneficio neto ni una ganancia garantizada. El IAC no se convierte en rendimiento.", "This is not net profit or a guaranteed return. IAC is not converted into yield.")}</p></section>`;
}
function attachEconomics() {
  const form = $("#economic-budget");
  if (!form) return;
  form.onsubmit = (e) => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const next = structuredClone(state.budgets);
    for (const input of form.querySelectorAll("[data-budget-crop]")) {
      const value = input.value === "" ? null : Number(input.value),
        id = input.dataset.budgetCrop;
      if (
        value !== null &&
        (!Number.isFinite(value) || value < 0 || value > 1e9)
      ) {
        $("#budget-error").textContent = t(
          "Introduce importes válidos y no negativos.",
          "Enter valid, non-negative amounts.",
        );
        return;
      }
      next[id] ??= { revenue: null, cost: null };
      next[id][input.dataset.budgetField] = value;
    }
    state.budgets = next;
    const saved = writeStore(BUDGET_STORAGE_KEY, next);
    updateResults();
    toast(
      saved
        ? "Presupuesto guardado y beneficio actualizado."
        : "No se pudo guardar: el presupuesto solo está en memoria.",
      saved
        ? "Budget saved and benefit updated."
        : "Could not save: the budget is kept in memory only.",
    );
  };
}
function economicsSources() {
  return `<section class="card view-panel"><h2>${t("Economía · fuentes y método", "Economics · sources and method")}</h2><p>${t("Referencias guardadas para los 12 cultivos, en GHS por hectárea y ciclo. Son escenarios históricos de distintos años y sistemas agrícolas: no equivalen a precios actuales ni permiten una comparación económica homogénea. Actualiza el presupuesto antes de tomar decisiones.", "Saved references for all 12 crops, in GHS per hectare and cycle. These are historical scenarios from different years and farming systems: they are not current prices or a like-for-like economic comparison. Update the budget before making decisions.")}</p>
  <div class="economic-table"><table><caption>${t("Presupuestos iniciales · GHS/ha/ciclo", "Initial budgets · GHS/ha/cycle")}</caption><thead><tr><th>${t("Cultivo", "Crop")}</th><th>${t("Ingresos", "Revenue")}</th><th>${t("Costes variables", "Variable costs")}</th><th>${t("Referencia", "Reference")}</th></tr></thead><tbody>${orderedCrops()
    .map((c) => {
      const b = ECONOMIC_DATA.crops[c.id],
        src = ECONOMIC_DATA.sources[b.source];
      return `<tr><td>${esc(cropLabel(c.id))}</td><td>${truncated(b.revenue)}</td><td>${truncated(b.cost)}</td><td><a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(src.title)}</a><br>${esc(b.basis[language])}</td></tr>`;
    })
    .join("")}</tbody></table></div>
  <p class="notice">${t("Guisante: referencia externa de Australia, convertida a GHS, sin validación económica en Ghana. La conversión de moneda no adapta rendimientos, precios ni costes al país.", "Pea: external Australian reference converted to GHS, without economic validation in Ghana. Currency conversion does not adapt yields, prices or costs to the country.")}</p>
  ${Object.values(ECONOMIC_DATA.sources)
    .map(
      (src) =>
        `<details class="economic-source"><summary>${esc(src.title)}</summary><p>${esc(src[language])}</p><a href="${esc(src.url)}" target="_blank" rel="noopener">${t("Consultar fuente", "View source")} ↗</a></details>`,
    )
    .join("")}
  <p>${t("Los importes convertidos se truncan a dos decimales al almacenarlos. No se aplica una actualización general por inflación. Los ajustes manuales se guardan en este navegador; no se envían a otros usuarios ni cambian las referencias documentadas.", "Converted amounts are truncated to two decimals when stored. No general inflation adjustment is applied. Manual edits are saved in this browser; they are not sent to other users and do not change the documented references.")}</p>
  <p><a href="https://mofep.gov.gh/sites/default/files/news/Methodologies_for_Preparation_and_Integrated_Appraisal_of_Public_Investment_Projects.pdf#page=91" target="_blank" rel="noopener">${t("Ministerio de Finanzas de Ghana · metodología, noviembre de 2024, pág. 83", "Ghana Ministry of Finance · methodology, November 2024, p. 83")} ↗</a></p><p>${t("Margen = ingresos − costes variables. Se suman los ciclos completos de la propuesta; para parcelas se multiplica por las hectáreas aproximadas del rectángulo. Para puntos se muestra por hectárea. El barbecho se supone sin ingresos ni costes variables. No se incluyen costes fijos, inversión, impuestos ni descuento temporal; tampoco se estima la mejora respecto a una situación previa.", "Margin = revenue − variable costs. Complete crop cycles are summed; for plots this is multiplied by the rectangle’s approximate hectares. Points show values per hectare. Fallow assumes no revenue or variable costs. Fixed costs, investment, taxes and time discounting are excluded; improvement over a prior baseline is not estimated.")}</p><p>${t("El IAC no escala los rendimientos ni cambia el presupuesto. Si vacías un campo, no se sustituye por cero. Las propuestas siguen ordenadas por IAC descendente.", "IAC does not scale yields or change the budget. Clearing a field does not replace it with zero. Proposals remain ordered by descending IAC.")}</p></section><section class="card view-panel"><h2>${t("Límite de Ghana", "Ghana boundary")}</h2><p><a href="https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM0/" target="_blank" rel="noopener">geoBoundaries · gbOpen GHA ADM0 ↗</a></p><p>${t("Copia local: GHA-ADM0-71095829, commit 9469f09. Año representado: 2007; compilación: 12/12/2023. Fuente: Stanford Digital Repository, dominio público. Se usa el polígono nacional, no su caja envolvente. No define límites catastrales.", "Local copy: GHA-ADM0-71095829, commit 9469f09. Represented year: 2007; build: 12 December 2023. Source: Stanford Digital Repository, public domain. Uses the national polygon, not its bounding box. Does not define cadastral boundaries.")}</p><a href="https://purl.stanford.edu/rh271yg5585" target="_blank" rel="noopener">Stanford Digital Repository ↗</a></section>`;
}
