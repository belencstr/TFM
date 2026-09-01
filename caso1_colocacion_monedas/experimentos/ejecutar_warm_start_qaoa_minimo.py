"""Caso 1 — Warm-Start QAOA sobre la instancia mínima del p-median.

Mantiene la misma instancia y configuración del experimento QAOA estándar:
4 candidatas, k=2, 20 variables QUBO, p=1, 30 iteraciones COBYLA,
2048 shots y la misma semilla. La única diferencia es el warm start.
"""

import copy
import os
import sys
import time
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas
from modelo.distancias import construir_matriz_navegable
from modelo.grafo import construir_grafo, resumen_grafo
from modelo.qubo_pmedian import (
    construir_qubo_pmedian,
    comprobar_factibilidad,
    energia_qubo,
    nombre_y,
)
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo

K = 2
REPS = 1
MAXITER = 30
SHOTS = 2048
SEED = 20260814
EPSILON = 0.25
PRE_SOLVER_ITER = 1000
TOLERANCIA = 1e-8


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def importar_qiskit():
    try:
        from qiskit.primitives import StatevectorSampler
        from qiskit_optimization import QuadraticProgram
        from qiskit_optimization.algorithms import SlsqpOptimizer, WarmStartQAOAOptimizer
        from qiskit_optimization.minimum_eigensolvers import QAOA
        from qiskit_optimization.optimizers import COBYLA
        from qiskit_optimization.problems.variable import VarType
        from qiskit_optimization.utils import algorithm_globals
    except ImportError as exc:
        raise ImportError(
            "Faltan dependencias de Qiskit. Instala:\n"
            "    python -m pip install qiskit qiskit-optimization"
        ) from exc

    return locals()


def convertir_qubo_a_qp(qubo, QuadraticProgram):
    qp = QuadraticProgram(name="pmedian_warm_start_qaoa")
    for variable in qubo["variables"]:
        qp.binary_var(name=variable)

    qp.minimize(
        constant=float(qubo["constante"]),
        linear={k: float(v) for k, v in qubo["lineal"].items()},
        quadratic={(u, v): float(c) for (u, v), c in qubo["cuadratico"].items()},
    )
    return qp


def relajar_qp(qp, VarType):
    relajado = copy.deepcopy(qp)
    for variable in relajado.variables:
        variable.vartype = VarType.CONTINUOUS
        variable.lowerbound = 0.0
        variable.upperbound = 1.0
    return relajado


def coste_pmedian(matriz, asignacion):
    n = len(matriz)
    coste = 0.0
    for i in range(n):
        for j in range(n):
            coste += float(matriz[i][j]) * int(asignacion.get(nombre_y(i, j), 0))
    return int(round(coste)) if abs(coste - round(coste)) <= TOLERANCIA else coste


def asignacion_desde_vector(nombres, vector):
    return {nombre: int(round(float(valor))) for nombre, valor in zip(nombres, vector)}


def mapa_con_monedas(mapa, seleccionadas):
    copia = [list(fila) for fila in mapa]
    for candidata in seleccionadas:
        copia[candidata["fila"]][candidata["columna"]] = "o"
    return "\n".join("".join(fila) for fila in copia)


def analizar_samples(resultado, qubo, matriz, optimo):
    nombres = [variable.name for variable in resultado.variables]
    prob_factible = 0.0
    prob_optimo = 0.0
    mejor_factible = None
    muestras_factibles = 0

    for sample in resultado.samples:
        asignacion = asignacion_desde_vector(nombres, sample.x)
        fact = comprobar_factibilidad(qubo, asignacion)
        if not fact["factible"]:
            continue

        prob = float(sample.probability)
        muestras_factibles += 1
        prob_factible += prob
        coste = coste_pmedian(matriz, asignacion)
        energia = float(energia_qubo(qubo, asignacion))

        if abs(energia - float(coste)) > TOLERANCIA:
            raise RuntimeError("Muestra factible con energía QUBO distinta del coste p-median.")

        if abs(float(coste) - float(optimo)) <= TOLERANCIA:
            prob_optimo += prob

        candidato = {
            "factibilidad": fact,
            "coste": coste,
            "energia": energia,
            "probabilidad": prob,
        }
        if (
            mejor_factible is None
            or float(coste) < float(mejor_factible["coste"])
            or (
                float(coste) == float(mejor_factible["coste"])
                and prob > mejor_factible["probabilidad"]
            )
        ):
            mejor_factible = candidato

    return {
        "prob_factible": prob_factible,
        "prob_optimo": prob_optimo,
        "mejor_factible": mejor_factible,
        "muestras_factibles": muestras_factibles,
    }


def ejecutar():
    q = importar_qiskit()
    StatevectorSampler = q["StatevectorSampler"]
    QuadraticProgram = q["QuadraticProgram"]
    SlsqpOptimizer = q["SlsqpOptimizer"]
    WarmStartQAOAOptimizer = q["WarmStartQAOAOptimizer"]
    QAOA = q["QAOA"]
    COBYLA = q["COBYLA"]
    VarType = q["VarType"]
    algorithm_globals = q["algorithm_globals"]

    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    resumen = resumen_grafo(grafo)
    matriz = construir_matriz_navegable(candidatas, grafo)

    pam = k_medoids_pam(candidatas, matriz, K)
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    optimo = exacta["coste_total"]

    qubo = construir_qubo_pmedian(matriz, K, cota_factible=pam["coste_total"])
    qp = convertir_qubo_a_qp(qubo, QuadraticProgram)
    operador_ising, offset_ising = qp.to_ising()

    # Diagnóstico del pre-solver sobre la relajación continua.
    pre_solver = SlsqpOptimizer(iter=PRE_SOLVER_ITER)
    relajado = relajar_qp(qp, VarType)
    t0 = time.perf_counter()
    resultado_relajado = pre_solver.solve(relajado)
    tiempo_relajacion = time.perf_counter() - t0

    print("=" * 88)
    print("CASO 1 — WARM-START QAOA SOBRE INSTANCIA MÍNIMA")
    print("=" * 88)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dimensiones: {len(MAPA_QAOA_MINIMO)} x {len(MAPA_QAOA_MINIMO[0])}")
    print(f"Candidatas: {len(candidatas)} | k: {K}")
    print(f"Nodos: {resumen['nodos']} | Aristas: {resumen['aristas']} | Conexo: {resumen['conexo']}")
    print()

    print("REFERENCIA CLÁSICA")
    print(f"PAM: {pam['coste_total']}")
    print(f"Óptimo exhaustivo: {optimo}")
    print()

    print("QUBO / ISING")
    print(f"A = B = C = {qubo['A']}")
    print(f"Variables QUBO / qubits: {qubo['numero_variables']}")
    print(f"Términos cuadráticos: {qubo['numero_terminos_cuadraticos']}")
    print(f"Términos de Pauli: {len(operador_ising)}")
    print(f"Offset Ising: {float(offset_ising):.6f}")
    print()

    print("PRE-SOLVER — RELAJACIÓN CONTINUA")
    print("Método: SLSQP")
    print(f"Tiempo: {tiempo_relajacion:.4f} s")
    print(f"Objetivo relajado: {float(resultado_relajado.fval):.6f}")
    print("Valores relajados:")
    for variable, valor in zip(resultado_relajado.variables, resultado_relajado.x):
        print(f"  {variable.name:<8} = {float(valor):.6f}")
    print()

    algorithm_globals.random_seed = SEED
    sampler = StatevectorSampler(default_shots=SHOTS, seed=SEED)
    qaoa = QAOA(
        sampler=sampler,
        optimizer=COBYLA(maxiter=MAXITER),
        reps=REPS,
        initial_point=[0.0, 1.0],
    )

    warm_start = WarmStartQAOAOptimizer(
        pre_solver=pre_solver,
        relax_for_pre_solver=True,
        qaoa=qaoa,
        epsilon=EPSILON,
        num_initial_solutions=1,
    )

    print("WARM-START QAOA")
    print(f"p: {REPS} | COBYLA maxiter: {MAXITER} | shots: {SHOTS} | seed: {SEED}")
    print(f"epsilon: {EPSILON}")
    print()

    t0 = time.perf_counter()
    resultado = warm_start.solve(qp)
    tiempo = time.perf_counter() - t0

    nombres = [variable.name for variable in resultado.variables]
    asignacion = asignacion_desde_vector(nombres, resultado.x)
    fact = comprobar_factibilidad(qubo, asignacion)
    coste = coste_pmedian(matriz, asignacion) if fact["factible"] else None
    analisis = analizar_samples(resultado, qubo, matriz, optimo)

    print("RESULTADO DEVUELTO")
    print(f"Tiempo Warm-Start QAOA: {tiempo:.4f} s")
    print(f"Objetivo QUBO: {float(resultado.fval):.6f}")
    print(f"Factible: {fact['factible']}")
    print(f"Monedas seleccionadas: {len(fact['seleccionadas'])}")

    if coste is not None:
        gap = 100.0 * (float(coste) - float(optimo)) / float(optimo) if optimo else 0.0
        print(f"Coste p-median: {coste}")
        print(f"Gap: {gap:.2f}%")
        print(f"Alcanza el óptimo: {abs(float(coste) - float(optimo)) <= TOLERANCIA}")
        seleccionadas = [candidatas[j] for j in fact["seleccionadas"]]
        print("Posiciones seleccionadas:")
        for c in seleccionadas:
            print(f"  {c['id']} -> (fila={c['fila']}, columna={c['columna']})")
        print("Mapa:")
        print(mapa_con_monedas(MAPA_QAOA_MINIMO, seleccionadas))
    else:
        print("Coste p-median: no se calcula por inviabilidad.")
    print()

    print("DISTRIBUCIÓN DE MUESTRAS")
    print(f"Probabilidad factible: {100.0 * analisis['prob_factible']:.4f}%")
    print(f"Probabilidad óptima: {100.0 * analisis['prob_optimo']:.4f}%")
    print(f"Muestras factibles distintas: {analisis['muestras_factibles']}")

    mejor = analisis["mejor_factible"]
    if mejor is not None:
        print(f"Mejor coste factible observado: {mejor['coste']}")
        print(f"Probabilidad de esa muestra: {100.0 * mejor['probabilidad']:.4f}%")
    else:
        print("No se observó ninguna muestra factible.")
    print()

    print("COMPARACIÓN CON QAOA ESTÁNDAR")
    print("QAOA estándar anterior: 0% factible y 0% óptimo.")
    if analisis["prob_factible"] > 0:
        print("Warm-Start mejora la factibilidad respecto a la ejecución estándar.")
    else:
        print("Warm-Start tampoco produjo muestras factibles.")
    if analisis["prob_optimo"] > 0:
        print("Warm-Start asignó probabilidad positiva a soluciones óptimas.")
    else:
        print("Warm-Start no muestreó soluciones óptimas.")


def main():
    carpeta = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(carpeta, f"warm_start_qaoa_pmedian_4cand_k{K}_p{REPS}_{marca}.txt")

    stdout_original = sys.stdout
    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar()
            print()
            print("=" * 88)
            print(f"Registro guardado en: {ruta}")
            print("=" * 88)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
