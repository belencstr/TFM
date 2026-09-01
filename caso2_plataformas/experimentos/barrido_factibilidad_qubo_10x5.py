"""Barrido clásico de factibilidad para la instancia reducida 16x5.

Objetivo:
- reutilizar exactamente la lógica física de la v4;
- comprobar qué longitudes L* son factibles;
- mantener exactamente 2 subidas y 2 bajadas;
- registrar una ruta válida para cada longitud.

Este experimento no es todavía QUBO. Sirve para elegir L* con datos.
"""

import os
import sys
from datetime import datetime

from ortools.sat.python import cp_model

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    ANCHO_PLATAFORMA,
    HUECO_MIN,
    HUECO_MAX,
    SUBIDA_MAX,
    CAIDA_MAX,
    obtener_anclas_candidatas,
    construir_grafo_segmentos_v4,
    contar_aristas,
)

ANCHO = 16
ALTO = 5
START = (0, 2)
GOAL = (15, 2)

LONGITUDES = [4, 5, 6]
SUBIDAS_EXACTAS = 2
BAJADAS_EXACTAS = 2
MAX_TIEMPO = 30.0
SEED = 20260825


def resolver_longitud(grafo, longitud):
    model = cp_model.CpModel()
    nodos = list(grafo.keys())

    z = {}
    entradas = {n: [] for n in nodos}
    salidas = {n: [] for n in nodos}

    for o, destinos in grafo.items():
        for d in destinos:
            var = model.NewBoolVar(
                f"z_{o[0]}_{o[1]}__{d[0]}_{d[1]}"
            )
            z[(o, d)] = var
            salidas[o].append(var)
            entradas[d].append(var)

    # START: exactamente una salida.
    model.Add(sum(salidas[START]) == 1)
    if entradas[START]:
        model.Add(sum(entradas[START]) == 0)

    # GOAL: exactamente una entrada.
    model.Add(sum(entradas[GOAL]) == 1)
    if salidas[GOAL]:
        model.Add(sum(salidas[GOAL]) == 0)

    # Conservación de flujo.
    for n in nodos:
        if n in (START, GOAL):
            continue
        model.Add(sum(entradas[n]) == sum(salidas[n]))
        model.Add(sum(entradas[n]) <= 1)
        model.Add(sum(salidas[n]) <= 1)

    # Longitud exacta L*.
    model.Add(sum(z.values()) == longitud)

    # Exactamente 2 subidas y 2 bajadas.
    subidas = []
    bajadas = []

    for (o, d), var in z.items():
        dy = d[1] - o[1]
        if dy > 0:
            subidas.append(var)
        elif dy < 0:
            bajadas.append(var)

    model.Add(sum(subidas) == SUBIDAS_EXACTAS)
    model.Add(sum(bajadas) == BAJADAS_EXACTAS)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = MAX_TIEMPO
    solver.parameters.random_seed = SEED
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": solver.StatusName(status),
            "ruta": None,
            "tiempo": solver.WallTime(),
        }

    saltos = [
        (o, d)
        for (o, d), var in z.items()
        if solver.Value(var) == 1
    ]

    siguiente = {o: d for o, d in saltos}

    ruta = [START]
    actual = START

    while actual != GOAL:
        if actual not in siguiente:
            raise RuntimeError(
                "La solución cumple flujo pero no se puede reconstruir "
                "como ruta START->GOAL."
            )
        actual = siguiente[actual]
        ruta.append(actual)

    planos = 0
    for o, d in saltos:
        if d[1] == o[1]:
            planos += 1

    return {
        "status": solver.StatusName(status),
        "ruta": ruta,
        "saltos": saltos,
        "planos": planos,
        "tiempo": solver.WallTime(),
    }


def main():
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

    print("=" * 82)
    print("CASO 2 — BARRIDO CLÁSICO DE FACTIBILIDAD PARA QUBO")
    print("=" * 82)
    print(f"Mapa reducido: {ANCHO} x {ALTO}")
    print(f"START: {START}")
    print(f"GOAL: {GOAL}")
    print(f"Ancho plataforma: {ANCHO_PLATAFORMA}")
    print(f"Hueco permitido: {HUECO_MIN} .. {HUECO_MAX}")
    print(f"Subida máxima: {SUBIDA_MAX}")
    print(f"Caída máxima: {CAIDA_MAX}")
    print(f"Candidatas: {len(candidatas)}")
    print(f"Variables QUBO previstas = |E| = {contar_aristas(grafo)}")
    print()

    for longitud in LONGITUDES:
        resultado = resolver_longitud(
            grafo,
            longitud,
        )

        print("-" * 82)
        print(f"L* = {longitud}")
        print(f"Estado: {resultado['status']}")
        print(f"Tiempo: {resultado['tiempo']:.4f} s")

        if resultado["ruta"] is None:
            print("Factible: NO")
            continue

        print("Factible: SÍ")
        print(f"Planos: {resultado['planos']}")
        print("Ruta:")
        print(
            " -> ".join(
                str(p)
                for p in resultado["ruta"]
            )
        )

    print("-" * 82)


if __name__ == "__main__":
    carpeta = os.path.join(
        RAIZ,
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
        f"caso2_barrido_Lstar_16x5_{marca}.txt",
    )

    stdout_original = sys.stdout

    class Tee:
        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            for s in self.streams:
                s.write(data)
                s.flush()

        def flush(self):
            for s in self.streams:
                s.flush()

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
            main()
            print()
            print(f"Registro guardado en: {ruta_txt}")
    finally:
        sys.stdout = stdout_original

    print(f"\nTXT generado correctamente: {ruta_txt}")