from ortools.sat.python import cp_model


def generar_ruta_cpsat_v2(
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
        nodo: model.NewBoolVar(f"u_{nodo[0]}_{nodo[1]}")
        for nodo in nodos
    }
    model.Add(usado[inicio] == 1)
    model.Add(usado[meta] == 1)

    z = {}
    entradas = {nodo: [] for nodo in nodos}
    salidas = {nodo: [] for nodo in nodos}

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
        e = sum(entradas[nodo])
        s = sum(salidas[nodo])
        model.Add(e == s)
        model.Add(e <= 1)
        model.Add(s <= 1)
        model.Add(usado[nodo] == e)

    numero_saltos = sum(z.values())
    model.Add(numero_saltos >= min_saltos)
    model.Add(numero_saltos <= max_saltos)

    subidas = []
    bajadas = []
    planos = set()

    for (origen, destino), var in z.items():
        dy = destino[1] - origen[1]
        if dy > 0:
            subidas.append(var)
        elif dy < 0:
            bajadas.append(var)
        else:
            planos.add((origen, destino))

    model.Add(sum(subidas) >= min_subidas)
    model.Add(sum(bajadas) >= min_bajadas)

    # No permitir tres saltos planos consecutivos.
    for (a, b) in planos:
        for c in grafo.get(b, []):
            if (b, c) not in planos:
                continue
            for d in grafo.get(c, []):
                if (c, d) not in planos:
                    continue
                model.Add(z[(a, b)] + z[(b, c)] + z[(c, d)] <= 2)

    # Evitar atajos: si dos nodos seleccionados pueden saltarse entre sí,
    # ese salto debe ser precisamente un salto consecutivo de la ruta.
    for (origen, destino), var in z.items():
        model.Add(usado[origen] + usado[destino] <= 1 + var)

    # Minimizar zigzag extremo.
    variacion = []
    for (origen, destino), var in z.items():
        dy_abs = abs(destino[1] - origen[1])
        if dy_abs:
            variacion.append(dy_abs * var)
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

    saltos_usados = [
        (o, d) for (o, d), var in z.items()
        if solver.Value(var) == 1
    ]
    nodos_usados = [
        n for n, var in usado.items()
        if solver.Value(var) == 1
    ]

    siguiente = {o: d for o, d in saltos_usados}
    ruta = [inicio]
    actual = inicio

    while actual != meta:
        actual = siguiente[actual]
        ruta.append(actual)

    n_subidas = 0
    n_bajadas = 0
    n_planos = 0
    variacion_total = 0

    for o, d in saltos_usados:
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
        "nodos_usados": nodos_usados,
        "saltos": saltos_usados,
        "num_saltos": len(saltos_usados),
        "num_subidas": n_subidas,
        "num_bajadas": n_bajadas,
        "num_planos": n_planos,
        "variacion_vertical": variacion_total,
        "tiempo": solver.WallTime(),
    }