from ortools.sat.python import cp_model
from modelo.grafo_saltos_segmentos_v4 import ANCHO_PLATAFORMA

def se_solapan(a, b):
    if a[1] != b[1]:
        return False
    a_fin = a[0] + ANCHO_PLATAFORMA - 1
    b_fin = b[0] + ANCHO_PLATAFORMA - 1
    return not (a_fin < b[0] or b_fin < a[0])

def generar_ruta_segmentos_cpsat_v4(
    grafo, inicio, meta,
    min_saltos=11, max_saltos=14,
    min_subidas=2, min_bajadas=2,
    max_tiempo=60.0, seed=20260825,
):
    model = cp_model.CpModel()
    nodos = list(grafo.keys())

    usado = {n: model.NewBoolVar(f"u_{n[0]}_{n[1]}") for n in nodos}
    model.Add(usado[inicio] == 1)
    model.Add(usado[meta] == 1)

    z = {}
    entradas = {n: [] for n in nodos}
    salidas = {n: [] for n in nodos}

    for o, destinos in grafo.items():
        for d in destinos:
            var = model.NewBoolVar(f"z_{o[0]}_{o[1]}__{d[0]}_{d[1]}")
            z[(o, d)] = var
            salidas[o].append(var)
            entradas[d].append(var)

    model.Add(sum(salidas[inicio]) == 1)
    if entradas[inicio]:
        model.Add(sum(entradas[inicio]) == 0)

    model.Add(sum(entradas[meta]) == 1)
    if salidas[meta]:
        model.Add(sum(salidas[meta]) == 0)

    for n in nodos:
        if n in (inicio, meta):
            continue
        ent = sum(entradas[n])
        sal = sum(salidas[n])
        model.Add(ent == sal)
        model.Add(ent <= 1)
        model.Add(sal <= 1)
        model.Add(usado[n] == ent)

    candidatas = [n for n in nodos if n not in (inicio, meta)]
    for i in range(len(candidatas)):
        for j in range(i+1, len(candidatas)):
            a, b = candidatas[i], candidatas[j]
            if se_solapan(a, b):
                model.Add(usado[a] + usado[b] <= 1)

    numero_saltos = sum(z.values())
    model.Add(numero_saltos >= min_saltos)
    model.Add(numero_saltos <= max_saltos)

    subidas, bajadas, planos = [], [], set()
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

    for (a, b) in planos:
        for c in grafo.get(b, []):
            if (b, c) not in planos:
                continue
            for d in grafo.get(c, []):
                if (c, d) not in planos:
                    continue
                model.Add(z[(a,b)] + z[(b,c)] + z[(c,d)] <= 2)

    for (o, d), var in z.items():
        model.Add(usado[o] + usado[d] <= 1 + var)

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
        return {"status": solver.StatusName(status), "ruta": None, "tiempo": solver.WallTime()}

    saltos = [(o,d) for (o,d), var in z.items() if solver.Value(var) == 1]
    usados = [n for n,var in usado.items() if solver.Value(var) == 1]

    siguiente = {o:d for o,d in saltos}
    ruta = [inicio]
    actual = inicio
    while actual != meta:
        actual = siguiente[actual]
        ruta.append(actual)

    n_subidas = n_bajadas = n_planos = variacion_total = 0
    for o,d in saltos:
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