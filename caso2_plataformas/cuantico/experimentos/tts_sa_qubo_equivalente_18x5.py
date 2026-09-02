import math
import os
import sys
import time
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    ANCHO_PLATAFORMA, SUBIDA_MAX, CAIDA_MAX,
    obtener_anclas_candidatas, construir_grafo_segmentos_v4,
)
from cuantico.formulacion.qubo_caso2_equivalente import construir_qubo_equivalente
from cuantico.solvers.simulated_annealing import resolver_qubo_sa

ANCHO=18; ALTO=5; START=(0,2); GOAL=(17,2)
MIN_SALTOS=4; MAX_SALTOS=5; MIN_SUBIDAS=2; MIN_BAJADAS=2
NUM_READS=20
SWEEPS_LIST=[10,50,100,500,1000]
SEMILLAS=[20260902,20260903,20260904]
CONFIDENCE=0.99
ENERGIA_OPTIMA=4.0
TOL=1e-8

class Tee:
    def __init__(self,*streams): self.streams=streams
    def write(self,data):
        for s in self.streams: s.write(data); s.flush()
    def flush(self):
        for s in self.streams: s.flush()

def tts(t_read,p,confidence=CONFIDENCE):
    if p<=0: return math.inf
    if p>=1: return t_read
    return t_read*math.log(1-confidence)/math.log(1-p)

def fmt(x):
    return 'no estimable' if math.isinf(x) else f'{x:.6f} s'

def ejecutar_config(Q,offset,sweeps):
    total=optimos=0; tiempos=[]; emin=math.inf; esum=0.0
    for seed in SEMILLAS:
        t0=time.perf_counter()
        ss=resolver_qubo_sa(Q,num_reads=NUM_READS,num_sweeps=sweeps,seed=seed)
        tiempos.append(time.perf_counter()-t0)
        for d in ss.data(fields=['energy','num_occurrences']):
            e=float(d.energy)+float(offset); occ=int(d.num_occurrences)
            total += occ; esum += e*occ; emin=min(emin,e)
            if abs(e-ENERGIA_OPTIMA)<=TOL: optimos += occ
    p=optimos/total; tread=sum(tiempos)/total
    return dict(sweeps=sweeps,emin=emin,emean=esum/total,p=p,tread=tread,tts=tts(tread,p))

def ejecutar():
    candidatas=obtener_anclas_candidatas(ANCHO,ALTO,START,GOAL)
    posiciones=[START]+candidatas+[GOAL]
    grafo=construir_grafo_segmentos_v4(posiciones,START,GOAL)
    t0=time.perf_counter()
    Q,offset,meta=construir_qubo_equivalente(
        grafo=grafo,candidatas=candidatas,start=START,goal=GOAL,
        ancho_plataforma=ANCHO_PLATAFORMA,min_saltos=MIN_SALTOS,max_saltos=MAX_SALTOS,
        min_subidas=MIN_SUBIDAS,min_bajadas=MIN_BAJADAS,
        max_subida_fisica=SUBIDA_MAX,max_caida_fisica=CAIDA_MAX,
    )
    tbuild=time.perf_counter()-t0
    print('='*120)
    print('CASO 2 — TTS SA SOBRE QUBO EQUIVALENTE 18x5')
    print('='*120)
    print(f"Variables={meta['n_variables_total']} | términos={meta['n_terminos_qubo']} | P={meta['P']} | cota={meta['max_objetivo']}")
    print(f'Óptimo conocido={ENERGIA_OPTIMA} | build={tbuild:.3f}s | reads/seed={NUM_READS} | seeds={SEMILLAS}')
    print(f'sweeps={SWEEPS_LIST}')
    print()
    resolver_qubo_sa(Q,num_reads=2,num_sweeps=5,seed=999999)
    resultados=[]
    for sweeps in SWEEPS_LIST:
        r=ejecutar_config(Q,offset,sweeps); resultados.append(r)
        print(f"sweeps={sweeps:4d} | Emin={r['emin']:.1f} | Emean={r['emean']:.2f} | p_opt={100*r['p']:.4f}% | "
              f"t/read={r['tread']:.6f}s | TTS99_opt={fmt(r['tts'])}")
    finitos=[r for r in resultados if not math.isinf(r['tts'])]
    print()
    if finitos:
        m=min(finitos,key=lambda r:r['tts']); print(f"Mejor TTS: sweeps={m['sweeps']}, TTS99={m['tts']:.6f}s")
    else:
        print('No se observa ninguna muestra óptima: con p_empírico=0 no se puede estimar un TTS99 finito.')

if __name__=='__main__':
    carpeta=os.path.join(RAIZ,'cuantico','resultados'); os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta=os.path.join(carpeta,f'tts_sa_qubo_equivalente_18x5_{marca}.txt')
    original=sys.stdout
    try:
        with open(ruta,'w',encoding='utf-8') as f:
            sys.stdout=Tee(original,f); ejecutar(); print(); print(f'Registro guardado en: {ruta}')
    finally:
        sys.stdout=original
    print(f'\nTXT generado correctamente: {ruta}')