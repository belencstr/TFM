"""Solver QAOA para la formulación compacta de p-median / k-medoids.

Utiliza Qiskit (QuadraticProgram, StatevectorSampler, QAOA, MinimumEigenOptimizer).
Al trabajar con únicamente n qubits (en lugar de n + n^2), la convergencia es órdenes
de magnitud más rápida y la probabilidad de muestrear estados factibles y óptimos
es sustancialmente mayor.
"""

import time
try:
    from modelo.qubo_pmedian_compacto import (
        comprobar_factibilidad_compacto,
        coste_pmedian_compacto,
        energia_qubo_compacto,
    )
except (ImportError, ModuleNotFoundError):
    from caso1_colocacion_monedas.modelo.qubo_pmedian_compacto import (
        comprobar_factibilidad_compacto,
        coste_pmedian_compacto,
        energia_qubo_compacto,
    )


def importar_qiskit():
    """Importa las clases necesarias de Qiskit con un mensaje descriptivo si faltan."""
    try:
        from qiskit.primitives import StatevectorSampler
        from qiskit_optimization import QuadraticProgram
        from qiskit_optimization.algorithms import MinimumEigenOptimizer
        from qiskit_optimization.minimum_eigensolvers import QAOA
        from qiskit_optimization.optimizers import COBYLA
        from qiskit_optimization.utils import algorithm_globals
    except ImportError as exc:
        raise ImportError(
            "Faltan dependencias de Qiskit. Instala:\n"
            "    python -m pip install qiskit qiskit-optimization"
        ) from exc

    return {
        "StatevectorSampler": StatevectorSampler,
        "QuadraticProgram": QuadraticProgram,
        "MinimumEigenOptimizer": MinimumEigenOptimizer,
        "QAOA": QAOA,
        "COBYLA": COBYLA,
        "algorithm_globals": algorithm_globals,
    }


def convertir_qubo_compacto_a_qp(qubo, QuadraticProgram):
    """Convierte el diccionario QUBO compacto en un QuadraticProgram de Qiskit."""
    qp = QuadraticProgram(name="pmedian_compacto")

    for variable in qubo["variables"]:
        qp.binary_var(name=variable)

    qp.minimize(
        constant=float(qubo["constante"]),
        linear={var: float(coef) for var, coef in qubo["lineal"].items()},
        quadratic={(u, v): float(coef) for (u, v), coef in qubo["cuadratico"].items()},
    )

    return qp


def analizar_muestras_compacto(resultado, qubo, matriz_distancias, optimo_referencia=None):
    """Analiza la distribución de probabilidad generada por QAOA sobre el modelo compacto."""
    nombres = [var.name for var in resultado.variables]

    prob_factible = 0.0
    prob_optimo = 0.0
    muestras_factibles = 0
    muestras_analizadas = []

    for sample in resultado.samples:
        asignacion = {
            nom: int(round(float(val)))
            for nom, val in zip(nombres, sample.x)
        }
        fact = comprobar_factibilidad_compacto(qubo, asignacion)
        prob = float(sample.probability)
        energia = float(energia_qubo_compacto(qubo, asignacion))

        coste = None
        es_optimo = False

        if fact["factible"]:
            muestras_factibles += 1
            prob_factible += prob
            coste = coste_pmedian_compacto(matriz_distancias, fact["seleccionadas"])

            if optimo_referencia is not None and abs(float(coste) - float(optimo_referencia)) < 1e-6:
                prob_optimo += prob
                es_optimo = True

        muestras_analizadas.append({
            "asignacion": asignacion,
            "seleccionadas": fact["seleccionadas"],
            "factible": fact["factible"],
            "energia": energia,
            "coste": coste,
            "probabilidad": prob,
            "es_optimo": es_optimo,
        })

    # Ordenar por probabilidad descendente
    muestras_analizadas.sort(key=lambda m: m["probabilidad"], reverse=True)

    return {
        "probabilidad_factible": prob_factible,
        "probabilidad_optimo": prob_optimo,
        "muestras_factibles_distintas": muestras_factibles,
        "muestras": muestras_analizadas,
    }


def resolver_pmedian_qaoa_compacto(
    qubo,
    matriz_distancias,
    reps=1,
    maxiter=50,
    shots=1024,
    seed=42,
    optimo_referencia=None,
    initial_point=None,
):
    """Ejecuta QAOA sobre el modelo compacto y analiza la solución."""
    q = importar_qiskit()
    StatevectorSampler = q["StatevectorSampler"]
    QuadraticProgram = q["QuadraticProgram"]
    MinimumEigenOptimizer = q["MinimumEigenOptimizer"]
    QAOA = q["QAOA"]
    COBYLA = q["COBYLA"]
    algorithm_globals = q["algorithm_globals"]

    algorithm_globals.random_seed = seed

    qp = convertir_qubo_compacto_a_qp(qubo, QuadraticProgram)
    sampler = StatevectorSampler(default_shots=shots, seed=seed)

    kwargs_qaoa = {
        "sampler": sampler,
        "optimizer": COBYLA(maxiter=maxiter),
        "reps": reps,
    }
    if initial_point is not None:
        kwargs_qaoa["initial_point"] = initial_point

    qaoa = QAOA(**kwargs_qaoa)
    optimizador = MinimumEigenOptimizer(qaoa)

    t0 = time.perf_counter()
    resultado_qp = optimizador.solve(qp)
    tiempo_total = time.perf_counter() - t0

    nombres = [var.name for var in resultado_qp.variables]
    asignacion_mejor = {
        nom: int(round(float(val)))
        for nom, val in zip(nombres, resultado_qp.x)
    }
    fact_mejor = comprobar_factibilidad_compacto(qubo, asignacion_mejor)
    coste_mejor = (
        coste_pmedian_compacto(matriz_distancias, fact_mejor["seleccionadas"])
        if fact_mejor["factible"]
        else None
    )

    analisis = analizar_muestras_compacto(
        resultado_qp,
        qubo,
        matriz_distancias,
        optimo_referencia=optimo_referencia,
    )

    return {
        "tiempo": tiempo_total,
        "asignacion": asignacion_mejor,
        "seleccionadas": fact_mejor["seleccionadas"],
        "factible": fact_mejor["factible"],
        "energia": float(resultado_qp.fval),
        "coste": coste_mejor,
        "analisis_muestras": analisis,
        "qubits": qubo["numero_variables"],
        "shots": shots,
        "reps": reps,
        "maxiter": maxiter,
        "seed": seed,
        "resultado_qp": resultado_qp,
    }
