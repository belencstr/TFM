"""Experimento QUBO + Simulated Annealing sobre instancias pequeñas.

Instancias:
    A -> 8 candidatas
    B -> 9 candidatas
    C -> 10 candidatas

En las tres se mantiene k=4 y el mismo problema p-median/k-medoids.

Se compara:
1. PAM (algoritmo clásico principal).
2. Búsqueda exhaustiva (óptimo exacto).
3. QUBO + Simulated Annealing.

La salida se muestra por consola y se guarda automáticamente en un TXT.
"""

import os
import sys
import time
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from mapas.mapa_qubo_a import MAPA_QUBO_A
from mapas.mapa_qubo_b import MAPA_QUBO_B
from mapas.mapa_qubo_c import MAPA_QUBO_C

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
from solvers.simulated_annealing_qubo import resolver_qubo_simulated_annealing


K = 4

# Mantenemos inicialmente los mismos parámetros que en el experimento grande.
# Así la comparación de tamaño es más limpia.
NUM_READS = 100
NUM_SWEEPS = 1000
SEED_BASE = 20260814

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


def mapa_con_monedas(mapa, seleccionadas):
    copia = [list(fila) for fila in mapa]

    for candidata in seleccionadas:
        copia[candidata["fila"]][candidata["columna"]] = "o"

    return "\n".join("".join(fila) for fila in copia)


def coste_pmedian_seguro(matriz, asignacion):
    """Calcula el coste p-median evitando overflow de tipos NumPy."""
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


def muestra_es_binaria(asignacion):
    for valor in asignacion.values():
        if int(valor) not in (0, 1):
            return False
        if float(valor) not in (0.0, 1.0):
            return False

    return True


def analizar_muestras(qubo, matriz, resultado_sa):
    mejor_factible = None
    mejor_energia = None

    lecturas_totales = 0
    lecturas_factibles = 0

    no_binarias = 0
    errores_energia = 0
    errores_factibles = 0

    for muestra in resultado_sa["muestras"]:
        asignacion = muestra["asignacion"]
        ocurrencias = muestra["num_occurrences"]
        lecturas_totales += ocurrencias

        if not muestra_es_binaria(asignacion):
            no_binarias += ocurrencias

        energia_recalculada = float(energia_qubo(qubo, asignacion))
        energia_sampler = float(muestra["energia"])

        if abs(energia_recalculada - energia_sampler) > TOLERANCIA:
            errores_energia += ocurrencias

        factibilidad = comprobar_factibilidad(qubo, asignacion)

        analizada = {
            **muestra,
            "energia_recalculada": energia_recalculada,
            "factibilidad": factibilidad,
            "coste_pmedian": None,
        }

        if (
            mejor_energia is None
            or energia_recalculada < mejor_energia["energia_recalculada"]
        ):
            mejor_energia = analizada

        if not factibilidad["factible"]:
            continue

        lecturas_factibles += ocurrencias
        coste = coste_pmedian_seguro(matriz, asignacion)
        analizada["coste_pmedian"] = coste

        # En una solución factible todas las penalizaciones valen cero.
        if abs(energia_recalculada - float(coste)) > TOLERANCIA:
            errores_factibles += ocurrencias

        if (
            mejor_factible is None
            or float(coste) < float(mejor_factible["coste_pmedian"])
            or (
                float(coste) == float(mejor_factible["coste_pmedian"])
                and energia_recalculada
                < mejor_factible["energia_recalculada"]
            )
        ):
            mejor_factible = analizada

    return {
        "mejor_energia": mejor_energia,
        "mejor_factible": mejor_factible,
        "lecturas_totales": lecturas_totales,
        "lecturas_factibles": lecturas_factibles,
        "tasa_factibilidad": (
            100.0 * lecturas_factibles / lecturas_totales
            if lecturas_totales
            else 0.0
        ),
        "no_binarias": no_binarias,
        "errores_energia": errores_energia,
        "errores_factibles": errores_factibles,
    }


def ejecutar_instancia(nombre, mapa, seed):
    candidatas = obtener_candidatas(mapa)
    grafo = construir_grafo(mapa)
    resumen = resumen_grafo(grafo)
    matriz = construir_matriz_navegable(candidatas, grafo)

    inicio = time.perf_counter()
    pam = k_medoids_pam(candidatas, matriz, K)
    tiempo_pam = time.perf_counter() - inicio

    inicio = time.perf_counter()
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    tiempo_exacto = time.perf_counter() - inicio

    qubo = construir_qubo_pmedian(
        matriz,
        K,
        cota_factible=pam["coste_total"],
    )

    inicio = time.perf_counter()
    resultado_sa = resolver_qubo_simulated_annealing(
        qubo,
        num_reads=NUM_READS,
        num_sweeps=NUM_SWEEPS,
        seed=seed,
    )
    tiempo_sa = time.perf_counter() - inicio

    analisis = analizar_muestras(qubo, matriz, resultado_sa)

    print("=" * 88)
    print(f"INSTANCIA QUBO {nombre}")
    print("=" * 88)
    print(f"Dimensiones: {len(mapa)} x {len(mapa[0])}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"Nodos navegables: {resumen['nodos']}")
    print(f"Aristas: {resumen['aristas']}")
    print(f"Grafo conexo: {resumen['conexo']}")
    print(f"k: {K}")
    print()

    print("REFERENCIAS CLÁSICAS")
    print(f"PAM: {pam['coste_total']} | tiempo: {tiempo_pam:.6f} s")
    print(
        f"Óptimo exhaustivo: {exacta['coste_total']} | "
        f"tiempo: {tiempo_exacto:.6f} s"
    )
    print(
        "PAM alcanza el óptimo: "
        f"{pam['coste_total'] == exacta['coste_total']}"
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
    print(f"Tiempo: {tiempo_sa:.6f} s")
    print(
        f"Lecturas factibles: "
        f"{analisis['lecturas_factibles']}/{analisis['lecturas_totales']}"
    )
    print(f"Tasa de factibilidad: {analisis['tasa_factibilidad']:.2f}%")
    print()

    print("COMPROBACIONES")
    print(f"Lecturas no binarias: {analisis['no_binarias']}")
    print(
        "Discrepancias energía sampler/recalculada: "
        f"{analisis['errores_energia']}"
    )
    print(
        "Factibles con energía != coste p-median: "
        f"{analisis['errores_factibles']}"
    )
    print()

    mejor_factible = analisis["mejor_factible"]

    if mejor_factible is None:
        coste_sa = None
        gap = None
        alcanza_optimo = False
        print("MEJOR SOLUCIÓN FACTIBLE")
        print("No se ha encontrado ninguna solución factible.")
        print()
    else:
        coste_sa = mejor_factible["coste_pmedian"]
        gap = (
            100.0
            * (float(coste_sa) - float(exacta["coste_total"]))
            / float(exacta["coste_total"])
            if exacta["coste_total"] != 0
            else 0.0
        )
        alcanza_optimo = (
            abs(float(coste_sa) - float(exacta["coste_total"]))
            <= TOLERANCIA
        )

        indices = mejor_factible["factibilidad"]["seleccionadas"]
        seleccionadas = [candidatas[j] for j in indices]

        print("MEJOR SOLUCIÓN FACTIBLE DE SA")
        print(f"Coste p-median: {coste_sa}")
        print(f"Energía QUBO: {mejor_factible['energia_recalculada']:.6f}")
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

    coherente = (
        analisis["no_binarias"] == 0
        and analisis["errores_energia"] == 0
        and analisis["errores_factibles"] == 0
    )

    return {
        "mapa": nombre,
        "candidatas": len(candidatas),
        "variables_qubo": qubo["numero_variables"],
        "terminos": qubo["numero_terminos_cuadraticos"],
        "pam": pam["coste_total"],
        "optimo": exacta["coste_total"],
        "sa": coste_sa,
        "gap": gap,
        "factibilidad": analisis["tasa_factibilidad"],
        "tiempo_sa": tiempo_sa,
        "optimo_sa": alcanza_optimo,
        "coherente": coherente,
    }


def ejecutar_experimento():
    print("=" * 88)
    print("CASO 1 — ESCALADO DEL QUBO EN INSTANCIAS PEQUEÑAS")
    print("=" * 88)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Problema: p-median / k-medoids")
    print("Algoritmo clásico: PAM")
    print("Referencia exacta: búsqueda exhaustiva")
    print("Solver QUBO: D-Wave SimulatedAnnealingSampler")
    print(f"k: {K}")
    print(f"num_reads: {NUM_READS}")
    print(f"num_sweeps: {NUM_SWEEPS}")
    print()

    resultados = []

    instancias = (
        ("A — 8 candidatas", MAPA_QUBO_A),
        ("B — 9 candidatas", MAPA_QUBO_B),
        ("C — 10 candidatas", MAPA_QUBO_C),
    )

    for indice, (nombre, mapa) in enumerate(instancias):
        resultados.append(
            ejecutar_instancia(
                nombre,
                mapa,
                seed=SEED_BASE + indice,
            )
        )

    print("=" * 122)
    print("RESUMEN COMPARATIVO")
    print("=" * 122)
    print(
        f"{'Instancia':<22}"
        f"{'Cand.':>7}"
        f"{'Vars':>8}"
        f"{'Térm. Q':>10}"
        f"{'PAM':>7}"
        f"{'Óptimo':>9}"
        f"{'SA':>8}"
        f"{'Gap %':>9}"
        f"{'Fact. %':>10}"
        f"{'t SA':>10}"
        f"{'Óptimo SA':>12}"
    )

    for r in resultados:
        sa_txt = "-" if r["sa"] is None else str(r["sa"])
        gap_txt = "-" if r["gap"] is None else f"{r['gap']:.2f}"

        print(
            f"{r['mapa']:<22}"
            f"{r['candidatas']:>7}"
            f"{r['variables_qubo']:>8}"
            f"{r['terminos']:>10}"
            f"{r['pam']:>7}"
            f"{r['optimo']:>9}"
            f"{sa_txt:>8}"
            f"{gap_txt:>9}"
            f"{r['factibilidad']:>10.2f}"
            f"{r['tiempo_sa']:>10.4f}"
            f"{str(r['optimo_sa']):>12}"
        )


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"qubo_sa_instancias_8_9_10_k{K}_{marca_tiempo}.txt"
    ruta = os.path.join(carpeta_resultados, nombre)

    stdout_original = sys.stdout

    try:
        with open(ruta, "w", encoding="utf-8") as fichero:
            sys.stdout = Tee(stdout_original, fichero)
            ejecutar_experimento()
            print()
            print("=" * 88)
            print(f"Registro guardado en: {ruta}")
            print("=" * 88)
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta}")


if __name__ == "__main__":
    main()
