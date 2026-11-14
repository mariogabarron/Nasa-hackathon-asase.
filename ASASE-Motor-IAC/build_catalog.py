import json
from pathlib import Path

# Intervalos desde PDF "Parametros e Intervalos de Idoneidad ..." pp. 3-10.
# Cada tupla representa: (min_S3, min_S2, min_S1, max_S1, max_S2, max_S3).
# El ultimo max puede ser null cuando el documento NO especifica una banda superior S3/N.
NAMES=['temp_media_C','temp_min_C','temp_max_C','precipitacion_mm','radiacion_solar_MJ_m2','humedad_suelo_smap_m3m3','humedad_raiz_smap_m3m3','temp_suelo_smap_C','suelo_ph_0_30cm']

def crop(label,cycle,veto,nums,carbon,textures):
    assert len(nums)==9, label
    assert all(len(v)==6 for v in nums),label
    return dict(nombre=label,ciclo_dias=list(cycle),veto=veto,
                intervalos={k:list(v) for k,v in zip(NAMES,nums)},
                carbono_organico_minimos=dict(zip(['S3','S2','S1'],carbon)),
                textura={k:list(v) for k,v in textures.items()})

R={'Franco':'Franco','Franco-limoso':'Franco-limoso','Franco-arcilloso':'Franco-arcilloso','Franco-arenoso':'Franco-arenoso','Arcillo-limoso':'Arcillo-limoso','Arcilloso':'Arcilloso','Arenoso-franco':'Arenoso-franco','Arenoso':'Arenoso'}
C={}
C['maiz']=crop('Maíz',(90,120),['humedad_raiz_smap_m3m3','precipitacion_mm','temp_max_C'],[
 (15,18,22,28,32,35),(10,12,16,22,25,27),(20,24,28,33,36,39),(55,80,110,180,240,300),(12,15,18,24,27,30),(.12,.16,.22,.34,.40,.45),(.14,.18,.24,.36,.42,.46),(15,18,22,29,33,36),(4.8,5.2,5.8,7,7.6,8.2)
],(5,8,12),{'S1':['Franco','Franco-limoso','Franco-arcilloso'],'S2':['Franco-arenoso','Arcillo-limoso'],'S3':['Arenoso-franco','Arcilloso'],'N':['Arenoso']})
C['sorgo']=crop('Sorgo',(120,150),['humedad_raiz_smap_m3m3','temp_max_C'],[
 (18,21,25,31,35,38),(11,14,18,24,27,29),(22,26,30,36,40,43),(35,50,75,140,200,260),(13,16,19,25,28,31),(.08,.11,.16,.30,.36,.42),(.10,.13,.18,.32,.38,.44),(16,20,24,32,36,39),(4.5,5,5.5,7.2,7.8,8.4)
],(3.5,6,9),{'S1':['Franco','Franco-arcilloso','Franco-arenoso'],'S2':['Franco-limoso','Arcilloso'],'S3':['Arenoso-franco'],'N':['Arenoso']})
C['mijo_perla']=crop('Mijo perla',(120,150),['humedad_suelo_smap_m3m3'],[
 (19,22,26,33,36,40),(12,15,19,25,28,30),(24,28,32,38,41,44),(25,35,55,110,160,210),(14,17,20,26,29,32),(.06,.08,.12,.25,.31,.36),(.07,.10,.14,.27,.33,.38),(18,21,25,34,37,40),(4.5,5,5.5,7,7.6,8.2)
],(2.5,4.5,7),{'S1':['Franco-arenoso','Arenoso-franco','Franco'],'S2':['Franco-limoso','Franco-arcilloso'],'S3':['Arenoso'],'N':['Arcilloso']})
C['arroz_bajio']=crop('Arroz de bajío',(110,150),['humedad_raiz_smap_m3m3','precipitacion_mm','suelo_textura_clase'],[
 (18,21,24,30,33,36),(14,16,19,24,26,28),(22,25,29,34,37,40),(90,120,160,260,320,380),(11,14,17,23,26,29),(.18,.24,.30,.44,.48,None),(.20,.26,.32,.46,.50,None),(17,20,23,30,33,36),(4.5,5,5.5,6.8,7.4,8)
],(6,9,14),{'S1':['Arcilloso','Franco-arcilloso','Arcillo-limoso'],'S2':['Franco','Franco-limoso'],'S3':['Franco-arenoso'],'N':['Arenoso','Arenoso-franco']})
C['cacahuete']=crop('Cacahuete / Maní',(90,120),['suelo_textura_clase','humedad_suelo_smap_m3m3'],[
 (17,20,24,30,33,36),(11,14,18,23,25,27),(22,25,29,34,37,40),(45,65,90,150,200,250),(13,16,19,25,28,30),(.09,.12,.16,.28,.34,.39),(.10,.14,.18,.30,.36,.41),(17,20,24,31,34,37),(4.8,5.3,5.8,6.8,7.3,7.8)
],(4,6,10),{'S1':['Franco-arenoso','Franco'],'S2':['Arenoso-franco','Franco-limoso'],'S3':['Franco-arcilloso'],'N':['Arcilloso','Arenoso']})
C['name']=crop('Ñame',(240,270),['suelo_carbono_organico_g_kg','humedad_raiz_smap_m3m3','suelo_textura_clase'],[
 (18,21,25,30,33,36),(12,15,19,24,26,28),(22,25,29,34,37,39),(70,95,130,210,260,320),(12,14,17,23,26,28),(.13,.17,.22,.35,.40,.44),(.15,.19,.25,.37,.42,.46),(16,19,23,30,33,36),(4.5,5,5.5,6.8,7.3,7.8)
],(7,10,15),{'S1':['Franco','Franco-limoso','Franco-arenoso'],'S2':['Franco-arcilloso'],'S3':['Arenoso-franco'],'N':['Arcilloso','Arenoso']})
C['caupi']=crop('Caupí / Frijol carilla',(60,90),['humedad_suelo_smap_m3m3','temp_min_C'],[
 (17,20,24,31,34,37),(12,15,18,23,26,28),(22,26,30,35,38,41),(30,45,70,130,180,230),(12,15,18,24,27,30),(.07,.10,.15,.28,.34,.39),(.09,.12,.17,.30,.36,.41),(17,20,24,31,35,38),(4.5,5,5.5,7,7.6,8.2)
],(3,5,8),{'S1':['Franco-arenoso','Franco'],'S2':['Arenoso-franco','Franco-limoso','Franco-arcilloso'],'S3':['Arenoso'],'N':['Arcilloso']})
C['soja']=crop('Soja',(105,135),['humedad_raiz_smap_m3m3','suelo_ph_0_30cm'],[
 (17,20,23,29,32,35),(11,14,17,22,25,27),(21,25,28,33,36,39),(60,80,110,175,230,280),(12,15,18,24,27,30),(.11,.15,.20,.33,.39,.44),(.13,.17,.22,.35,.41,.45),(15,18,22,29,33,36),(5,5.5,6,7,7.5,8)
],(4.5,7,11),{'S1':['Franco','Franco-limoso','Franco-arcilloso'],'S2':['Franco-arenoso','Arcillo-limoso'],'S3':['Arcilloso','Arenoso-franco'],'N':['Arenoso']})
C['yuca']=crop('Yuca / Mandioca',(240,360),['humedad_raiz_smap_m3m3','temp_min_C'],[
 (18,21,25,30,34,37),(12,15,18,23,26,28),(22,26,30,35,38,41),(40,60,90,160,220,280),(12,15,18,24,27,30),(.08,.11,.16,.29,.35,.40),(.09,.13,.18,.31,.37,.42),(16,20,24,31,35,38),(4.2,4.6,5.2,6.8,7.5,8)
],(3,5,8),{'S1':['Franco-arenoso','Franco'],'S2':['Arenoso-franco','Franco-limoso'],'S3':['Franco-arcilloso','Arenoso'],'N':['Arcilloso']})
C['boniato']=crop('Boniato / Batata',(105,135),['suelo_textura_clase','humedad_raiz_smap_m3m3'],[
 (17,20,23,29,32,35),(12,14,17,22,25,27),(21,25,28,33,36,39),(45,65,95,155,210,260),(12,15,18,24,27,30),(.10,.13,.18,.30,.36,.41),(.11,.15,.20,.32,.38,.43),(16,19,22,29,33,36),(4.5,5,5.5,6.6,7.2,7.7)
],(4,6,10),{'S1':['Franco-arenoso','Franco'],'S2':['Arenoso-franco','Franco-limoso'],'S3':['Franco-arcilloso'],'N':['Arcilloso','Arenoso']})
C['bambara']=crop('Guisante Bambara',(105,135),['humedad_suelo_smap_m3m3','suelo_textura_clase'],[
 (18,20,24,31,35,38),(12,15,18,23,26,28),(22,26,30,36,39,42),(30,45,65,120,170,220),(13,16,19,25,28,31),(.07,.09,.14,.25,.31,.36),(.08,.11,.16,.27,.33,.38),(17,20,24,32,36,39),(4.3,4.8,5.3,6.6,7.2,7.8)
],(2.5,4.5,7),{'S1':['Franco-arenoso','Arenoso-franco'],'S2':['Franco','Arenoso'],'S3':['Franco-limoso','Franco-arcilloso'],'N':['Arcilloso']})
C['algodon']=crop('Algodón',(150,180),['temp_min_C','humedad_raiz_smap_m3m3','radiacion_solar_MJ_m2'],[
 (18,21,25,31,34,37),(12,15,18,23,26,28),(22,26,30,36,39,42),(45,65,95,155,210,260),(14,17,20,26,29,32),(.10,.13,.18,.31,.37,.42),(.11,.15,.20,.34,.40,.45),(17,20,24,31,35,38),(4.8,5.2,5.8,7.4,8,8.5)
],(4,6.5,10),{'S1':['Franco','Franco-arcilloso','Franco-limoso'],'S2':['Franco-arenoso','Arcilloso'],'S3':['Arenoso-franco'],'N':['Arenoso']})

WEIGHTS={
 'inicio_lluvias_siembra':{'meses':[4,5,6],'pesos':[.05,.03,.08,.22,.06,.24,.08,.08,.05,.06,.05]},
 'plena_lluvia_crecimiento':{'meses':[7,8,9],'pesos':[.08,.03,.04,.24,.12,.07,.18,.03,.07,.07,.07]},
 'retirada_lluvias_cosecha':{'meses':[10,11],'pesos':[.10,.04,.08,.12,.14,.06,.22,.04,.06,.07,.07]},
 'epoca_seca_harmattan':{'meses':[12,1,2,3],'pesos':[.08,.07,.14,.04,.08,.15,.24,.05,.05,.05,.05]},
}
for i,item in WEIGHTS.items():
    vals=item.pop('pesos');item['pesos']=dict(zip(NAMES[:9]+['suelo_carbono_organico_g_kg','suelo_textura_clase'],vals))
    assert abs(sum(item['pesos'].values())-1)<1e-10,(i,sum(item['pesos'].values()))
for k,v in C.items():
    assert set(v['intervalos'])==set(NAMES)
    assert set(v['textura'])=={'S1','S2','S3','N'}
    assert all(len(x)==6 for x in v['intervalos'].values())
    for p,x in v['intervalos'].items():
        if x[-1] is None: assert k=='arroz_bajio' and p.startswith('humedad_')
        else: assert x==sorted(x), (k,p,x)
    assert set(v['veto']).issubset(set(NAMES)|{'suelo_textura_clase','suelo_carbono_organico_g_kg'})
out={'fuentes':{'pesos':'Matriz de Pesos y Justificacion Agronomica - Norte de Ghana 2.pdf (pp. 1-4)',
 'umbrales':'Parametros e Intervalos de Idoneidad de los 12 Cultivos - Norte de Ghana.pdf (pp. 1-10)'},
 'estaciones':WEIGHTS,'cultivos':C}
Path('/mnt/data/asase-iac/configuracion_iac.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Generados',len(C),'cultivos,',len(WEIGHTS),'estaciones')
