const { test } = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");
const { readFileSync } = require("node:fs");
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
function bridge(url, options = {}) {
  const r = spawnSync(
    process.env.ASASE_TEST_PYTHON || "python3",
    [path.join(__dirname, "frontend_bridge.py")],
    {
      input: JSON.stringify({
        url,
        method: options.method || "GET",
        body: options.body ? JSON.parse(options.body) : undefined,
      }),
      encoding: "utf8",
    },
  );
  if (r.status !== 0) throw new Error(r.stderr);
  const parsed = JSON.parse(r.stdout);
  return {
    ok: parsed.status < 400,
    status: parsed.status,
    json: async () => parsed.body,
  };
}
const catalogue = bridge("/cultivos");
async function setup({
  stored,
  brokenCatalog = false,
  storageBlocked = false,
} = {}) {
  const dom = new JSDOM(
    '<!doctype html><html><body><div id="app"></div></body></html>',
    {
      url: "http://localhost:8000/",
      runScripts: "outside-only",
      pretendToBeVisual: true,
    },
  );
  const w = dom.window;
  const NativeDate = w.Date;
  w.Date = class extends NativeDate {
    constructor(...args) {
      super(...(args.length ? args : ["2026-11-14T12:00:00Z"]));
    }
    static now() {
      return new NativeDate("2026-11-14T12:00:00Z").getTime();
    }
  };
  w.structuredClone = structuredClone;
  w.AbortController = AbortController;
  w.confirm = () => true;
  if (stored) w.localStorage.setItem("asase.parcels.v3", stored);
  if (storageBlocked)
    w.Storage.prototype.setItem = () => {
      throw new Error("quota");
    };
  w.SVGSVGElement.prototype.createSVGRect = () => ({});
  Object.defineProperty(w.HTMLElement.prototype, "clientWidth", {
    get() {
      return 700;
    },
  });
  Object.defineProperty(w.HTMLElement.prototype, "clientHeight", {
    get() {
      return 460;
    },
  });
  w.HTMLElement.prototype.getBoundingClientRect = function () {
    return {
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 700,
      bottom: 460,
      width: 700,
      height: 460,
    };
  };
  const calls = [];
  w.fetch = async (url, options = {}) => {
    calls.push({ url, ...options });
    if (url === "/cultivos")
      return brokenCatalog
        ? {
            ok: false,
            status: 503,
            json: async () => ({ detail: "Catálogo no disponible" }),
          }
        : catalogue;
    return bridge(url, options);
  };
  for (const file of ["vendor/leaflet/leaflet.js", "base.js", "app.js"])
    vm.runInContext(
      readFileSync(path.join(root, "frontend", file), "utf8"),
      dom.getInternalVMContext(),
      { filename: file },
    );
  const tick = () => new Promise((r) => setImmediate(r));
  await tick();
  const click = (s) => {
    const el = w.document.querySelector(s);
    assert.ok(el, `Missing ${s}`);
    el.click();
  };
  const fill = (s, v) => {
    const el = w.document.querySelector(s);
    assert.ok(el, `Missing ${s}`);
    el.value = v;
    el.dispatchEvent(new w.Event("input", { bubbles: true }));
    el.dispatchEvent(new w.Event("change", { bubbles: true }));
  };
  const submit = (s) =>
    w.document
      .querySelector(s)
      .dispatchEvent(
        new w.Event("submit", { bubbles: true, cancelable: true }),
      );
  return {
    dom,
    w,
    calls,
    click,
    fill,
    submit,
    tick,
    eval: (s) => vm.runInContext(s, dom.getInternalVMContext()),
  };
}
function mapClick(q, lat = 9.4, lng = -0.84) {
  q.eval(`map.fire('click',{latlng:L.latLng(${lat},${lng})})`);
}

test("Inicio, idiomas, Leaflet, zoom, punto e IAC real con fuentes controladas", async () => {
  const q = await setup();
  try {
    assert.ok(q.w.document.querySelector("#login-form"));
    q.click('[data-language="en"]');
    assert.match(q.w.document.body.textContent, /Welcome/);
    q.click('[data-language="es"]');
    q.click("[data-demo]");
    assert.equal(q.w.document.querySelectorAll("#crop option").length, 12);
    assert.ok(q.w.document.querySelector('[data-analyse="iac"]').disabled);
    const zoom = q.eval("map.getZoom()");
    q.click(".leaflet-control-zoom-in");
    assert.equal(q.eval("map.getZoom()"), zoom + 1);
    mapClick(q);
    assert.equal(q.eval("state.point[0]"), 9.4);
    q.fill("#start-date", "2025-04-01");
    q.fill("#end-date", "2025-04-03");
    q.fill("#crop", "1");
    q.click('[data-analyse="iac"]');
    await q.tick();
    const body = JSON.parse(q.calls.find((c) => c.url === "/predecir").body);
    assert.deepEqual(body, {
      start_date: "2025-04-01",
      end_date: "2025-04-03",
      point: [9.4, -0.84],
      historial: [],
      accion: "iac",
      language: "es",
      cultivo_id: 1,
    });
    assert.equal(q.eval("typeof state.result.data.iac"), "number");
    assert.ok(q.w.document.querySelector(".iac-number"));
    q.fill("#crop", "2");
    assert.equal(q.eval("state.result"), null);
    q.fill("#end-date", "2026-04-03");
    const n = q.calls.length;
    q.click('[data-analyse="iac"]');
    await q.tick();
    assert.equal(q.calls.length, n);
    assert.match(q.w.document.querySelector("#results").textContent, /365/);
    q.click("[data-logout]");
    assert.ok(q.w.document.querySelector("#login-form"));
  } finally {
    q.dom.window.close();
  }
});

test("Recomendaciones consume planes, muestra tramos e IAC estimado", async () => {
  const q = await setup();
  try {
    q.click("[data-demo]");
    q.click('[data-view="recommendations"]');
    mapClick(q);
    q.fill("#start-date", "2027-04-01");
    q.fill("#end-date", "2028-03-31");
    q.fill("#rec-count", "2");
    q.click('[data-analyse="rotaciones"]');
    await q.tick();
    const body = JSON.parse(q.calls.at(-1).body);
    assert.equal(body.accion, "rotaciones");
    assert.equal(body.n_recomendaciones, 2);
    assert.ok(!("cultivo_id" in body));
    assert.equal(q.w.document.querySelectorAll(".plan").length, 2);
    assert.ok(q.w.document.querySelectorAll(".rotation li").length > 0);
    assert.match(q.w.document.querySelector("#results").textContent, /2025/);
    assert.ok(q.w.document.querySelector(".rotation b"));
  } finally {
    q.dom.window.close();
  }
});

test("Crear área, historial ordenado, analizar, persistir, editar y eliminar parcela", async () => {
  const q = await setup();
  let stored;
  try {
    q.click("[data-demo]");
    q.click('[data-view="parcels"]');
    q.click("#new-parcel");
    q.fill("#parcel-name", "Tamale <norte>");
    assert.equal(q.w.document.querySelector("#parcel-crop"), null);
    q.click('[data-selection="bbox"]');
    mapClick(q, 9, -1);
    mapClick(q, 10, 0);
    q.fill("#history-crop", "1");
    q.click("#add-history");
    q.fill("#history-crop", "5");
    q.click("#add-history");
    q.submit("#parcel-form");
    const p = q.eval("parcels[0]");
    assert.deepEqual(Array.from(p.bbox), [9, -1, 10, 0]);
    assert.equal(p.point, null);
    assert.deepEqual(Array.from(p.history), [1, 5]);
    assert.ok(!q.w.document.querySelector("norte"));
    q.fill("#start-date", "2025-04-01");
    q.fill("#end-date", "2025-04-03");
    q.fill("#crop", "3");
    q.click('[data-analyse="iac"]');
    await q.tick();
    let body = JSON.parse(q.calls.at(-1).body);
    assert.deepEqual(body.bbox, [9, -1, 10, 0]);
    assert.ok(!("point" in body));
    assert.deepEqual(body.historial, [1, 5]);
    assert.equal(body.cultivo_id, 3);
    q.fill("#rec-start-date", "2027-01-01");
    q.fill("#rec-end-date", "2027-12-31");
    q.click('[data-analyse="rotaciones"]');
    await q.tick();
    assert.ok(q.w.document.querySelector(".plan"));
    q.click("#edit-parcel");
    q.fill("#parcel-name", "Tamale editada");
    q.click('[data-remove-history="0"]');
    q.submit("#parcel-form");
    stored = q.w.localStorage.getItem("asase.parcels.v3");
    assert.equal(JSON.parse(stored)[0].name, "Tamale editada");
    assert.deepEqual(JSON.parse(stored)[0].history, [5]);
    q.click("#delete-parcel");
    assert.equal(q.eval("parcels.length"), 0);
  } finally {
    q.dom.window.close();
  }
  const reloaded = await setup({ stored });
  try {
    reloaded.click("[data-demo]");
    reloaded.click('[data-view="parcels"]');
    assert.match(reloaded.w.document.body.textContent, /Tamale editada/);
    reloaded.click("[data-parcel]");
    assert.ok(
      !reloaded.w.document.querySelector('[data-analyse="iac"]').disabled,
    );
  } finally {
    reloaded.dom.window.close();
  }
});

test("Geolocalización y errores de API sin resultados inventados", async () => {
  const q = await setup();
  try {
    q.w.navigator.geolocation = {
      getCurrentPosition(ok) {
        ok({ coords: { latitude: 10.2, longitude: -1.2 } });
      },
    };
    q.click("[data-demo]");
    q.click("#locate");
    assert.equal(q.eval("state.point[0]"), 10.2);
    q.w.fetch = async () => ({
      ok: false,
      status: 503,
      json: async () => ({
        detail: {
          codigo: "CONFIGURACION",
          mensaje: "Earth Engine no está autorizado",
        },
      }),
    });
    q.click('[data-analyse="iac"]');
    await q.tick();
    assert.match(
      q.w.document.querySelector("#results").textContent,
      /503.*Earth Engine/,
    );
    assert.equal(q.eval("state.result"), null);
    q.w.navigator.geolocation = {
      getCurrentPosition(ok, fail) {
        fail({ code: 1 });
      },
    };
    q.click("#locate");
    assert.match(q.w.document.querySelector(".toast").textContent, /permisos/);
  } finally {
    q.dom.window.close();
  }
});

test("Respuestas tardías se descartan al cambiar de punto o cancelar", async () => {
  const q = await setup();
  try {
    q.click("[data-demo]");
    mapClick(q);
    let resolve;
    q.w.fetch = () => new Promise((r) => (resolve = r));
    q.click('[data-analyse="iac"]');
    assert.equal(q.eval("state.busy"), true);
    mapClick(q, 10, -1);
    resolve({
      ok: true,
      status: 200,
      json: async () => ({ iac: 99, razon: "resultado anterior" }),
    });
    await q.tick();
    assert.equal(q.eval("state.result"), null);
    assert.equal(q.eval("state.busy"), false);
    q.click('[data-analyse="iac"]');
    q.click("#cancel-query");
    resolve({ ok: true, status: 200, json: async () => ({ iac: 99 }) });
    await q.tick();
    assert.equal(q.eval("state.result"), null);
  } finally {
    q.dom.window.close();
  }
});

test("Catálogo caído bloquea consultas, permite reintentar; almacenamiento falla de forma visible", async () => {
  const q = await setup({ brokenCatalog: true });
  try {
    q.click("[data-demo]");
    mapClick(q);
    assert.ok(q.w.document.querySelector('[data-analyse="iac"]').disabled);
    assert.ok(q.w.document.querySelector("#retry-catalog"));
    q.w.fetch = async () => catalogue;
    q.click("#retry-catalog");
    await q.tick();
    assert.equal(q.w.document.querySelectorAll("#crop option").length, 12);
  } finally {
    q.dom.window.close();
  }
  const b = await setup({ storageBlocked: true });
  try {
    b.click("[data-demo]");
    b.click('[data-view="parcels"]');
    b.click("#new-parcel");
    b.fill("#parcel-name", "Sin espacio");
    mapClick(b);
    b.submit("#parcel-form");
    assert.match(b.w.document.body.textContent, /solo están en memoria/);
  } finally {
    b.dom.window.close();
  }
});

test("Recomendaciones rechaza pasado, hoy, rango inverso y vacío, sin peticiones", async () => {
  const q = await setup();
  try {
    q.click("[data-demo]");
    q.click('[data-view="recommendations"]');
    mapClick(q);
    assert.equal(q.w.document.querySelector("#start-date").min, "2026-11-15");
    const before = q.calls.length;
    for (const [start, end, pattern] of [
      ["2026-11-13", "2027-12-31", /futuras/],
      ["2026-11-14", "2027-12-31", /futuras/],
      ["2027-01-01", "2026-11-14", /futuras/],
      ["2027-12-31", "2027-01-01", /posterior/],
      ["", "2027-12-31", /Completa/],
    ]) {
      q.fill("#start-date", start);
      q.fill("#end-date", end);
      assert.match(
        q.w.document.querySelector("#recommendation-date-error").textContent,
        pattern,
      );
      assert.ok(
        q.w.document.querySelector('[data-analyse="rotaciones"]').disabled,
      );
      await q.eval('analyse("rotaciones")');
      assert.equal(q.calls.length, before);
    }
    q.fill("#start-date", "2027-01-01");
    q.fill("#end-date", "2027-12-31");
    assert.equal(
      q.w.document.querySelector("#recommendation-date-error").textContent,
      "",
    );
    assert.ok(
      !q.w.document.querySelector('[data-analyse="rotaciones"]').disabled,
    );
  } finally {
    q.dom.window.close();
  }
});

test("Parcelas migra sin cultivo plantado y separa fechas IAC de recomendaciones", async () => {
  const stored = JSON.stringify([
    {
      id: "old",
      name: "Parcela existente",
      point: [9, -1],
      bbox: null,
      cropId: 1,
      history: [5, 2],
    },
  ]);
  const q = await setup({ stored });
  try {
    assert.ok(
      !(
        "cropId" in JSON.parse(q.w.localStorage.getItem("asase.parcels.v3"))[0]
      ),
    );
    q.click("[data-demo]");
    q.click('[data-view="parcels"]');
    q.click('[data-parcel="old"]');
    assert.deepEqual(Array.from(q.eval("activeParcel().history")), [5, 2]);
    q.fill("#start-date", "2025-04-01");
    q.fill("#end-date", "2025-04-03");
    q.fill("#rec-start-date", "2027-01-01");
    q.fill("#rec-end-date", "2027-12-31");
    q.click('[data-analyse="rotaciones"]');
    await q.tick();
    let req = JSON.parse(q.calls.at(-1).body);
    assert.equal(req.start_date, "2027-01-01");
    assert.equal(req.end_date, "2027-12-31");
    q.click('[data-analyse="iac"]');
    await q.tick();
    req = JSON.parse(q.calls.at(-1).body);
    assert.equal(req.start_date, "2025-04-01");
    assert.equal(req.end_date, "2025-04-03");
    q.fill("#rec-start-date", "2026-11-14");
    assert.match(
      q.w.document.querySelector("#recommendation-date-error").textContent,
      /futuras/,
    );
    assert.ok(
      q.w.document.querySelector('[data-analyse="rotaciones"]').disabled,
    );
    assert.ok(!q.w.document.querySelector('[data-analyse="iac"]').disabled);
    q.click("#edit-parcel");
    assert.equal(q.w.document.querySelector("#parcel-crop"), null);
    q.submit("#parcel-form");
    assert.ok(
      !(
        "cropId" in JSON.parse(q.w.localStorage.getItem("asase.parcels.v3"))[0]
      ),
    );
  } finally {
    q.dom.window.close();
  }
});

test("Selectores alfabéticos ES/EN, sin IDs y búsqueda sin acentos", async () => {
  const q = await setup();
  try {
    q.click("[data-demo]");
    mapClick(q);
    const labels = () =>
      Array.from(q.w.document.querySelectorAll("#crop option")).map(
        (o) => o.textContent,
      );
    let names = labels();
    assert.deepEqual(
      names,
      [...names].sort((a, b) =>
        a.localeCompare(b, "es", { sensitivity: "base" }),
      ),
    );
    assert.ok(names.every((n) => !/#|\d/.test(n)));
    q.fill("#crop-search", "maiz");
    assert.match(q.w.document.querySelector("#crop").textContent, /Maíz/);
    assert.ok(
      !q.w.document.querySelector("#crop").textContent.includes("Algodón"),
    );
    q.fill("#crop", "1");
    q.click('[data-analyse="iac"]');
    await q.tick();
    q.fill("#crop-search", "zzzz");
    assert.match(
      q.w.document.querySelector("#crop").textContent,
      /Sin resultados/,
    );
    assert.ok(q.w.document.querySelector('[data-analyse="iac"]').disabled);
    q.click('[data-language="en"]');
    names = labels().filter((n) => n !== "Select a crop");
    assert.deepEqual(
      names,
      [...names].sort((a, b) =>
        a.localeCompare(b, "en", { sensitivity: "base" }),
      ),
    );
    assert.ok(names.includes("Maize"));
    q.click('[data-view="parcels"]');
    q.click("#new-parcel");
    q.fill("#history-crop-search", "pea");
    assert.match(
      q.w.document.querySelector("#history-crop").textContent,
      /Pea/i,
    );
  } finally {
    q.dom.window.close();
  }
});

test("IAC tres colores y nulo neutro; propuesta con mayor IAC primero", async () => {
  const q = await setup();
  try {
    q.click("[data-demo]");
    mapClick(q);
    for (const [value, klass] of [
      [0, "iac-low"],
      [39.99, "iac-low"],
      [40, "iac-medium"],
      [69.99, "iac-medium"],
      [70, "iac-high"],
      [100, "iac-high"],
      [null, "iac-none"],
    ]) {
      q.w.fetch = async () => ({
        ok: true,
        status: 200,
        json: async () => ({ iac: value, razon: null }),
      });
      q.click('[data-analyse="iac"]');
      await q.tick();
      assert.ok(
        q.w.document.querySelector(".iac-number").classList.contains(klass),
      );
    }
    q.click('[data-view="recommendations"]');
    q.w.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        recomendaciones: [
          {
            iac_medio_cultivado: 65,
            dias_cultivados: 365,
            rotacion: [],
            supuestos: [],
          },
          {
            iac_medio_cultivado: 90,
            dias_cultivados: 200,
            rotacion: [],
            supuestos: [],
          },
          {
            iac_medio_cultivado: null,
            dias_cultivados: 0,
            rotacion: [],
            supuestos: [],
          },
        ],
      }),
    });
    q.click('[data-analyse="rotaciones"]');
    await q.tick();
    assert.equal(
      q.w.document.querySelector(".plan .plan-metrics .iac-high").textContent,
      "90",
    );
    assert.ok(
      q.w.document.querySelectorAll(".plan")[1].querySelector(".iac-medium"),
    );
  } finally {
    q.dom.window.close();
  }
});

test("Cambio a inglés limpia resultados previos y pide razones y planes en inglés", async () => {
  const q = await setup();
  try {
    q.click("[data-demo]");
    mapClick(q);
    q.fill("#start-date", "2025-04-01");
    q.fill("#end-date", "2025-04-03");
    q.fill("#crop", "2");
    q.click('[data-analyse="iac"]');
    await q.tick();
    assert.match(
      q.w.document.querySelector("[data-api-text]").textContent,
      /Temperatura mínima/,
    );
    q.click('[data-language="en"]');
    assert.equal(q.w.document.querySelector(".iac-number"), null);
    q.click('[data-analyse="iac"]');
    await q.tick();
    assert.equal(JSON.parse(q.calls.at(-1).body).language, "en");
    assert.match(
      q.w.document.querySelector("[data-api-text]").textContent,
      /Minimum temperature/,
    );
    q.click('[data-view="recommendations"]');
    q.click('[data-analyse="rotaciones"]');
    await q.tick();
    const text = Array.from(q.w.document.querySelectorAll("[data-api-text]"))
      .map((el) => el.textContent)
      .join(" ");
    assert.match(text, /Proposal/);
    assert.ok(!text.includes("cultivos"));
  } finally {
    q.dom.window.close();
  }
});
