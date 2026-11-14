import json
from pathlib import Path
rows=[
 ('2025-12-15',27,17,35, 1,22,.10,.16,27),
 ('2026-01-15',27,16,36, 0,23,.09,.14,29),
 ('2026-02-15',30,19,40, 0,24,.08,.12,34),
 ('2026-03-15',31,21,41, 8,25,.10,.13,36),
 ('2026-04-15',30,20,38,65,24,.19,.20,33),
 ('2026-05-15',28,20,35,125,22,.25,.26,29),
 ('2026-06-15',27,20,33,160,21,.29,.30,28),
 ('2026-07-15',26,19,33,175,18,.32,.33,27),
 ('2026-08-15',26,19,32,195,17,.34,.35,27),
 ('2026-09-15',27,20,34,150,20,.30,.32,29),
 ('2026-10-15',28,20,36,115,22,.25,.28,30),
 ('2026-11-14',29,20,36,85,23,.21,.26,32),
]
keys=['fecha','temp_media_C','temp_min_C','temp_max_C','precipitacion_mm','radiacion_solar_MJ_m2','humedad_suelo_smap_m3m3','humedad_raiz_smap_m3m3','temp_suelo_smap_C']
d={'region':'Northern','cultivo':'maiz','fecha_consulta':'2026-11-14','suelo':{'suelo_ph_0_30cm':6.3,'suelo_carbono_organico_g_kg':12.7,'suelo_textura_clase':'Franco','suelo_arcilla_pct':18,'suelo_arena_pct':42,'suelo_limo_pct':40},'observaciones':[dict(zip(keys,row)) for row in rows]}
p=Path(__file__).resolve().parent
(p/'ejemplo_entrada.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
