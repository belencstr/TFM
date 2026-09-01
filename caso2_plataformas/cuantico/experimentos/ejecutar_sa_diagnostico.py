"""Diagnóstico inicial con Simulated Annealing para el QUBO del Caso 2.

Objetivo:
- probar inicialmente A=B=C=D=E=F=1;
- ejecutar 100 lecturas;
- medir energía y factibilidad;
- inspeccionar la mejor muestra;
- reconstruir la ruta si es posible;
- usar BFS para detectar atajos.

Este experimento es diagnóstico. No constituye todavía el ensayo final
de robustez.
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
    calcular_hueco,
    contar_aristas,
)

from cuantico.formulacion.qubo_caso2_18x5 import (
    ANCHO,
    ALTO,
    START,
    GOAL,
    L_OBJETIVO,
    SUBIDAS_OBJETIVO,
    BAJADAS_OBJETIVO,
    construir_qubo,
    energia_qubo,
    evaluar_restricciones,
)

from cuantico.solvers.simulated_annealing import (
    resolver_qubo_sa,
)


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


def aristas_activas(muestra):
    return [
        arista
        for arista, valor in muestra.items()
        if int(valor) == 1
    ]


def reconstruir_ruta(muestra):
    """Intenta reconstruir START -> GOAL a partir de las aristas activas."""
    activas = aristas_activas(muestra)

    siguientes = {}

    for origen, destino in activas:
        siguientes.setdefault(origen, []).append(destino)

    ruta = [START]
    actual = START
    visitados = {START}

    while actual != GOAL:
        candidatos = siguientes.get(actual, [])

        if len(candidatos) != 1:
            return None

        actual = candidatos[0]

        if actual in visitados:
            return None

        ruta.append(actual)
        visitados.add(actual)

        if len(ruta) > L_OBJETIVO + 2:
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


def construir_subgrafo_inducido(grafo, nodos):
    nodos = set(nodos)

    return {
        origen: [
            destino
            for destino in grafo.get(origen, [])
            if destino in nodos
        ]
        for origen in nodos
    }


def max_planos_consecutivos(ruta):
    if not ruta or len(ruta) < 2:
        return None

    actual = 0
    maximo = 0

    for origen, destino in zip(
        ruta[:-1],
        ruta[1:],
    ):
        if destino[1] == origen[1]:
            actual += 1
            maximo = max(maximo, actual)
        else:
            actual = 0

    return maximo


def analizar_muestra(grafo, qubo, offset, muestra):
    evaluacion = evaluar_restricciones(
        grafo,
        muestra,
    )

    energia = energia_qubo(
        qubo,
        offset,
        muestra,
    )

    ruta = reconstruir_ruta(muestra)

    resultado = {
        "energia": energia,
        "evaluacion": evaluacion,
        "ruta": ruta,
        "bfs": None,
        "delta_L": None,
        "max_planos_consecutivos": None,
        "huecos": None,
    }

    if ruta is None:
        return resultado

    nodos_ruta = set(ruta)
    subgrafo = construir_subgrafo_inducido(
        grafo,
        nodos_ruta,
    )

    camino_bfs = bfs(
        subgrafo,
        START,
        GOAL,
    )

    resultado["bfs"] = camino_bfs

    if camino_bfs is not None:
        L_qubo = len(ruta) - 1
        L_bfs = len(camino_bfs) - 1
        resultado["delta_L"] = L_qubo - L_bfs

    resultado["max_planos_consecutivos"] = (
        max_planos_consecutivos(ruta)
    )

    resultado["huecos"] = [
        calcular_hueco(
            o,
            d,
            START,
            GOAL,
        )
        for o, d in zip(
            ruta[:-1],
            ruta[1:],
        )
    ]

    return resultado


def ejecutar():
    candidatas = obtener_anclas_candidatas(
        ANCHO,
        ALTO,
        START,
        GOAL,
    )

    posiciones = [START] + candidatas + [GOAL]

    grafo = construir_grafo_segmentos_v4(
        posiciones,
        START,
        GOAL,
    )

    qubo, offset = construir_qubo(grafo)

    print("=" * 92)
    print("CASO 2 — DIAGNÓSTICO SIMULATED ANNEALING")
    print("=" * 92)
    print(f"Mapa: {ANCHO} x {ALTO}")
    print(f"Variables QUBO = |E| = {contar_aristas(grafo)}")
    print(f"Términos QUBO no nulos: {len(qubo)}")
    print(f"L*: {L_OBJETIVO}")
    print(f"Subidas objetivo: {SUBIDAS_OBJETIVO}")
    print(f"Bajadas objetivo: {BAJADAS_OBJETIVO}")
    print(f"num_reads: {NUM_READS}")
    print(f"num_sweeps: {NUM_SWEEPS}")
    print(f"seed: {SEED}")
    print()

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
        analisis = analizar_muestra(
            grafo,
            qubo,
            offset,
            muestra,
        )

        for _ in range(int(datum.num_occurrences)):
            registros.append(analisis)

    registros.sort(
        key=lambda r: r["energia"]
    )

    factibles = [
        r
        for r in registros
        if r["evaluacion"]["factible_qubo"]
    ]

    print("Resumen:")
    print(f"  Lecturas totales: {len(registros)}")
    print(f"  Energía mínima real: {registros[0]['energia']:.6f}")
    print(f"  Energía máxima real: {registros[-1]['energia']:.6f}")
    print(
        f"  Muestras factibles QUBO: "
        f"{len(factibles)}/{len(registros)} "
        f"({100.0*len(factibles)/len(registros):.2f}%)"
    )
    print()

    mejor = registros[0]
    ev = mejor["evaluacion"]

    print("Mejor muestra:")
    print(f"  Energía: {mejor['energia']:.6f}")
    print(f"  Factible QUBO: {ev['factible_qubo']}")
    print(f"  Salidas START: {ev['salida_start']}")
    print(f"  Entradas GOAL: {ev['entrada_goal']}")
    print(f"  Saltos activos: {ev['numero_saltos']}")
    print(f"  Subidas: {ev['numero_subidas']}")
    print(f"  Bajadas: {ev['numero_bajadas']}")
    print(f"  Planos: {ev['numero_planos']}")
    print(f"  Violaciones flujo: {len(ev['violaciones_flujo'])}")
    print()

    print("Penalizaciones de la mejor muestra:")
    print(f"  Inicio: {ev['penalizacion_inicio']}")
    print(f"  Meta: {ev['penalizacion_meta']}")
    print(f"  Flujo: {ev['penalizacion_flujo']}")
    print(f"  Longitud: {ev['penalizacion_longitud']}")
    print(f"  Subidas: {ev['penalizacion_subidas']}")
    print(f"  Bajadas: {ev['penalizacion_bajadas']}")
    print()

    if mejor["ruta"] is None:
        print("No se puede reconstruir una ruta única START -> GOAL.")
    else:
        print("Ruta reconstruida:")
        print(
            " -> ".join(
                str(p)
                for p in mejor["ruta"]
            )
        )
        print()

        if mejor["bfs"] is not None:
            print(
                f"Longitud ruta QUBO: "
                f"{len(mejor['ruta']) - 1}"
            )
            print(
                f"Longitud mínima BFS: "
                f"{len(mejor['bfs']) - 1}"
            )
            print(
                f"Delta L (QUBO - BFS): "
                f"{mejor['delta_L']}"
            )
        else:
            print("BFS no encuentra camino en el subgrafo inducido.")

        print(
            f"Máximo de planos consecutivos: "
            f"{mejor['max_planos_consecutivos']}"
        )
        print(
            f"Huecos de la ruta: "
            f"{mejor['huecos']}"
        )

    print()
    print("Factibilidad por restricción (sobre todas las lecturas):")

    checks = {
        "START": lambda e: e["salida_start"] == 1,
        "GOAL": lambda e: e["entrada_goal"] == 1,
        "Flujo": lambda e: len(e["violaciones_flujo"]) == 0,
        "Longitud": lambda e: e["numero_saltos"] == L_OBJETIVO,
        "Subidas": lambda e: e["numero_subidas"] == SUBIDAS_OBJETIVO,
        "Bajadas": lambda e: e["numero_bajadas"] == BAJADAS_OBJETIVO,
    }

    for nombre, condicion in checks.items():
        ok = sum(
            1
            for r in registros
            if condicion(r["evaluacion"])
        )

        print(
            f"  {nombre}: "
            f"{ok}/{len(registros)} "
            f"({100.0*ok/len(registros):.2f}%)"
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
        f"diagnostico_sa_"
        f"{ANCHO}x{ALTO}_"
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