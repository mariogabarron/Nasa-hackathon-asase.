"use strict";
// All catalogue crops have a documented historical budget in GHS/ha/cycle.
// Pea uses an explicitly labelled external reference, not validated for Ghana.
const ECON_REFERENCES = Object.freeze(
  Object.fromEntries(
    Object.entries(ECONOMIC_DATA.crops).map(([id, c]) => [
      id,
      Object.freeze({ revenue: c.revenue, cost: c.cost }),
    ]),
  ),
);
const BUDGET_STORAGE_KEY = "asase.budgets.v1";
function loadBudgets() {
  const result = structuredClone(ECON_REFERENCES),
    stored = readStore(BUDGET_STORAGE_KEY, {});
  if (!stored || typeof stored !== "object" || Array.isArray(stored))
    return result;
  for (const id of Object.keys(result)) {
    const b = stored[id];
    if (
      b &&
      [b.revenue, b.cost].every(
        (v) =>
          v === null ||
          (typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 1e9),
      )
    )
      result[id] = { revenue: b.revenue, cost: b.cost };
  }
  return result;
}
// Truncate toward zero at presentation time; preserve calculation and ranking precision.
function truncated(value, digits = 2) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  const [mantissa, exponent = "0"] = String(value).split("e");
  const negative = mantissa.startsWith("-");
  const [whole, fraction = ""] = mantissa.replace("-", "").split(".");
  const raw = whole + fraction,
    dot = whole.length + Number(exponent);
  const expanded =
    dot <= 0
      ? "0." + "0".repeat(-dot) + raw
      : dot >= raw.length
        ? raw + "0".repeat(dot - raw.length)
        : raw.slice(0, dot) + "." + raw.slice(dot);
  const [integer, decimal = ""] = expanded.split(".");
  const tail = decimal.slice(0, digits).replace(/0+$/, "");
  const result = integer + (tail ? "." + tail : "");
  return (negative && Number(result) !== 0 ? "-" : "") + result;
}
function estimateEconomics(plan, budgets, catalog, area = 1) {
  const missing = new Set(),
    incomplete = new Set();
  let revenue = 0,
    cost = 0,
    cycles = 0;
  for (const r of plan.rotacion || []) {
    if (!r.cultivo_id) continue; // Fallow: no crop income or variable expenses assumed.
    const c = catalog.find((c) => c.id === r.cultivo_id),
      b = budgets[r.cultivo_id];
    if (!c || r.dias !== c.duracion_ciclo_dias) incomplete.add(r.cultivo_id);
    if (
      !b ||
      ![b.revenue, b.cost].every(
        (v) => typeof v === "number" && Number.isFinite(v) && v >= 0,
      )
    )
      missing.add(r.cultivo_id);
    else {
      revenue += Math.round(b.revenue * 100);
      cost += Math.round(b.cost * 100);
    }
    cycles++;
  }
  const complete =
    !missing.size &&
    !incomplete.size &&
    cycles > 0 &&
    Number.isFinite(area) &&
    area > 0;
  return {
    complete,
    missing: [...missing],
    incomplete: [...incomplete],
    cycles,
    revenue: complete ? (revenue / 100) * area : null,
    cost: complete ? (cost / 100) * area : null,
    margin: complete ? ((revenue - cost) / 100) * area : null,
    perHa: complete ? (revenue - cost) / 100 : null,
  };
}
