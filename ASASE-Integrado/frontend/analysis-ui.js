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
function economicsEditor(plans) {
  const ids = [
    ...new Set(
      plans.flatMap((p) =>
        (p.rotacion || []).map((r) => r.cultivo_id).filter(Boolean),
      ),
    ),
  ].sort((a, b) => cropLabel(a).localeCompare(cropLabel(b), language));
  if (!ids.length) return "";
  return `<details class="economic-editor"><summary>${t("Presupuesto económico · ajustar ingresos y costes", "Economic budget · adjust revenue and costs")}</summary><p>${t("GHS por hectárea y ciclo completo. Actualiza las referencias históricas con tus precios y costes previstos. Completa los campos vacíos para estimar todas las propuestas.", "GHS per hectare and complete cycle. Update historical references with your expected revenue and costs. Fill empty fields to estimate every proposal.")}</p><form id="economic-budget">${ids
    .map((id) => {
      const b = state.budgets[id],
        ref = ECON_REFERENCES[id];
      const original =
        ref && b?.revenue === ref.revenue && b?.cost === ref.cost;
      return `<fieldset><legend>${esc(cropLabel(id))}</legend><p class="period-note">${original ? t("Referencia histórica · estudio de 2023, norte de Ghana", "Historical reference · 2023 study, Northern Ghana") : b ? t("Presupuesto propio", "Custom budget") : t("Sin referencia: introduce tu presupuesto", "No reference: enter your budget")}${id === 1 ? " · " + t("manejo medio", "medium management") : id === 4 ? " · " + t("arroz de secano", "upland rice") : ""}</p><div class="economic-fields"><label class="field">${t("Ingresos (GHS/ha/ciclo)", "Revenue (GHS/ha/cycle)")}<input type="number" min="0" max="1000000000" step="0.01" data-budget-crop="${id}" data-budget-field="revenue" value="${b?.revenue ?? ""}"></label><label class="field">${t("Costes variables (GHS/ha/ciclo)", "Variable costs (GHS/ha/cycle)")}<input type="number" min="0" max="1000000000" step="0.01" data-budget-crop="${id}" data-budget-field="cost" value="${b?.cost ?? ""}"></label></div></fieldset>`;
    })
    .join(
      "",
    )}<button type="submit" class="muted-button">${t("Actualizar beneficio estimado", "Update estimated benefit")}</button><p class="form-error" id="budget-error" role="alert"></p></form><p class="period-note">${t("Los presupuestos se mantienen durante esta sesión. Consulta el método y las referencias en Fuentes.", "Budgets are kept during this session. See Sources for the method and references.")}</p></details>`;
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
  return `<section class="economic-result"><h4>${label}</h4><strong class="economic-value ${e.margin < 0 ? "economic-negative" : ""}">${truncated(e.margin)} GHS${context.areaHa ? "" : t("/ha", "/ha")}</strong><p>${t("Margen antes de costes fijos", "Margin before fixed costs")} · ${e.cycles} ${t("ciclos", "cycles")}${context.areaHa ? " · " + truncated(context.areaHa) + " ha " + t("aproximadas", "approximately") : ""}</p><p>${t("Ingresos", "Revenue")}: ${truncated(e.revenue)} · ${t("Costes variables", "Variable costs")}: ${truncated(e.cost)} GHS${context.areaHa ? "" : "/ha"}</p>${context.areaHa ? `<p>${truncated(e.perHa)} GHS/ha · ${t("Se supone cultivada toda el área seleccionada.", "Assumes the entire selected area is cultivated.")}</p>` : ""}<p class="period-note">${historical ? t("Escenario con referencias históricas, no precios actuales. ", "Scenario using historical references, not current prices. ") : t("Escenario con tu presupuesto. ", "Scenario using your budget. ")}${t("No es beneficio neto ni una ganancia garantizada. El IAC no se convierte en rendimiento.", "This is not net profit or a guaranteed return. IAC is not converted into yield.")}</p></section>`;
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
    updateResults();
    toast(
      "Beneficio actualizado con el presupuesto.",
      "Benefit updated using the budget.",
    );
  };
}
function economicsSources() {
  return `<section class="card view-panel"><h2>${t("Economía · fuentes y método", "Economics · sources and method")}</h2><p><a href="https://doi.org/10.3390/su15097386" target="_blank" rel="noopener">Adelesi et al. (2023), Sustainability 15(9), 7386 · ${t("tabla 4", "Table 4")} ↗</a></p><p>${t("Estudio del norte de Ghana, publicado el 28/04/2023. Encuestas de 2020 y antes de la siembra de 2022. Importes históricos, sin actualizar por inflación: maíz con manejo medio, soja, arroz de secano y cacahuete. Licencia CC BY 4.0.", "Northern Ghana study, published 28 April 2023. Surveys in 2020 and before the 2022 planting season. Historical amounts, without inflation adjustment: medium-management maize, soybean, upland rice and groundnut. CC BY 4.0.")}</p><div class="economic-table"><table><caption>${t("Presupuesto de referencia · GHS/ha/ciclo", "Reference budget · GHS/ha/cycle")}</caption><thead><tr><th>${t("Cultivo", "Crop")}</th><th>${t("Ingresos", "Revenue")}</th><th>${t("Costes variables", "Variable costs")}</th></tr></thead><tbody>${Object.entries(
    ECON_REFERENCES,
  )
    .map(
      ([id, b]) =>
        `<tr><td>${esc(cropLabel(id))}</td><td>${truncated(b.revenue)}</td><td>${truncated(b.cost)}</td></tr>`,
    )
    .join(
      "",
    )}</tbody></table></div><p><a href="https://mofep.gov.gh/sites/default/files/news/Methodologies_for_Preparation_and_Integrated_Appraisal_of_Public_Investment_Projects.pdf#page=91" target="_blank" rel="noopener">${t("Ministerio de Finanzas de Ghana · metodología, noviembre de 2024, pág. 83", "Ghana Ministry of Finance · methodology, November 2024, p. 83")} ↗</a></p><p>${t("Margen = ingresos − costes variables. Se suman los ciclos completos de la propuesta; para parcelas se multiplica por las hectáreas aproximadas del rectángulo. Para puntos se muestra por hectárea. El barbecho se supone sin ingresos ni costes variables. No se incluyen costes fijos, inversión, impuestos ni descuento temporal; tampoco se estima la mejora respecto a una situación previa.", "Margin = revenue − variable costs. Complete crop cycles are summed; for plots this is multiplied by the rectangle’s approximate hectares. Points show values per hectare. Fallow assumes no revenue or variable costs. Fixed costs, investment, taxes and time discounting are excluded; improvement over a prior baseline is not estimated.")}</p><p>${t("El IAC no escala los rendimientos ni cambia el presupuesto. Los cultivos sin referencia necesitan datos propios; nunca se sustituyen datos ausentes por cero. El orden de las recomendaciones sigue siendo por IAC descendente.", "IAC does not scale yields or change the budget. Crops without references need custom data; missing values are never replaced with zero. Recommendations remain ordered by descending IAC.")}</p></section><section class="card view-panel"><h2>${t("Límite de Ghana", "Ghana boundary")}</h2><p><a href="https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM0/" target="_blank" rel="noopener">geoBoundaries · gbOpen GHA ADM0 ↗</a></p><p>${t("Copia local: GHA-ADM0-71095829, commit 9469f09. Año representado: 2007; compilación: 12/12/2023. Fuente: Stanford Digital Repository, dominio público. Se usa el polígono nacional, no su caja envolvente. No define límites catastrales.", "Local copy: GHA-ADM0-71095829, commit 9469f09. Represented year: 2007; build: 12 December 2023. Source: Stanford Digital Repository, public domain. Uses the national polygon, not its bounding box. Does not define cadastral boundaries.")}</p><a href="https://purl.stanford.edu/rh271yg5585" target="_blank" rel="noopener">Stanford Digital Repository ↗</a></section>`;
}
