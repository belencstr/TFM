"""Barrido del peso C de conservación de flujo en el QUBO del Caso 2.

Se mantienen:
    A = B = D = E = F = 1

Se prueban:
    C in {1, 2, 5, 10}

Para cada valor se ejecuta Simulated Annealing con:
    num_reads = 100
    num_sweeps = 1000
    seed = 20260826

Se registra:
- energía mínima;
- porcentaje de muestras totalmente factibles;
- cumplimiento individual de cada restricción;
- número de soluciones factibles sin atajos (Delta L = 0);
- número de soluciones factibles con atajo (Delta L > 0).
"""

import os
import sys
from collections import deque
from datetime import datetime

RAIZ = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    obtener_anclas_candidatas,
    construir_grafo_segmentos_v4,
    contar_aristas,
)

import cuantico.formulacion.qubo as qmod

from cuantico.solvers.simulated_annealing import (
    resolver_qubo_sa,
)


VALORES_C = [1.0, 2.0, 5.0, 10.0]
NUM_READS = 100
NUM_SWEEPS = 1000
SEED = 20260826


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


def muestra_dict(sample):
    return {
        variable: int(valor)
        for variable, valor in sample.items()
    }


def reconstruir_ruta(muestra):
    activas = [
        arista
        for arista, valor in muestra.items()
        if int(valor) == 1
    ]

    siguientes = {}

    for origen, destino in activas:
        siguientes.setdefault(origen, []).append(destino)

    ruta = [qmod.START]
    actual = qmod.START
    visitados = {qmod.START}

    while actual != qmod.GOAL:
        candidatos = siguientes.get(actual, [])

        if len(candidatos) != 1:
            return None

        actual = candidatos[0]

        if actual in visitados:
            return None

        ruta.append(actual)
        visitados.add(actual)

        if len(ruta) > qmod.L_OBJETIVO + 2:
            return None

    return ruta


def bfs(grafo, inicio, meta):
    cola = deque([inicio])
    anterior = {inicio: None}

    while cola:
        actual = cola.popleft()

        if actual == meta:
            break

        for sig in grafo.get(actual, []):
            if sig not in anterior:
                anterior[sig] = actual
                cola.append(sig)

    if meta not in anterior:
        return None

    camino = []
    actual = meta

    while actual is not None:
        camino.append(actual)
        actual = anterior[actual]

    return list(reversed(camino))


def delta_l_para_muestra(grafo, muestra):
    ruta = reconstruir_ruta(muestra)

    if ruta is None:
        return None

    nodos = set(ruta)

    subgrafo = {
        origen: [
            destino
            for destino in grafo.get(origen, [])
            if destino in nodos
        ]
        for origen in nodos
    }

    camino_bfs = bfs(
        subgrafo,
        qmod.START,
        qmod.GOAL,
    )

    if camino_bfs is None:
        return None

    return (
        len(ruta) - 1
        - (len(camino_bfs) - 1)
    )


def construir_grafo():
    candidatas = obtener_anclas_candidatas(
        qmod.ANCHO,
        qmod.ALTO,
        qmod.START,
        qmod.GOAL,
    )

    posiciones = [
        qmod.START,
        *candidatas,
        qmod.GOAL,
    ]

    grafo = construir_grafo_segmentos_v4(
        posiciones,
        qmod.START,
        qmod.GOAL,
    )

    return grafo


def ejecutar_valor_c(grafo, valor_c):
    qmod.C = float(valor_c)

    qubo, offset = qmod.construir_qubo(
        grafo
    )

    sampleset = resolver_qubo_sa(
        qubo,
        num_reads=NUM_READS,
        num_sweeps=NUM_SWEEPS,
        seed=SEED,
    )

    registros = []

    for datum in sampleset.data(
        fields=["sample", "energy", "num_occurrences"]
    ):
        muestra = muestra_dict(datum.sample)

        evaluacion = qmod.evaluar_restricciones(
            grafo,
            muestra,
        )

        energia_real = qmod.energia_qubo(
            qubo,
            offset,
            muestra,
        )

        delta_l = None

        if evaluacion["factible_qubo"]:
            delta_l = delta_l_para_muestra(
                grafo,
                muestra,
            )

        for _ in range(int(datum.num_occurrences)):
            registros.append(
                {
                    "energia": energia_real,
                    "evaluacion": evaluacion,
                    "delta_l": delta_l,
                }
            )

    registros.sort(
        key=lambda r: r["energia"]
    )

    total = len(registros)

    factibles = [
        r
        for r in registros
        if r["evaluacion"]["factible_qubo"]
    ]

    def porcentaje(condicion):
        ok = sum(
            1
            for r in registros
            if condicion(r["evaluacion"])
        )

        return ok, 100.0 * ok / total

    restricciones = {
        "START": porcentaje(
            lambda e: e["salida_start"] == 1
        ),
        "GOAL": porcentaje(
            lambda e: e["entrada_goal"] == 1
        ),
        "Flujo": porcentaje(
            lambda e: len(e["violaciones_flujo"]) == 0
        ),
        "Longitud": porcentaje(
            lambda e: e["numero_saltos"] == qmod.L_OBJETIVO
        ),
        "Subidas": porcentaje(
            lambda e: e["numero_subidas"] == qmod.SUBIDAS_OBJETIVO
        ),
        "Bajadas": porcentaje(
            lambda e: e["numero_bajadas"] == qmod.BAJADAS_OBJETIVO
        ),
    }

    sin_atajo = sum(
        1
        for r in factibles
        if r["delta_l"] == 0
    )

    con_atajo = sum(
        1
        for r in factibles
        if (
            r["delta_l"] is not None
            and r["delta_l"] > 0
        )
    )

    no_evaluable = sum(
        1
        for r in factibles
        if r["delta_l"] is None
    )

    return {
        "C": valor_c,
        "terminos_qubo": len(qubo),
        "offset": offset,
        "energia_min": registros[0]["energia"],
        "energia_max": registros[-1]["energia"],
        "factibles": len(factibles),
        "factibilidad_pct": (
            100.0 * len(factibles) / total
        ),
        "restricciones": restricciones,
        "sin_atajo": sin_atajo,
        "con_atajo": con_atajo,
        "no_evaluable": no_evaluable,
    }


def ejecutar():
    grafo = construir_grafo()

    print("=" * 100)
    print("CASO 2 — BARRIDO DEL PESO C DE CONSERVACIÓN DE FLUJO")
    print("=" * 100)
    print(
        f"Mapa: {qmod.ANCHO} x {qmod.ALTO}"
    )
    print(
        f"Variables QUBO = |E| = "
        f"{contar_aristas(grafo)}"
    )
    print(
        f"L*: {qmod.L_OBJETIVO}"
    )
    print(
        f"Subidas objetivo: "
        f"{qmod.SUBIDAS_OBJETIVO}"
    )
    print(
        f"Bajadas objetivo: "
        f"{qmod.BAJADAS_OBJETIVO}"
    )
    print(
        f"A=B=D=E=F=1"
    )
    print(
        f"C probados: {VALORES_C}"
    )
    print(
        f"num_reads={NUM_READS}, "
        f"num_sweeps={NUM_SWEEPS}, "
        f"seed={SEED}"
    )
    print()

    resultados = []

    for valor_c in VALORES_C:
        print("-" * 100)
        print(f"Ejecutando C = {valor_c} ...")

        resultado = ejecutar_valor_c(
            grafo,
            valor_c,
        )

        resultados.append(resultado)

        print(
            f"Energía mínima: "
            f"{resultado['energia_min']:.6f}"
        )
        print(
            f"Factibilidad total: "
            f"{resultado['factibles']}/{NUM_READS} "
            f"({resultado['factibilidad_pct']:.2f}%)"
        )

        for nombre, (ok, pct) in (
            resultado["restricciones"].items()
        ):
            print(
                f"  {nombre}: "
                f"{ok}/{NUM_READS} "
                f"({pct:.2f}%)"
            )

        print(
            f"  Factibles sin atajo: "
            f"{resultado['sin_atajo']}"
        )
        print(
            f"  Factibles con atajo: "
            f"{resultado['con_atajo']}"
        )
        print(
            f"  Factibles no evaluables BFS: "
            f"{resultado['no_evaluable']}"
        )

    print()
    print("=" * 100)
    print("RESUMEN COMPARATIVO")
    print("=" * 100)

    encabezado = (
        f"{'C':>6} | "
        f"{'Fact.%':>8} | "
        f"{'START':>7} | "
        f"{'GOAL':>7} | "
        f"{'Flujo':>7} | "
        f"{'Long.':>7} | "
        f"{'Sub.':>7} | "
        f"{'Baj.':>7} | "
        f"{'sin atajo':>10} | "
        f"{'con atajo':>10}"
    )

    print(encabezado)
    print("-" * len(encabezado))

    for r in resultados:
        restr = r["restricciones"]

        print(
            f"{r['C']:>6.1f} | "
            f"{r['factibilidad_pct']:>8.2f} | "
            f"{restr['START'][1]:>7.2f} | "
            f"{restr['GOAL'][1]:>7.2f} | "
            f"{restr['Flujo'][1]:>7.2f} | "
            f"{restr['Longitud'][1]:>7.2f} | "
            f"{restr['Subidas'][1]:>7.2f} | "
            f"{restr['Bajadas'][1]:>7.2f} | "
            f"{r['sin_atajo']:>10} | "
            f"{r['con_atajo']:>10}"
        )


def main():
    carpeta = os.path.join(
        RAIZ,
        "cuantico",
        "resultados",
    )
    os.makedirs(
        carpeta,
        exist_ok=True,
    )

    marca = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    ruta_txt = os.path.join(
        carpeta,
        f"barrido_C_flujo_"
        f"{qmod.ANCHO}x{qmod.ALTO}_"
        f"{NUM_READS}reads_"
        f"{NUM_SWEEPS}sweeps_"
        f"{marca}.txt",
    )

    stdout_original = sys.stdout

    try:
        with open(
            ruta_txt,
            "w",
            encoding="utf-8",
        ) as f:
            sys.stdout = Tee(
                stdout_original,
                f,
            )

            ejecutar()

            print()
            print(
                f"Registro guardado en: "
                f"{ruta_txt}"
            )
    finally:
        sys.stdout = stdout_original

    print(
        f"\nTXT generado correctamente: "
        f"{ruta_txt}"
    )


if __name__ == "__main__":
    main()
