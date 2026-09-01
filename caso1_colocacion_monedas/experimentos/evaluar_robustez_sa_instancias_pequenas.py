"""Robustez de Simulated Annealing sobre las instancias QUBO pequeñas.

Para cada una de las tres instancias:
    A -> 8 candidatas
    B -> 9 candidatas
    C -> 10 candidatas

se ejecuta Simulated Annealing con 20 semillas distintas, manteniendo:
    k = 4
    num_reads = 100
    num_sweeps = 1000

Se registra:
- número de ejecuciones que alcanzan el óptimo exacto;
- tasa de éxito;
- mejor, peor y coste medio;
- gap medio respecto al óptimo;
- factibilidad media;
- tiempo medio por ejecución.

La salida se muestra por consola y se guarda automáticamente en resultados/.
"""

import os
import sys
import time
from datetime import datetime
from statistics import mean, pstdev

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_qubo_a import MAPA_QUBO_A
from mapas.mapa_qubo_b import MAPA_QUBO_B
from mapas.mapa_qubo_c import MAPA_QUBO_C

from modelo.candidatas import obtener_candidatas
from modelo.distancias import construir_matriz_navegable
from modelo.grafo import construir_grafo
from modelo.qubo_pmedian import (
    construir_qubo_pmedian,
    comprobar_factibilidad,
    energia_qubo,
    nombre_y,
)

from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo
from solvers.simulated_annealing_qubo import resolver_qubo_simulated_annealing


K = 4
NUM_READS = 100
NUM_SWEEPS = 1000

NUM_SEMILLAS = 20
SEMILLA_INICIAL = 20260814

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


def coste_pmedian_seguro(matriz, asignacion):
    """Calcula el coste evitando posibles overflow numéricos."""
    n = len(matriz)
    coste = 0.0

    for i in range(n):
        for j in range(n):
            distancia = float(matriz[i][j])
            bit = int(asignacion.get(nombre_y(i, j), 0))
            coste += distancia * bit

    if abs(coste - round(coste)) <= TOLERANCIA:
        return int(round(coste))

    return coste


def analizar_muestras(qubo, matriz, resultado_sa):
    """Obtiene la mejor muestra factible y la tasa de factibilidad."""
    mejor_factible = None

    lecturas_totales = 0
    lecturas_factibles = 0

    errores_energia = 0
    errores_factibles = 0

    for muestra in resultado_sa["muestras"]:
        asignacion = muestra["asignacion"]
        ocurrencias = muestra["num_occurrences"]

        lecturas_totales += ocurrencias

        energia_sampler = float(muestra["energia"])
        energia_recalculada = float(energia_qubo(qubo, asignacion))

        if abs(energia_sampler - energia_recalculada) > TOLERANCIA:
            errores_energia += ocurrencias

        factibilidad = comprobar_factibilidad(qubo, asignacion)

        if not factibilidad["factible"]:
            continue

        lecturas_factibles += ocurrencias
        coste = coste_pmedian_seguro(matriz, asignacion)

        if abs(energia_recalculada - float(coste)) > TOLERANCIA:
            errores_factibles += ocurrencias

        candidato = {
            "asignacion": asignacion,
            "energia": energia_recalculada,
            "coste": coste,
            "factibilidad": factibilidad,
        }

        if (
            mejor_factible is None
            or float(coste) < float(mejor_factible["coste"])
            or (
                float(coste) == float(mejor_factible["coste"])
                and energia_recalculada < mejor_factible["energia"]
            )
        ):
            mejor_factible = candidato

    tasa_factibilidad = (
        100.0 * lecturas_factibles / lecturas_totales
        if lecturas_totales
        else 0.0
    )

    return {
        "mejor_factible": mejor_factible,
        "lecturas_totales": lecturas_totales,
        "lecturas_factibles": lecturas_factibles,
        "tasa_factibilidad": tasa_factibilidad,
        "errores_energia": errores_energia,
        "errores_factibles": errores_factibles,
    }


def ejecutar_instancia(nombre, mapa):
    candidatas = obtener_candidatas(mapa)
    grafo = construir_grafo(mapa)
    matriz = construir_matriz_navegable(candidatas, grafo)

    # Referencias calculadas una sola vez.
    pam = k_medoids_pam(candidatas, matriz, K)
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)

    qubo = construir_qubo_pmedian(
        matriz,
        K,
        cota_factible=pam["coste_total"],
    )

    optimo = exacta["coste_total"]

    resultados_semillas = []

    print("=" * 92)
    print(f"ROBUSTEZ SA — {nombre}")
    print("=" * 92)
    print(f"Candidatas: {len(candidatas)}")
    print(f"k: {K}")
    print(f"Variables QUBO: {qubo['numero_variables']}")
    print(f"Términos cuadráticos: {qubo['numero_terminos_cuadraticos']}")
    print(f"PAM: {pam['coste_total']}")
    print(f"Óptimo exacto: {optimo}")
    print(f"A = B = C = {qubo['A']}")
    print()

    print(
        f"{'Nº':>3} "
        f"{'Seed':>10} "
        f"{'Coste':>8} "
        f"{'Gap %':>9} "
        f"{'Fact. %':>10} "
        f"{'Óptimo':>9} "
        f"{'Tiempo (s)':>12}"
    )

    for indice in range(NUM_SEMILLAS):
        seed = SEMILLA_INICIAL + indice

        inicio = time.perf_counter()
        resultado_sa = resolver_qubo_simulated_annealing(
            qubo,
            num_reads=NUM_READS,
            num_sweeps=NUM_SWEEPS,
            seed=seed,
        )
        tiempo = time.perf_counter() - inicio

        analisis = analizar_muestras(qubo, matriz, resultado_sa)
        mejor = analisis["mejor_factible"]

        if mejor is None:
            coste = None
            gap = None
            alcanza_optimo = False
        else:
            coste = mejor["coste"]
            gap = (
                100.0 * (float(coste) - float(optimo)) / float(optimo)
                if optimo != 0
                else 0.0
            )
            alcanza_optimo = (
                abs(float(coste) - float(optimo)) <= TOLERANCIA
            )

        resultados_semillas.append(
            {
                "indice": indice + 1,
                "seed": seed,
                "coste": coste,
                "gap": gap,
                "factibilidad": analisis["tasa_factibilidad"],
                "optimo": alcanza_optimo,
                "tiempo": tiempo,
                "errores_energia": analisis["errores_energia"],
                "errores_factibles": analisis["errores_factibles"],
            }
        )

        coste_txt = "-" if coste is None else str(coste)
        gap_txt = "-" if gap is None else f"{gap:.2f}"

        print(
            f"{indice + 1:>3} "
            f"{seed:>10} "
            f"{coste_txt:>8} "
            f"{gap_txt:>9} "
            f"{analisis['tasa_factibilidad']:>10.2f} "
            f"{str(alcanza_optimo):>9} "
            f"{tiempo:>12.4f}"
        )

    validos = [r for r in resultados_semillas if r["coste"] is not None]

    exitos = sum(1 for r in resultados_semillas if r["optimo"])
    tasa_exito = 100.0 * exitos / NUM_SEMILLAS

    if validos:
        costes = [float(r["coste"]) for r in validos]
        gaps = [float(r["gap"]) for r in validos]
        factibilidades = [r["factibilidad"] for r in validos]

        mejor_coste = min(costes)
        peor_coste = max(costes)
        coste_medio = mean(costes)
        desviacion_coste = pstdev(costes) if len(costes) > 1 else 0.0
        gap_medio = mean(gaps)
        factibilidad_media = mean(factibilidades)
    else:
        mejor_coste = None
        peor_coste = None
        coste_medio = None
        desviacion_coste = None
        gap_medio = None
        factibilidad_media = 0.0

    tiempos = [r["tiempo"] for r in resultados_semillas]
    tiempo_medio = mean(tiempos)

    errores_energia_total = sum(
        r["errores_energia"] for r in resultados_semillas
    )
    errores_factibles_total = sum(
        r["errores_factibles"] for r in resultados_semillas
    )

    print()
    print("RESUMEN DE ROBUSTEZ")
    print(f"Ejecuciones: {NUM_SEMILLAS}")
    print(f"Ejecuciones con solución factible: {len(validos)}")
    print(f"Ejecuciones que alcanzan el óptimo: {exitos}")
    print(f"Tasa de éxito: {tasa_exito:.2f}%")

    if validos:
        print(f"Mejor coste encontrado: {mejor_coste:g}")
        print(f"Peor coste encontrado: {peor_coste:g}")
        print(f"Coste medio: {coste_medio:.4f}")
        print(f"Desviación típica del coste: {desviacion_coste:.4f}")
        print(f"Gap medio: {gap_medio:.2f}%")
        print(f"Factibilidad media: {factibilidad_media:.2f}%")

    print(f"Tiempo medio por ejecución: {tiempo_medio:.4f} s")
    print(f"Errores de energía detectados: {errores_energia_total}")
    print(
        "Errores energía/coste en muestras factibles: "
        f"{errores_factibles_total}"
    )
    print()

    return {
        "instancia": nombre,
        "candidatas": len(candidatas),
        "variables": qubo["numero_variables"],
        "optimo": optimo,
        "exitos": exitos,
        "tasa_exito": tasa_exito,
        "mejor_coste": mejor_coste,
        "peor_coste": peor_coste,
        "coste_medio": coste_medio,
        "gap_medio": gap_medio,
        "factibilidad_media": factibilidad_media,
        "tiempo_medio": tiempo_medio,
    }


def ejecutar_experimento():
    print("=" * 92)
    print("CASO 1 — ROBUSTEZ DE SIMULATED ANNEALING")
    print("=" * 92)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Problema: p-median / k-medoids")
    print("Solver QUBO: D-Wave SimulatedAnnealingSampler")
    print(f"k: {K}")
    print(f"Semillas por instancia: {NUM_SEMILLAS}")
    print(f"num_reads: {NUM_READS}")
    print(f"num_sweeps: {NUM_SWEEPS}")
    print()

    resultados = []

    for nombre, mapa in (
        ("A — 8 candidatas", MAPA_QUBO_A),
        ("B — 9 candidatas", MAPA_QUBO_B),
        ("C — 10 candidatas", MAPA_QUBO_C),
    ):
        resultados.append(ejecutar_instancia(nombre, mapa))

    print("=" * 120)
    print("RESUMEN GLOBAL")
    print("=" * 120)
    print(
        f"{'Instancia':<22}"
        f"{'Vars':>8}"
        f"{'Óptimo':>9}"
        f"{'Éxitos':>10}"
        f"{'Éxito %':>10}"
        f"{'Mejor':>9}"
        f"{'Media':>10}"
        f"{'Peor':>9}"
        f"{'Gap med. %':>12}"
        f"{'Fact. med. %':>13}"
        f"{'t med.':>10}"
    )

    for r in resultados:
        def fmt(valor, dec=2):
            if valor is None:
                return "-"
            return f"{valor:.{dec}f}"

        mejor = "-" if r["mejor_coste"] is None else f"{r['mejor_coste']:g}"
        peor = "-" if r["peor_coste"] is None else f"{r['peor_coste']:g}"

        print(
            f"{r['instancia']:<22}"
            f"{r['variables']:>8}"
            f"{r['optimo']:>9}"
            f"{r['exitos']:>10}"
            f"{r['tasa_exito']:>10.2f}"
            f"{mejor:>9}"
            f"{fmt(r['coste_medio'], 2):>10}"
            f"{peor:>9}"
            f"{fmt(r['gap_medio'], 2):>12}"
            f"{fmt(r['factibilidad_media'], 2):>13}"
            f"{r['tiempo_medio']:>10.4f}"
        )


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = (
        f"robustez_sa_8_9_10_k{K}_"
        f"{NUM_SEMILLAS}semillas_{marca_tiempo}.txt"
    )
    ruta = os.path.join(carpeta_resultados, nombre)

    stdout_original = sys.stdout

    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar_experimento()
            print()
            print("=" * 92)
            print(f"Registro guardado en: {ruta}")
            print("=" * 92)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
