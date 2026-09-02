import math, os, sys, time
from datetime import datetime

RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas
from modelo.distancias import construir_matriz_navegable
from modelo.grafo import construir_grafo
from modelo.qubo_pmedian import construir_qubo_pmedian
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo
from experimentos.ejecutar_qaoa_minimo import (
    importar_qiskit,
    convertir_qubo_a_quadratic_program,
    analizar_samples_qaoa,
)

K=2
REPS=1
ITERACIONES=[1,3,5,10,15,20,25,30]
SEED=20260902
CONFIDENCE=0.99

def prob_batch(p_shot,shots):
    if p_shot<=0: return 0.0
    if p_shot>=1: return 1.0
    return 1-(1-p_shot)**shots

def tts(t_run,p_batch):
    if p_batch<=0: return math.inf
    if p_batch>=1: return t_run
    return t_run*math.log(1-CONFIDENCE)/math.log(1-p_batch)

def ft(x):
    return "inf" if math.isinf(x) else f"{x:.3f}"

def ejecutar():
    q=importar_qiskit()
    StatevectorSampler=q["StatevectorSampler"]
    QuadraticProgram=q["QuadraticProgram"]
    MinimumEigenOptimizer=q["MinimumEigenOptimizer"]
    QAOA=q["QAOA"]
    COBYLA=q["COBYLA"]
    algorithm_globals=q["algorithm_globals"]

    candidatas=obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo=construir_grafo(MAPA_QAOA_MINIMO)
    matriz=construir_matriz_navegable(candidatas,grafo)
    pam=k_medoids_pam(candidatas,matriz,K)
    exacta=k_medoids_exhaustivo(candidatas,matriz,K)
    optimo=exacta["coste_total"]

    qubo=construir_qubo_pmedian(matriz,K,cota_factible=pam["coste_total"])
    qp=convertir_qubo_a_quadratic_program(qubo,QuadraticProgram)

    nvars=qubo["numero_variables"]
    SHOTS_LIST=[nvars,2*nvars,4*nvars,8*nvars]

    print("="*120)
    print("CASO 1 — BARRIDO QAOA + TTS99")
    print("="*120)
    print(f"Variables/qubits: {nvars}")
    print(f"p/reps: {REPS}")
    print(f"Iteraciones: {ITERACIONES}")
    print(f"Shots: {SHOTS_LIST}")
    print(f"Seed: {SEED}")
    print(f"Optimo exacto: {optimo}")
    print()

    for maxiter in ITERACIONES:
        for shots in SHOTS_LIST:
            algorithm_globals.random_seed=SEED
            sampler=StatevectorSampler(default_shots=shots,seed=SEED)
            qaoa=QAOA(
                sampler=sampler,
                optimizer=COBYLA(maxiter=maxiter),
                reps=REPS,
                initial_point=[0.0,1.0],
            )
            solver=MinimumEigenOptimizer(qaoa)

            t0=time.perf_counter()
            resultado=solver.solve(qp)
            tiempo=time.perf_counter()-t0

            a=analizar_samples_qaoa(resultado,qubo,matriz,optimo)
            p_fact=float(a["probabilidad_factible"])
            p_opt=float(a["probabilidad_optimo"])
            pb_fact=prob_batch(p_fact,shots)
            pb_opt=prob_batch(p_opt,shots)

            print(
                f"iter={maxiter:2d} | shots={shots:3d} | t={tiempo:8.3f}s | "
                f"p_fact/shot={100*p_fact:7.3f}% | p_opt/shot={100*p_opt:7.3f}% | "
                f"Pbatch_fact={100*pb_fact:7.3f}% | Pbatch_opt={100*pb_opt:7.3f}% | "
                f"TTS99_fact={ft(tts(tiempo,pb_fact))}s | "
                f"TTS99_opt={ft(tts(tiempo,pb_opt))}s"
            )
            sys.stdout.flush()

if __name__=="__main__":
    carpeta=os.path.join(RAIZ,"resultados"); os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"qaoa_tts_barrido_{marca}.txt")
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