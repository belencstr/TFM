"""Versión 2 del experimento QUBO p-median + Simulated Annealing.

Cambios respecto a v1:
- Mantiene intacto el experimento anterior.
- Evita overflow numérico al calcular el coste p-median, convirtiendo
  explícitamente distancias y bits a tipos Python.
- Comprueba que todas las distancias sean no negativas.
- Comprueba que las muestras sean binarias.
- Recalcula la energía QUBO con la función propia `energia_qubo`.
- Verifica que la energía de D-Wave y la energía recalculada coincidan.
- Para muestras factibles, verifica que:
      energía QUBO == coste p-median
  porque todas las penalizaciones deben ser cero.
- Guarda automáticamente un TXT independiente con sufijo `_v2`.
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
    energia_qubo,
    nombre_y,
)

from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo
from solvers.simulated_annealing_qubo import resolver_qubo_simulated_annealing


K = 4

NUM_READS = 100
NUM_SWEEPS = 1000
SEED_BASE = 12345

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


def mapa_con_monedas(mapa, candidatas_seleccionadas):
    copia = [list(fila) for fila in mapa]

    for candidata in candidatas_seleccionadas:
        copia[candidata["fila"]][candidata["columna"]] = "o"

    return "\n".join("".join(fila) for fila in copia)


def validar_matriz_distancias(matriz):
    """Comprueba estructura y rango de la matriz de distancias."""
    n = len(matriz)

    if n == 0:
        raise ValueError("La matriz de distancias está vacía.")

    if any(len(fila) != n for fila in matriz):
        raise ValueError("La matriz de distancias no es cuadrada.")

    valores = [
        float(matriz[i][j])
        for i in range(n)
        for j in range(n)
    ]

    minimo = min(valores)
    maximo = max(valores)

    if minimo < 0:
        raise ValueError(
            f"Se ha encontrado una distancia negativa: mínimo={minimo}"
        )

    return {
        "n": n,
        "minimo": minimo,
        "maximo": maximo,
        "tipo_elemento": type(matriz[0][0]).__name__,
    }


def asignacion_es_binaria(asignacion):
    """Comprueba que todas las variables de una muestra sean 0 o 1."""
    invalidas = {
        nombre: valor
        for nombre, valor in asignacion.items()
        if int(valor) not in (0, 1) or float(valor) not in (0.0, 1.0)
    }

    return len(invalidas) == 0, invalidas


def coste_pmedian_seguro(matriz_distancias, asignacion):
    """Calcula sum d_ij*y_ij evitando overflow de enteros NumPy.

    La conversión explícita a float/int evita que una suma válida como 150
    se desborde, por ejemplo, a -106 si interviene un entero de 8 bits.
    """
    n = len(matriz_distancias)
    coste = 0.0

    for i in range(n):
        for j in range(n):
            distancia = float(matriz_distancias[i][j])
            bit = int(asignacion.get(nombre_y(i, j), 0))
            coste += distancia * bit

    # Las distancias actuales son enteras. Devolvemos int cuando procede
    # para que la salida del experimento sea más legible.
    if abs(coste - round(coste)) <= TOLERANCIA:
        return int(round(coste))

    return coste


def analizar_muestras(qubo, matriz, resultado_sa):
    """Analiza muestras y realiza comprobaciones internas de coherencia."""
    mejor_factible = None

    lecturas_factibles = 0
    lecturas_totales = 0

    muestras_no_binarias = 0
    discrepancias_energia = 0
    discrepancias_factibles = 0

    muestras_analizadas = []

    for muestra in resultado_sa["muestras"]:
        asignacion = muestra["asignacion"]
        ocurrencias = muestra["num_occurrences"]
        lecturas_totales += ocurrencias

        # 1) Comprobación de dominio binario.
        es_binaria, invalidas = asignacion_es_binaria(asignacion)
        if not es_binaria:
            muestras_no_binarias += ocurrencias

        # 2) Energía recalculada independientemente.
        energia_recalculada = float(energia_qubo(qubo, asignacion))
        energia_sampler = float(muestra["energia"])
        diferencia_energia = abs(energia_sampler - energia_recalculada)
        energia_coherente = diferencia_energia <= TOLERANCIA

        if not energia_coherente:
            discrepancias_energia += ocurrencias

        # 3) Factibilidad.
        factibilidad = comprobar_factibilidad(qubo, asignacion)

        coste = None
        energia_igual_coste = None

        if factibilidad["factible"]:
            lecturas_factibles += ocurrencias

            # 4) Coste original calculado con tipos seguros.
            coste = coste_pmedian_seguro(matriz, asignacion)

            # Para una muestra factible, todas las penalizaciones son 0.
            energia_igual_coste = (
                abs(energia_recalculada - float(coste)) <= TOLERANCIA
            )

            if not energia_igual_coste:
                discrepancias_factibles += ocurrencias

            candidato = {
                **muestra,
                "energia_recalculada": energia_recalculada,
                "diferencia_energia": diferencia_energia,
                "energia_coherente": energia_coherente,
                "factibilidad": factibilidad,
                "coste_pmedian": coste,
                "energia_igual_coste": energia_igual_coste,
            }

            if (
                mejor_factible is None
                or float(coste) < float(mejor_factible["coste_pmedian"])
                or (
                    float(coste) == float(mejor_factible["coste_pmedian"])
                    and energia_recalculada
                    < mejor_factible["energia_recalculada"]
                )
            ):
                mejor_factible = candidato

        muestras_analizadas.append(
            {
                **muestra,
                "energia_recalculada": energia_recalculada,
                "diferencia_energia": diferencia_energia,
                "energia_coherente": energia_coherente,
                "factibilidad": factibilidad,
                "coste_pmedian": coste,
                "energia_igual_coste": energia_igual_coste,
                "es_binaria": es_binaria,
                "variables_invalidas": invalidas,
            }
        )

    # Ordenamos por la energía realmente recalculada.
    muestras_analizadas.sort(key=lambda m: m["energia_recalculada"])
    mejor_energia = muestras_analizadas[0]

    return {
        "mejor_energia": mejor_energia,
        "mejor_factible": mejor_factible,
        "lecturas_factibles": lecturas_factibles,
        "lecturas_totales": lecturas_totales,
        "tasa_factibilidad": (
            100.0 * lecturas_factibles / lecturas_totales
            if lecturas_totales
            else 0.0
        ),
        "muestras_no_binarias": muestras_no_binarias,
        "discrepancias_energia": discrepancias_energia,
        "discrepancias_factibles": discrepancias_factibles,
    }


def ejecutar_mapa(nombre, mapa, seed):
    candidatas = obtener_candidatas(mapa)
    grafo = construir_grafo(mapa)
    matriz = construir_matriz_navegable(candidatas, grafo)

    diagnostico_matriz = validar_matriz_distancias(matriz)

    # ------------------------------------------------------------
    # Referencias clásicas
    # ------------------------------------------------------------
    inicio = time.perf_counter()
    pam = k_medoids_pam(candidatas, matriz, K)
    tiempo_pam = time.perf_counter() - inicio

    inicio = time.perf_counter()
    exacta = k_medoids_exhaustivo(candidatas, matriz, K)
    tiempo_exacto = time.perf_counter() - inicio

    # P = coste PAM + 1, igual que en v1.
    qubo = construir_qubo_pmedian(
        matriz,
        K,
        cota_factible=pam["coste_total"],
    )

    # ------------------------------------------------------------
    # Simulated Annealing
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

    print("=" * 88)
    print(f"CASO 1 — QUBO + SIMULATED ANNEALING V2 — MAPA {nombre}")
    print("=" * 88)
    print(f"Dimensiones: {len(mapa)} x {len(mapa[0])}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"k: {K}")
    print("Distancia: navegable")
    print()

    print("DIAGNÓSTICO DE LA MATRIZ")
    print(f"Tipo de un elemento: {diagnostico_matriz['tipo_elemento']}")
    print(f"Distancia mínima: {diagnostico_matriz['minimo']}")
    print(f"Distancia máxima: {diagnostico_matriz['maximo']}")
    print("Todas las distancias son no negativas: True")
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

    print("COMPROBACIONES INTERNAS")
    print(f"Lecturas no binarias: {analisis['muestras_no_binarias']}")
    print(
        "Lecturas con discrepancia energía sampler/recalculada: "
        f"{analisis['discrepancias_energia']}"
    )
    print(
        "Lecturas factibles con energía != coste p-median: "
        f"{analisis['discrepancias_factibles']}"
    )
    print()

    mejor_energia = analisis["mejor_energia"]

    print("MEJOR ENERGÍA ENCONTRADA")
    print(f"Energía informada por sampler: {mejor_energia['energia']:.6f}")
    print(
        f"Energía recalculada: "
        f"{mejor_energia['energia_recalculada']:.6f}"
    )
    print(
        f"Diferencia absoluta: "
        f"{mejor_energia['diferencia_energia']:.12f}"
    )
    print(f"Energía coherente: {mejor_energia['energia_coherente']}")
    print(f"Factible: {mejor_energia['factibilidad']['factible']}")
    print(
        "Número de monedas x=1: "
        f"{len(mejor_energia['factibilidad']['seleccionadas'])}"
    )

    if mejor_energia["coste_pmedian"] is not None:
        print(f"Coste p-median seguro: {mejor_energia['coste_pmedian']}")
        print(
            "Energía = coste para muestra factible: "
            f"{mejor_energia['energia_igual_coste']}"
        )
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

        print("MEJOR SOLUCIÓN FACTIBLE")
        print(f"Energía QUBO: {mejor_factible['energia_recalculada']:.6f}")
        print(f"Coste p-median seguro: {coste_sa}")
        print(
            "Energía = coste p-median: "
            f"{mejor_factible['energia_igual_coste']}"
        )
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

    # Si una de estas comprobaciones falla, el experimento queda marcado
    # explícitamente como inconsistente.
    experimento_coherente = (
        analisis["muestras_no_binarias"] == 0
        and analisis["discrepancias_energia"] == 0
        and analisis["discrepancias_factibles"] == 0
    )

    print("ESTADO DE COHERENCIA DEL EXPERIMENTO")
    print(f"Experimento internamente coherente: {experimento_coherente}")
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
        "coherente": experimento_coherente,
    }


def ejecutar_experimento():
    print("=" * 88)
    print("REGISTRO — QUBO P-MEDIAN + SIMULATED ANNEALING — V2")
    print("=" * 88)
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Problema: k-medoids / p-median")
    print("Solver QUBO: D-Wave SimulatedAnnealingSampler")
    print("Versión: 2")
    print("Corrección principal: cálculo seguro del coste para evitar overflow")
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

    print("=" * 116)
    print("RESUMEN COMPARATIVO")
    print("=" * 116)
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
        f"{'Coherente':>12}"
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
            f"{str(r['coherente']):>12}"
        )


def main():
    carpeta_resultados = os.path.join(RAIZ, "resultados")
    os.makedirs(carpeta_resultados, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"qubo_sa_mapas_reducidos_k{K}_v2_{marca_tiempo}.txt"
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
