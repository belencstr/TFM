"""Generador constraint-based del Caso 2 mediante OR-Tools CP-SAT.

El modelo selecciona una única ruta START -> GOAL sobre el grafo de saltos posibles.

Variables:
    z_(u,v) = 1 si el salto dirigido u -> v forma parte de la ruta.

Como el grafo solo permite avanzar hacia la derecha, es acíclico. Las restricciones
de flujo generan por tanto una ruta simple START -> GOAL.

Restricciones actuales:
- existe una única ruta START -> GOAL;
- número de saltos dentro de un intervalo;
- al menos un número mínimo de subidas;
- al menos un número mínimo de bajadas;
- no se permiten tres saltos horizontales consecutivos.

Esta primera versión genera únicamente el recorrido principal.
"""

from ortools.sat.python import cp_model


def generar_ruta_cpsat(
    grafo,
    inicio,
    meta,
    min_saltos=11,
    max_saltos=14,
    min_subidas=2,
    min_bajadas=2,
    max_tiempo=30.0,
    seed=20260816,
):
    model = cp_model.CpModel()

    # ------------------------------------------------------------
    # Variables de arista
    # ------------------------------------------------------------
    z = {}

    for origen, destinos in grafo.items():
        for destino in destinos:
            z[(origen, destino)] = model.NewBoolVar(
                f"z_{origen[0]}_{origen[1]}__{destino[0]}_{destino[1]}"
            )

    entradas = {nodo: [] for nodo in grafo}
    salidas = {nodo: [] for nodo in grafo}

    for (origen, destino), variable in z.items():
        salidas[origen].append(variable)
        entradas[destino].append(variable)

    # ------------------------------------------------------------
    # Conservación de flujo
    # ------------------------------------------------------------
    # START: exactamente una salida y ninguna entrada.
    model.Add(sum(salidas[inicio]) == 1)
    if entradas[inicio]:
        model.Add(sum(entradas[inicio]) == 0)

    # GOAL: exactamente una entrada y ninguna salida.
    model.Add(sum(entradas[meta]) == 1)
    if salidas[meta]:
        model.Add(sum(salidas[meta]) == 0)

    # Nodos intermedios:
    # si participan en la ruta tienen exactamente una entrada y una salida.
    for nodo in grafo:
        if nodo in (inicio, meta):
            continue

        suma_entrada = sum(entradas[nodo])
        suma_salida = sum(salidas[nodo])

        model.Add(suma_entrada == suma_salida)
        model.Add(suma_entrada <= 1)
        model.Add(suma_salida <= 1)

    # ------------------------------------------------------------
    # Longitud de la ruta
    # ------------------------------------------------------------
    numero_saltos = sum(z.values())

    model.Add(numero_saltos >= min_saltos)
    model.Add(numero_saltos <= max_saltos)

    # ------------------------------------------------------------
    # Variación vertical
    # ------------------------------------------------------------
    aristas_subida = []
    aristas_bajada = []
    aristas_planas = set()

    for (origen, destino), variable in z.items():
        dy = destino[1] - origen[1]

        if dy > 0:
            aristas_subida.append(variable)
        elif dy < 0:
            aristas_bajada.append(variable)
        else:
            aristas_planas.add((origen, destino))

    model.Add(sum(aristas_subida) >= min_subidas)
    model.Add(sum(aristas_bajada) >= min_bajadas)

    # ------------------------------------------------------------
    # Evitar tres saltos planos consecutivos
    # ------------------------------------------------------------
    # Para cualquier cadena u->v->w->t en la que los tres saltos sean
    # horizontales, como máximo dos de esas tres aristas pueden usarse.
    for (u, v) in aristas_planas:
        for w in grafo.get(v, []):
            if (v, w) not in aristas_planas:
                continue

            for t in grafo.get(w, []):
                if (w, t) not in aristas_planas:
                    continue

                model.Add(
                    z[(u, v)] + z[(v, w)] + z[(w, t)] <= 2
                )

    # ------------------------------------------------------------
    # Objetivo
    # ------------------------------------------------------------
    # No buscamos todavía "el camino más corto", porque eso volvería a
    # favorecer rutas triviales. El objetivo secundario es maximizar la
    # variación vertical total entre los saltos seleccionados.
    variacion_vertical = []

    for (origen, destino), variable in z.items():
        dy_abs = abs(destino[1] - origen[1])
        if dy_abs > 0:
            variacion_vertical.append(dy_abs * variable)

    model.Maximize(sum(variacion_vertical))

    # ------------------------------------------------------------
    # Resolver
    # ------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_tiempo
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": solver.StatusName(status),
            "ruta": None,
            "saltos": None,
            "num_saltos": None,
            "num_subidas": None,
            "num_bajadas": None,
            "num_planos": None,
            "variacion_vertical": None,
            "tiempo": solver.WallTime(),
        }

    saltos_usados = [
        (origen, destino)
        for (origen, destino), variable in z.items()
        if solver.Value(variable) == 1
    ]

    # Reconstruir la secuencia ordenada START -> GOAL.
    siguiente = {origen: destino for origen, destino in saltos_usados}

    ruta = [inicio]
    actual = inicio

    while actual != meta:
        if actual not in siguiente:
            raise RuntimeError(
                "La solución de CP-SAT cumple el modelo pero no se puede "
                "reconstruir como una ruta START -> GOAL."
            )

        actual = siguiente[actual]
        ruta.append(actual)

        if len(ruta) > len(grafo) + 1:
            raise RuntimeError("Se ha detectado un ciclo inesperado.")

    subidas = 0
    bajadas = 0
    planos = 0
    variacion = 0

    for origen, destino in saltos_usados:
        dy = destino[1] - origen[1]
        variacion += abs(dy)

        if dy > 0:
            subidas += 1
        elif dy < 0:
            bajadas += 1
        else:
            planos += 1

    return {
        "status": solver.StatusName(status),
        "ruta": ruta,
        "saltos": saltos_usados,
        "num_saltos": len(saltos_usados),
        "num_subidas": subidas,
        "num_bajadas": bajadas,
        "num_planos": planos,
        "variacion_vertical": variacion,
        "tiempo": solver.WallTime(),
        "objetivo": solver.ObjectiveValue(),
    }