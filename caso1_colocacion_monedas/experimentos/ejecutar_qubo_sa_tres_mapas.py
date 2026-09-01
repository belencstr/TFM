"""Resuelve los QUBO p-median de A, B y C mediante Simulated Annealing.

Compara:
- PAM, como algoritmo clásico principal.
- Búsqueda exhaustiva, como referencia exacta.
- Simulated Annealing, como solver clásico del QUBO.

Cada ejecución guarda automáticamente un TXT en `resultados/`.
"""

import os
import sys
import time
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_a_reducido import MAPA_A_REDUCIDO
from mapas.mapa_b_reducido import MAPA_B_REDUCIDO
from mapas.mapa_c_reducido import MAPA_C_REDUCIDO

from modelo.candidatas import obtener_candidatas
from modelo.distancias import construir_matriz_navegable
from modelo.grafo import construir_grafo
from modelo.qubo_pmedian import (
    construir_qubo_pmedian,
    comprobar_factibilidad,
    coste_pmedian_desde_asignacion,
)

from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo
from solvers.simulated_annealing_qubo import resolver_qubo_simulated_annealing


K = 4

# Parámetros iniciales del experimento.
# Se dejan explícitos para que queden registrados en cada TXT.
NUM_READS = 100
NUM_SWEEPS = 1000
SEED_BASE = 12345


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


def mapa_con_monedas(mapa, candidatas_seleccionadas):
    copia = [list(fila) for fila in mapa]

    for candidata in candidatas_seleccionadas:
        copia[candidata["fila"]][candidata["columna"]] = "o"

    return "\n".join("".join(fila) for fila in copia)


def analizar_muestras(qubo, matriz, resultado_sa):
    """Analiza factibilidad y calidad de todas las muestras de SA."""
    mejor_energia = resultado_sa["muestras"][0]

    mejor_factible = None
    lecturas_factibles = 0
    lecturas_totales = 0

    for muestra in resultado_sa["muestras"]:
        asignacion = muestra["asignacion"]
        ocurrencias = muestra["num_occurrences"]
        lecturas_totales += ocurrencias

        factibilidad = comprobar_factibilidad(qubo, asignacion)

        if not factibilidad["factible"]:
            continue

        lecturas_factibles += ocurrencias
        coste = coste_pmedian_desde_asignacion(matriz, asignacion)

        candidato = {
            **muestra,
            "factibilidad": factibilidad,
            "coste_pmedian": coste,
        }

        if (
            mejor_factible is None
            or candidato["coste_pmedian"] < mejor_factible["coste_pmedian"]
            or (
                candidato["coste_pmedian"] == mejor_factible["coste_pmedian"]
                and candidato["energia"] < mejor_factible["energia"]
            )
        ):
            mejor_factible = candidato

    fact_mejor_energia = comprobar_factibilidad(
        qubo,
        mejor_energia["asignacion"],
    )

    coste_mejor_energia = None
    if fact_mejor_energia["factible"]:
        coste_mejor_energia = coste_pmedian_desde_asignacion(
            matriz,
            mejor_energia["asignacion"],
        )

    return {
        "mejor_energia": {
            **mejor_energia,
            "factibilidad": fact_mejor_energia,
            "coste_pmedian": coste_mejor_energia,
        },
        "mejor_factible": mejor_factible,
        "lecturas_factibles": lecturas_factibles,
        "lecturas_totales": lecturas_totales,
        "tasa_factibilidad": (
            100.0 * lecturas_factibles / lecturas_totales
            if lecturas_totales
            else 0.0
        ),
    }


def ejecutar_mapa(nombre, mapa, seed):
    candidatas = obtener_candidatas(mapa)
    grafo = construir_grafo(mapa)
    matriz = construir_matriz_navegable(candidatas, grafo)

    # ------------------------------------------------------------
    # Referencias clásicas
    # ------------------------------------------------------------
    inicio = time.perf_counter()
    pam = k_medoids_pam(candidatas, matriz, K)
    tiempo_pam = time.perf_counter() - inicio

    inicio = time.perf_counter()
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    tiempo_exacto = time.perf_counter() - inicio

    # La solución PAM proporciona una cota factible para fijar P=PAM+1.
    qubo = construir_qubo_pmedian(
        matriz,
        K,
        cota_factible=pam["coste_total"],
    )

    # ------------------------------------------------------------
    # Simulated Annealing sobre el QUBO
    # ------------------------------------------------------------
    inicio = time.perf_counter()
    resultado_sa = resolver_qubo_simulated_annealing(
        qubo,
        num_reads=NUM_READS,
        num_sweeps=NUM_SWEEPS,
        seed=seed,
    )
    tiempo_sa = time.perf_counter() - inicio

    analisis = analizar_muestras(qubo, matriz, resultado_sa)

    print("=" * 84)
    print(f"CASO 1 — QUBO + SIMULATED ANNEALING — MAPA {nombre}")
    print("=" * 84)
    print(f"Dimensiones: {len(mapa)} x {len(mapa[0])}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"k: {K}")
    print("Distancia: navegable")
    print()

    print("REFERENCIA CLÁSICA")
    print(f"PAM: {pam['coste_total']}  | tiempo: {tiempo_pam:.6f} s")
    print(
        f"Óptimo exacto: {exacta['coste_total']}  | "
        f"tiempo: {tiempo_exacto:.6f} s"
    )
    print()

    print("QUBO")
    print(f"A = {qubo['A']}")
    print(f"B = {qubo['B']}")
    print(f"C = {qubo['C']}")
    print(f"Variables x: {len(qubo['variables_x'])}")
    print(f"Variables y: {len(qubo['variables_y'])}")
    print(f"Variables totales: {qubo['numero_variables']}")
    print(f"Términos cuadráticos: {qubo['numero_terminos_cuadraticos']}")
    print()

    print("SIMULATED ANNEALING")
    print(f"num_reads: {NUM_READS}")
    print(f"num_sweeps: {NUM_SWEEPS}")
    print(f"seed: {seed}")
    print(f"Tiempo SA: {tiempo_sa:.6f} s")
    print(
        f"Lecturas factibles: "
        f"{analisis['lecturas_factibles']}/{analisis['lecturas_totales']}"
    )
    print(f"Tasa de factibilidad: {analisis['tasa_factibilidad']:.2f}%")
    print()

    mejor_energia = analisis["mejor_energia"]
    print("MEJOR ENERGÍA ENCONTRADA")
    print(f"Energía QUBO: {mejor_energia['energia']:.6f}")
    print(f"Factible: {mejor_energia['factibilidad']['factible']}")
    print(
        "Número de monedas x=1: "
        f"{len(mejor_energia['factibilidad']['seleccionadas'])}"
    )
    if mejor_energia["coste_pmedian"] is not None:
        print(f"Coste p-median: {mejor_energia['coste_pmedian']}")
    else:
        print("Coste p-median: no se calcula al ser una muestra inviable.")
    print()

    mejor_factible = analisis["mejor_factible"]

    if mejor_factible is None:
        print("MEJOR SOLUCIÓN FACTIBLE")
        print("No se ha encontrado ninguna muestra factible.")
        print()
        gap = None
        coste_sa = None
        alcanza_optimo = False
    else:
        coste_sa = mejor_factible["coste_pmedian"]
        gap = (
            100.0
            * (coste_sa - exacta["coste_total"])
            / exacta["coste_total"]
            if exacta["coste_total"] != 0
            else 0.0
        )
        alcanza_optimo = coste_sa == exacta["coste_total"]

        indices = mejor_factible["factibilidad"]["seleccionadas"]
        seleccionadas = [candidatas[j] for j in indices]

        print("MEJOR SOLUCIÓN FACTIBLE")
        print(f"Coste p-median: {coste_sa}")
        print(f"Gap respecto al óptimo: {gap:.2f}%")
        print(f"Alcanza el óptimo exacto: {alcanza_optimo}")
        print("Monedas seleccionadas:")
        for candidata in seleccionadas:
            print(
                f"  {candidata['id']} -> "
                f"(fila={candidata['fila']}, "
                f"columna={candidata['columna']})"
            )
        print("Mapa resultante (o = moneda):")
        print(mapa_con_monedas(mapa, seleccionadas))
        print()

    return {
        "mapa": nombre,
        "candidatas": len(candidatas),
        "variables_qubo": qubo["numero_variables"],
        "pam": pam["coste_total"],
        "optimo": exacta["coste_total"],
        "sa": coste_sa,
        "gap": gap,
        "factibilidad": analisis["tasa_factibilidad"],
        "tiempo_sa": tiempo_sa,
        "alcanza_optimo": alcanza_optimo,
    }


def ejecutar_experimento():
    print("=" * 84)
    print("REGISTRO — QUBO P-MEDIAN + SIMULATED ANNEALING")
    print("=" * 84)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Problema: k-medoids / p-median")
    print("Solver QUBO: D-Wave SimulatedAnnealingSampler")
    print(f"k: {K}")
    print(f"num_reads: {NUM_READS}")
    print(f"num_sweeps: {NUM_SWEEPS}")
    print()

    resultados = []

    for indice, (nombre, mapa) in enumerate(
        (
            ("A", MAPA_A_REDUCIDO),
            ("B", MAPA_B_REDUCIDO),
            ("C", MAPA_C_REDUCIDO),
        )
    ):
        resultados.append(
            ejecutar_mapa(
                nombre,
                mapa,
                seed=SEED_BASE + indice,
            )
        )

    print("=" * 104)
    print("RESUMEN COMPARATIVO")
    print("=" * 104)
    print(
        f"{'Mapa':<7}"
        f"{'Cand.':>8}"
        f"{'Vars QUBO':>12}"
        f"{'PAM':>8}"
        f"{'Óptimo':>10}"
        f"{'SA':>10}"
        f"{'Gap (%)':>12}"
        f"{'Fact. (%)':>12}"
        f"{'t SA (s)':>12}"
    )

    for r in resultados:
        sa_txt = "-" if r["sa"] is None else str(r["sa"])
        gap_txt = "-" if r["gap"] is None else f"{r['gap']:.2f}"

        print(
            f"{r['mapa']:<7}"
            f"{r['candidatas']:>8}"
            f"{r['variables_qubo']:>12}"
            f"{r['pam']:>8}"
            f"{r['optimo']:>10}"
            f"{sa_txt:>10}"
            f"{gap_txt:>12}"
            f"{r['factibilidad']:>12.2f}"
            f"{r['tiempo_sa']:>12.4f}"
        )


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"qubo_sa_mapas_reducidos_k{K}_{marca_tiempo}.txt"
    ruta = os.path.join(carpeta_resultados, nombre)

    stdout_original = sys.stdout

    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar_experimento()
            print()
            print("=" * 84)
            print(f"Registro guardado en: {ruta}")
            print("=" * 84)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
