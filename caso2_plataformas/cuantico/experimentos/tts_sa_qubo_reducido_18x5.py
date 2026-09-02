import math
import os
import sys
import time
from collections import deque
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from modelo.grafo_saltos_segmentos_v4 import obtener_anclas_candidatas, construir_grafo_segmentos_v4
import cuantico.formulacion.qubo_caso2_18x5 as qmod
from cuantico.solvers.simulated_annealing import resolver_qubo_sa

qmod.C = 3.0
NUM_READS = 100
SWEEPS_LIST = [10, 50, 100, 500, 1000]
SEMILLAS = [20260902, 20260903, 20260904, 20260905, 20260906]
CONFIDENCE = 0.99

class Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, data):
        for s in self.streams: s.write(data); s.flush()
    def flush(self):
        for s in self.streams: s.flush()

def tts(t_read, p_success, confidence=CONFIDENCE):
    if p_success <= 0.0: return math.inf
    if p_success >= 1.0: return t_read
    return t_read * math.log(1.0-confidence) / math.log(1.0-p_success)

def fmt_tts(x):
    return 'no estimable' if math.isinf(x) else f'{x:.6f} s'

def bfs(grafo, inicio, meta):
    cola = deque([inicio]); ant = {inicio: None}
    while cola:
        a = cola.popleft()
        if a == meta: break
        for b in grafo.get(a, []):
            if b not in ant:
                ant[b] = a; cola.append(b)
    if meta not in ant: return None
    camino = []; a = meta
    while a is not None:
        camino.append(a); a = ant[a]
    return list(reversed(camino))

def reconstruir_ruta(muestra):
    activas = [e for e,v in muestra.items() if int(v) == 1]
    sig = {}
    for o,d in activas: sig.setdefault(o, []).append(d)
    ruta = [qmod.START]; actual = qmod.START; visit = {actual}
    while actual != qmod.GOAL:
        cand = sig.get(actual, [])
        if len(cand) != 1: return None
        actual = cand[0]
        if actual in visit: return None
        ruta.append(actual); visit.add(actual)
        if len(ruta) > qmod.L_OBJETIVO + 2: return None
    return ruta

def delta_l(grafo, muestra):
    ruta = reconstruir_ruta(muestra)
    if ruta is None: return None
    nodos = set(ruta)
    sub = {o:[d for d in grafo.get(o,[]) if d in nodos] for o in nodos}
    cbfs = bfs(sub, qmod.START, qmod.GOAL)
    if cbfs is None: return None
    return (len(ruta)-1) - (len(cbfs)-1)

def max_planos_consecutivos(ruta):
    if ruta is None: return None
    maximo = actual = 0
    for o,d in zip(ruta[:-1], ruta[1:]):
        if d[1] == o[1]:
            actual += 1; maximo = max(maximo, actual)
        else:
            actual = 0
    return maximo

def ejecutar_configuracion(grafo, Q, offset, sweeps):
    total = factibles = completas = 0
    tiempos = []; energia_min = math.inf
    for seed in SEMILLAS:
        t0 = time.perf_counter()
        ss = resolver_qubo_sa(Q, num_reads=NUM_READS, num_sweeps=sweeps, seed=seed)
        tiempos.append(time.perf_counter() - t0)
        for datum in ss.data(fields=['sample','num_occurrences']):
            muestra = {k:int(v) for k,v in datum.sample.items()}
            occ = int(datum.num_occurrences); total += occ
            energia = qmod.energia_qubo(Q, offset, muestra)
            energia_min = min(energia_min, energia)
            ev = qmod.evaluar_restricciones(grafo, muestra)
            if not ev['factible_qubo']: continue
            factibles += occ
            ruta = reconstruir_ruta(muestra)
            dl = delta_l(grafo, muestra)
            mp = max_planos_consecutivos(ruta)
            if ruta is not None and dl == 0 and mp is not None and mp <= 2:
                completas += occ
    p_fact = factibles/total; p_comp = completas/total
    t_read = sum(tiempos)/total
    return dict(sweeps=sweeps, energia_min=energia_min, p_fact=p_fact, p_comp=p_comp,
                t_read=t_read, tts_fact=tts(t_read,p_fact), tts_comp=tts(t_read,p_comp))

def ejecutar():
    candidatas = obtener_anclas_candidatas(qmod.ANCHO,qmod.ALTO,qmod.START,qmod.GOAL)
    posiciones = [qmod.START] + candidatas + [qmod.GOAL]
    grafo = construir_grafo_segmentos_v4(posiciones,qmod.START,qmod.GOAL)
    Q,offset = qmod.construir_qubo(grafo)
    print('='*120)
    print('CASO 2 — TTS SA SOBRE QUBO REDUCIDO 18x5')
    print('='*120)
    print(f'C={qmod.C}; reads/seed={NUM_READS}; seeds={SEMILLAS}; sweeps={SWEEPS_LIST}')
    print('Éxito 1: factibilidad QUBO. Éxito 2: factible + sin atajo + <=2 planos consecutivos.')
    print()
    resolver_qubo_sa(Q, num_reads=5, num_sweeps=5, seed=999999)
    resultados=[]
    for sweeps in SWEEPS_LIST:
        r = ejecutar_configuracion(grafo,Q,offset,sweeps); resultados.append(r)
        print(f"sweeps={sweeps:4d} | Emin={r['energia_min']:.1f} | p_fact={100*r['p_fact']:6.2f}% | "
              f"p_completa={100*r['p_comp']:6.2f}% | t/read={r['t_read']:.6f}s | "
              f"TTS99_fact={fmt_tts(r['tts_fact'])} | TTS99_completa={fmt_tts(r['tts_comp'])}")
    print('\nMEJORES CONFIGURACIONES')
    vf=[r for r in resultados if not math.isinf(r['tts_fact'])]
    vc=[r for r in resultados if not math.isinf(r['tts_comp'])]
    if vf:
        m=min(vf,key=lambda r:r['tts_fact']); print(f"Factibilidad QUBO: sweeps={m['sweeps']}, TTS99={m['tts_fact']:.6f}s")
    else: print('Factibilidad QUBO: TTS no estimable')
    if vc:
        m=min(vc,key=lambda r:r['tts_comp']); print(f"Ruta completa: sweeps={m['sweeps']}, TTS99={m['tts_comp']:.6f}s")
    else: print('Ruta completa: TTS no estimable')

if __name__ == '__main__':
    carpeta=os.path.join(RAIZ,'cuantico','resultados'); os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta=os.path.join(carpeta,f'tts_sa_qubo_reducido_18x5_{marca}.txt')
    original=sys.stdout
    try:
        with open(ruta,'w',encoding='utf-8') as f:
            sys.stdout=Tee(original,f); ejecutar(); print(); print(f'Registro guardado en: {ruta}')
    finally:
        sys.stdout=original
    print(f'\nTXT generado correctamente: {ruta}')