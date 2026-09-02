import math, os, sys, time
from datetime import datetime

RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from mapas.mapa_qubo_a import MAPA_QUBO_A
from mapas.mapa_qubo_b import MAPA_QUBO_B
from mapas.mapa_qubo_c import MAPA_QUBO_C
from modelo.candidatas import obtener_candidatas
from modelo.distancias import construir_matriz_navegable
from modelo.grafo import construir_grafo
from modelo.qubo_pmedian import construir_qubo_pmedian, comprobar_factibilidad, nombre_y
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo
from solvers.simulated_annealing_qubo import resolver_qubo_simulated_annealing

K=4
NUM_READS=100
SWEEPS_LIST=[10,50,100,500,1000]
SEEDS=[20260902,20260903,20260904,20260905,20260906]
CONFIDENCE=0.99
TOL=1e-8

def coste_pmedian(matriz,asignacion):
    n=len(matriz); c=0.0
    for i in range(n):
        for j in range(n):
            c += float(matriz[i][j])*int(asignacion.get(nombre_y(i,j),0))
    return c

def tts(t_read,p):
    if p<=0: return math.inf
    if p>=1: return t_read
    return t_read*math.log(1-CONFIDENCE)/math.log(1-p)

def ejecutar_config(nombre,mapa,sweeps):
    candidatas=obtener_candidatas(mapa)
    grafo=construir_grafo(mapa)
    matriz=construir_matriz_navegable(candidatas,grafo)
    pam=k_medoids_pam(candidatas,matriz,K)
    exacta=k_medoids_exhaustivo(candidatas,matriz,K)
    optimo=float(exacta["coste_total"])
    qubo=construir_qubo_pmedian(matriz,K,cota_factible=pam["coste_total"])

    total=fact=opt=0
    tiempo_total=0.0

    for seed in SEEDS:
        t0=time.perf_counter()
        resultado=resolver_qubo_simulated_annealing(
            qubo,num_reads=NUM_READS,num_sweeps=sweeps,seed=seed
        )
        tiempo_total += time.perf_counter()-t0

        for muestra in resultado["muestras"]:
            a=muestra["asignacion"]; occ=int(muestra["num_occurrences"])
            total += occ
            f=comprobar_factibilidad(qubo,a)
            if not f["factible"]:
                continue
            fact += occ
            if abs(coste_pmedian(matriz,a)-optimo)<=TOL:
                opt += occ

    p_fact=fact/total
    p_opt=opt/total
    t_read=tiempo_total/total

    return {
        "instancia":nombre,"vars":qubo["numero_variables"],"sweeps":sweeps,
        "p_fact":p_fact,"p_opt":p_opt,"t_read":t_read,
        "tts_fact":tts(t_read,p_fact),"tts_opt":tts(t_read,p_opt)
    }

def ft(x):
    return "inf" if math.isinf(x) else f"{x:.6f}"

def ejecutar():
    print("="*120)
    print("CASO 1 — BARRIDO SA Y TTS99")
    print("="*120)
    print(f"Seeds: {SEEDS}")
    print(f"Reads por seed: {NUM_READS}")
    print(f"Sweeps: {SWEEPS_LIST}")
    print("Exito: factibilidad u optimo exacto. TTS calculado por read.")
    print()

    resultados=[]
    for nombre,mapa in (("A-8",MAPA_QUBO_A),("B-9",MAPA_QUBO_B),("C-10",MAPA_QUBO_C)):
        for sweeps in SWEEPS_LIST:
            r=ejecutar_config(nombre,mapa,sweeps); resultados.append(r)
            print(
                f"{nombre} | vars={r['vars']} | sweeps={sweeps:4d} | "
                f"p_fact={100*r['p_fact']:6.2f}% | p_opt={100*r['p_opt']:6.2f}% | "
                f"t/read={r['t_read']:.6f}s | TTS99_fact={ft(r['tts_fact'])}s | "
                f"TTS99_opt={ft(r['tts_opt'])}s"
            )

    print()
    print("MEJOR TTS99 AL OPTIMO")
    for nombre in ("A-8","B-9","C-10"):
        rs=[r for r in resultados if r["instancia"]==nombre and not math.isinf(r["tts_opt"])]
        if not rs:
            print(f"{nombre}: no se observa optimo")
            continue
        m=min(rs,key=lambda r:r["tts_opt"])
        print(f"{nombre}: sweeps={m['sweeps']}, p_opt={100*m['p_opt']:.2f}%, TTS99={m['tts_opt']:.6f}s")

if __name__=="__main__":
    carpeta=os.path.join(RAIZ,"resultados"); os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"sa_tts_barrido_{marca}.txt")
    original=sys.stdout
    class Tee:
        def __init__(self,*s): self.s=s
        def write(self,d):
            for x in self.s: x.write(d); x.flush()
        def flush(self):
            for x in self.s: x.flush()
    try:
        with open(ruta,"w",encoding="utf-8") as f:
            sys.stdout=Tee(original,f); ejecutar(); print(); print(f"Registro guardado en: {ruta}")
    finally:
        sys.stdout=original
    print(f"\nTXT generado correctamente: {ruta}")