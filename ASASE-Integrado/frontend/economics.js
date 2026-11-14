"use strict";
// Adelesi et al. (2023), Table 4, doi:10.3390/su15097386, CC BY 4.0.
// Historical Northern Ghana budgets: total revenue and total variable cost, GHS/ha/cycle.
// Maize: medium management. Rice: upland. Do not infer yield from IAC.
const ECON_REFERENCES = Object.freeze({
  1: { revenue: 3603.6, cost: 4654.7 },
  4: { revenue: 6343.5, cost: 4011.2 },
  5: { revenue: 5062.2, cost: 3570.4 },
  7: { revenue: 2935, cost: 2696.3 },
});
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
