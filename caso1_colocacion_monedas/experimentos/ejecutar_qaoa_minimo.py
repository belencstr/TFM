"""Caso 1 — QAOA sobre una instancia mínima del p-median.

Instancia:
    4 candidatas
    k = 2 monedas

Con la formulación directa:
    4 variables x
    16 variables y
    20 variables QUBO = 20 qubits

Flujo:
1. Construir grafo y distancias.
2. Resolver p-median exactamente por búsqueda exhaustiva.
3. Construir exactamente el mismo QUBO ya validado.
4. Convertir el QUBO a QuadraticProgram / Hamiltoniano de Ising.
5. Resolver mediante QAOA en StatevectorSampler.
6. Comprobar factibilidad, coste y probabilidad de muestrear óptimos.

La salida se muestra por consola y se guarda automáticamente en resultados/.
"""

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

# QAOA inicial deliberadamente sencillo.
REPS = 1
MAXITER = 30
SHOTS = 2048
SEED = 20260814

TOLERANCIA = 1e-8


class Tee:
    """Duplica stdout en consola y fichero."""

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
    """Importa las clases necesarias con un mensaje de instalación claro."""
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


def convertir_qubo_a_quadratic_program(qubo, QuadraticProgram):
    """Crea un QuadraticProgram sin restricciones a partir de nuestro QUBO."""
    qp = QuadraticProgram(name="pmedian_qaoa_minimo")

    # El orden es importante: Qiskit mapea las variables a qubits
    # siguiendo el orden en que aparecen en el QuadraticProgram.
    for variable in qubo["variables"]:
        qp.binary_var(name=variable)

    qp.minimize(
        constant=float(qubo["constante"]),
        linear={
            variable: float(coef)
            for variable, coef in qubo["lineal"].items()
        },
        quadratic={
            (u, v): float(coef)
            for (u, v), coef in qubo["cuadratico"].items()
        },
    )

    return qp


def coste_pmedian_seguro(matriz, asignacion):
    n = len(matriz)
    coste = 0.0

    for i in range(n):
        for j in range(n):
            coste += (
                float(matriz[i][j])
                * int(asignacion.get(nombre_y(i, j), 0))
            )

    if abs(coste - round(coste)) <= TOLERANCIA:
        return int(round(coste))

    return coste


def asignacion_desde_vector(nombres, vector):
    return {
        nombre: int(round(float(valor)))
        for nombre, valor in zip(nombres, vector)
    }


def mapa_con_monedas(mapa, candidatas):
    copia = [list(fila) for fila in mapa]

    for candidata in candidatas:
        copia[candidata["fila"]][candidata["columna"]] = "o"

    return "\n".join("".join(fila) for fila in copia)


def analizar_samples_qaoa(resultado, qubo, matriz, optimo):
    """Analiza la distribución de probabilidad producida por QAOA."""
    nombres = [variable.name for variable in resultado.variables]

    prob_factible = 0.0
    prob_optimo = 0.0
    mejor_factible = None
    muestras_factibles = 0

    for sample in resultado.samples:
        asignacion = asignacion_desde_vector(nombres, sample.x)
        factibilidad = comprobar_factibilidad(qubo, asignacion)

        if not factibilidad["factible"]:
            continue

        muestras_factibles += 1
        prob = float(sample.probability)
        prob_factible += prob

        coste = coste_pmedian_seguro(matriz, asignacion)
        energia = float(energia_qubo(qubo, asignacion))

        if abs(energia - float(coste)) > TOLERANCIA:
            raise RuntimeError(
                "Una muestra factible presenta energía QUBO distinta "
                "del coste p-median."
            )

        if abs(float(coste) - float(optimo)) <= TOLERANCIA:
            prob_optimo += prob

        candidato = {
            "asignacion": asignacion,
            "factibilidad": factibilidad,
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
        "probabilidad_factible": prob_factible,
        "probabilidad_optimo": prob_optimo,
        "mejor_factible": mejor_factible,
        "muestras_factibles_distintas": muestras_factibles,
    }


def ejecutar():
    qiskit = importar_qiskit()

    StatevectorSampler = qiskit["StatevectorSampler"]
    QuadraticProgram = qiskit["QuadraticProgram"]
    MinimumEigenOptimizer = qiskit["MinimumEigenOptimizer"]
    QAOA = qiskit["QAOA"]
    COBYLA = qiskit["COBYLA"]
    algorithm_globals = qiskit["algorithm_globals"]

    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    resumen = resumen_grafo(grafo)
    matriz = construir_matriz_navegable(candidatas, grafo)

    pam = k_medoids_pam(candidatas, matriz, K)
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    optimo = exacta["coste_total"]

    # P = coste de una solución factible + 1, igual que en experimentos previos.
    qubo = construir_qubo_pmedian(
        matriz,
        K,
        cota_factible=pam["coste_total"],
    )

    qp = convertir_qubo_a_quadratic_program(qubo, QuadraticProgram)

    # Traducción QUBO -> Ising.
    operador_ising, offset_ising = qp.to_ising()

    print("=" * 84)
    print("CASO 1 — QAOA SOBRE INSTANCIA MÍNIMA")
    print("=" * 84)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dimensiones: {len(MAPA_QAOA_MINIMO)} x {len(MAPA_QAOA_MINIMO[0])}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"Nodos navegables: {resumen['nodos']}")
    print(f"Aristas: {resumen['aristas']}")
    print(f"Grafo conexo: {resumen['conexo']}")
    print(f"k: {K}")
    print()

    print("CANDIDATAS")
    for candidata in candidatas:
        print(
            f"  {candidata['id']} -> "
            f"(fila={candidata['fila']}, columna={candidata['columna']})"
        )
    print()

    print("REFERENCIA CLÁSICA")
    print(f"PAM: {pam['coste_total']}")
    print(f"Óptimo exhaustivo: {optimo}")
    print(f"PAM alcanza el óptimo: {pam['coste_total'] == optimo}")
    print("Selección óptima de referencia:")
    for candidata in exacta["candidatas"]:
        print(
            f"  {candidata['id']} -> "
            f"(fila={candidata['fila']}, columna={candidata['columna']})"
        )
    print("Mapa óptimo de referencia:")
    print(mapa_con_monedas(MAPA_QAOA_MINIMO, exacta["candidatas"]))
    print()

    print("QUBO")
    print(f"A = {qubo['A']}")
    print(f"B = {qubo['B']}")
    print(f"C = {qubo['C']}")
    print(f"Variables x: {len(qubo['variables_x'])}")
    print(f"Variables y: {len(qubo['variables_y'])}")
    print(f"Variables QUBO totales: {qubo['numero_variables']}")
    print(f"Términos cuadráticos: {qubo['numero_terminos_cuadraticos']}")
    print()

    print("HAMILTONIANO DE ISING")
    print(f"Qubits: {operador_ising.num_qubits}")
    print(f"Términos de Pauli: {len(operador_ising)}")
    print(f"Offset Ising: {float(offset_ising):.6f}")
    print()

    print("QAOA")
    print(f"reps (p): {REPS}")
    print(f"COBYLA maxiter: {MAXITER}")
    print(f"shots: {SHOTS}")
    print(f"seed: {SEED}")
    print()

    algorithm_globals.random_seed = SEED

    sampler = StatevectorSampler(
        default_shots=SHOTS,
        seed=SEED,
    )

    qaoa_mes = QAOA(
        sampler=sampler,
        optimizer=COBYLA(maxiter=MAXITER),
        reps=REPS,
        initial_point=[0.0, 1.0],
    )

    optimizador_qaoa = MinimumEigenOptimizer(qaoa_mes)

    inicio = time.perf_counter()
    resultado = optimizador_qaoa.solve(qp)
    tiempo = time.perf_counter() - inicio

    nombres = [variable.name for variable in resultado.variables]
    asignacion_resultado = asignacion_desde_vector(nombres, resultado.x)
    factibilidad_resultado = comprobar_factibilidad(
        qubo,
        asignacion_resultado,
    )

    coste_resultado = None
    if factibilidad_resultado["factible"]:
        coste_resultado = coste_pmedian_seguro(
            matriz,
            asignacion_resultado,
        )

    analisis = analizar_samples_qaoa(
        resultado,
        qubo,
        matriz,
        optimo,
    )

    print("RESULTADO DEVUELTO POR QAOA")
    print(f"Tiempo total: {tiempo:.4f} s")
    print(f"Energía/objetivo QUBO: {float(resultado.fval):.6f}")
    print(f"Factible para p-median: {factibilidad_resultado['factible']}")
    print(
        "Número de monedas seleccionadas: "
        f"{len(factibilidad_resultado['seleccionadas'])}"
    )

    if coste_resultado is not None:
        gap = (
            100.0
            * (float(coste_resultado) - float(optimo))
            / float(optimo)
            if optimo != 0
            else 0.0
        )
        print(f"Coste p-median: {coste_resultado}")
        print(f"Gap respecto al óptimo: {gap:.2f}%")
        print(
            "Alcanza el óptimo exacto: "
            f"{abs(float(coste_resultado) - float(optimo)) <= TOLERANCIA}"
        )

        seleccionadas = [
            candidatas[j]
            for j in factibilidad_resultado["seleccionadas"]
        ]

        print("Monedas seleccionadas:")
        for candidata in seleccionadas:
            print(
                f"  {candidata['id']} -> "
                f"(fila={candidata['fila']}, "
                f"columna={candidata['columna']})"
            )

        print("Mapa QAOA:")
        print(mapa_con_monedas(MAPA_QAOA_MINIMO, seleccionadas))
    else:
        print("Coste p-median: no se calcula porque el estado es inviable.")

    print()

    print("DISTRIBUCIÓN DE MUESTRAS QAOA")
    print(
        "Probabilidad total de soluciones factibles: "
        f"{100.0 * analisis['probabilidad_factible']:.2f}%"
    )
    print(
        "Probabilidad total de soluciones óptimas: "
        f"{100.0 * analisis['probabilidad_optimo']:.2f}%"
    )
    print(
        "Muestras factibles distintas observadas: "
        f"{analisis['muestras_factibles_distintas']}"
    )

    mejor_factible = analisis["mejor_factible"]

    if mejor_factible is not None:
        print(
            "Mejor coste factible presente en la distribución: "
            f"{mejor_factible['coste']}"
        )
        print(
            "Probabilidad de esa muestra concreta: "
            f"{100.0 * mejor_factible['probabilidad']:.2f}%"
        )
    else:
        print("No se observó ninguna muestra factible.")

    print()

    print("INTERPRETACIÓN")
    if analisis["probabilidad_optimo"] > 0:
        print(
            "QAOA asignó probabilidad positiva a al menos una solución "
            "óptima del mismo p-median."
        )
    else:
        print(
            "Con esta configuración, QAOA no muestreó ninguna solución "
            "óptima. Esto no invalida el QUBO; indica que deben estudiarse "
            "la profundidad p, el optimizador o la inicialización."
        )


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"qaoa_pmedian_4cand_k{K}_p{REPS}_{marca_tiempo}.txt"
    ruta = os.path.join(carpeta_resultados, nombre)

    stdout_original = sys.stdout

    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar()
            print()
            print("=" * 84)
            print(f"Registro guardado en: {ruta}")
            print("=" * 84)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
