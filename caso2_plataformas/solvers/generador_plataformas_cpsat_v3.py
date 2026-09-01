"""CP-SAT v3: ruta formada por plataformas horizontales de ancho fijo."""

from ortools.sat.python import cp_model
from modelo.grafo_saltos_segmentos import ANCHO_PLATAFORMA


def se_solapan(a, b):
    """Comprueba solapamiento físico de dos segmentos en la misma altura."""
    if a[1] != b[1]:
        return False

    a_ini = a[0]
    a_fin = a[0] + ANCHO_PLATAFORMA - 1
    b_ini = b[0]
    b_fin = b[0] + ANCHO_PLATAFORMA - 1

    return not (a_fin < b_ini or b_fin < a_ini)


def generar_ruta_segmentos_cpsat(
    grafo,
    inicio,
    meta,
    min_saltos=11,
    max_saltos=14,
    min_subidas=2,
    min_bajadas=2,
    max_tiempo=60.0,
    seed=20260824,
):
    model = cp_model.CpModel()
    nodos = list(grafo.keys())

    usado = {
        n: model.NewBoolVar(f"u_{n[0]}_{n[1]}")
        for n in nodos
    }

    model.Add(usado[inicio] == 1)
    model.Add(usado[meta] == 1)

    z = {}
    entradas = {n: [] for n in nodos}
    salidas = {n: [] for n in nodos}

    for origen, destinos in grafo.items():
        for destino in destinos:
            var = model.NewBoolVar(
                f"z_{origen[0]}_{origen[1]}__{destino[0]}_{destino[1]}"
            )
            z[(origen, destino)] = var
            salidas[origen].append(var)
            entradas[destino].append(var)

    model.Add(sum(salidas[inicio]) == 1)
    if entradas[inicio]:
        model.Add(sum(entradas[inicio]) == 0)

    model.Add(sum(entradas[meta]) == 1)
    if salidas[meta]:
        model.Add(sum(salidas[meta]) == 0)

    for nodo in nodos:
        if nodo in (inicio, meta):
            continue

        ent = sum(entradas[nodo])
        sal = sum(salidas[nodo])

        model.Add(ent == sal)
        model.Add(ent <= 1)
        model.Add(sal <= 1)
        model.Add(usado[nodo] == ent)

    # Dos plataformas físicas no pueden ocupar los mismos tiles.
    candidatas = [n for n in nodos if n not in (inicio, meta)]

    for i in range(len(candidatas)):
        for j in range(i + 1, len(candidatas)):
            a = candidatas[i]
            b = candidatas[j]

            if se_solapan(a, b):
                model.Add(usado[a] + usado[b] <= 1)

    numero_saltos = sum(z.values())
    model.Add(numero_saltos >= min_saltos)
    model.Add(numero_saltos <= max_saltos)

    subidas = []
    bajadas = []
    planos = set()

    for (o, d), var in z.items():
        dy = d[1] - o[1]

        if dy > 0:
            subidas.append(var)
        elif dy < 0:
            bajadas.append(var)
        else:
            planos.add((o, d))

    model.Add(sum(subidas) >= min_subidas)
    model.Add(sum(bajadas) >= min_bajadas)

    # Como en v2: no tres saltos planos seguidos.
    for (a, b) in planos:
        for c in grafo.get(b, []):
            if (b, c) not in planos:
                continue
            for d in grafo.get(c, []):
                if (c, d) not in planos:
                    continue
                model.Add(z[(a, b)] + z[(b, c)] + z[(c, d)] <= 2)

    # Antiatajos.
    for (o, d), var in z.items():
        model.Add(usado[o] + usado[d] <= 1 + var)

    # Preferir cambios verticales moderados.
    variacion = []
    for (o, d), var in z.items():
        dy = abs(d[1] - o[1])
        if dy:
            variacion.append(dy * var)

    model.Minimize(sum(variacion))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_tiempo
    solver.parameters.random_seed = seed
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

    usados = [
        n
        for n, var in usado.items()
        if solver.Value(var) == 1
    ]

    siguiente = {o: d for o, d in saltos}
    ruta = [inicio]
    actual = inicio

    while actual != meta:
        actual = siguiente[actual]
        ruta.append(actual)

    n_subidas = 0
    n_bajadas = 0
    n_planos = 0
    variacion_total = 0

    for o, d in saltos:
        dy = d[1] - o[1]
        variacion_total += abs(dy)

        if dy > 0:
            n_subidas += 1
        elif dy < 0:
            n_bajadas += 1
        else:
            n_planos += 1

    return {
        "status": solver.StatusName(status),
        "ruta": ruta,
        "nodos_usados": usados,
        "saltos": saltos,
        "num_saltos": len(saltos),
        "num_subidas": n_subidas,
        "num_bajadas": n_bajadas,
        "num_planos": n_planos,
        "variacion_vertical": variacion_total,
        "tiempo": solver.WallTime(),
    }