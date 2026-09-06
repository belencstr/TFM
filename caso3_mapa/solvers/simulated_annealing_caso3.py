"""Solver de Simulated Annealing para el QUBO del Caso 3.

Utiliza dwave.samplers.SimulatedAnnealingSampler para muestrear el
espacio de estados del QUBO y evaluar las soluciones obtenidas:
- Cumplimiento de START y GOAL.
- Cumplimiento estricto de obstáculos por zona (5 muros / 7 suelos).
- Navegabilidad mediante BFS (camino mínimo START->GOAL).
- Conectividad global (número de componentes conexas transitables).
- Número de fronteras suelo/pared (valor objetivo de Ising).
"""

from collections import deque
from time import perf_counter
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3 import (
    ROWS,
    COLS,
    CELLS,
    START,
    GOAL,
    ZONES,
    N_WALLS_PER_ZONE,
    neighbors,
    var_x,
    extraer_mapa_de_solucion,
)


def _importar_sampler():
    try:
        from dwave.samplers import SimulatedAnnealingSampler
        return SimulatedAnnealingSampler
    except ImportError as exc:
        raise ImportError(
            "No se encuentra 'dwave-samplers'. Instálalo con:\n"
            "    pip install dwave-samplers"
        ) from exc


def convertir_a_diccionario_qubo(qubo):
    """Convierte la estructura QUBO a la representación Q[(u, v)] = coeff."""
    Q = {}
    for var, coef in qubo["lineal"].items():
        Q[(var, var)] = float(coef)

    for (u, v), coef in qubo["cuadratico"].items():
        Q[(u, v)] = Q.get((u, v), 0.0) + float(coef)

    return Q


def bfs_camino_minimo(open_cells, start=START, goal=GOAL):
    """Calcula el camino más corto entre START y GOAL sobre las celdas abiertas."""
    if start not in open_cells or goal not in open_cells:
        return None

    queue = deque([start])
    parent = {start: None}

    while queue:
        current = queue.popleft()
        if current == goal:
            break

        for nxt in neighbors(current):
            if nxt in open_cells and nxt not in parent:
                parent[nxt] = current
                queue.append(nxt)

    if goal not in parent:
        return None

    path = []
    curr = goal
    while curr is not None:
        path.append(curr)
        curr = parent[curr]
    path.reverse()
    return path


def contar_componentes(open_cells):
    """Cuenta el número de componentes conexas de suelo."""
    unseen = set(open_cells)
    components = 0

    while unseen:
        components += 1
        first = next(iter(unseen))
        queue = deque([first])
        unseen.remove(first)

        while queue:
            curr = queue.popleft()
            for nxt in neighbors(curr):
                if nxt in unseen:
                    unseen.remove(nxt)
                    queue.append(nxt)

    return components


def calcular_fronteras_reales(open_cells):
    """Cuenta las transiciones suelo/muro reales en el mapa."""
    from clasico.caso3_cpsat_v3 import EDGES
    fronteras = 0
    for u, v in EDGES:
        u_open = u in open_cells
        v_open = v in open_cells
        if u_open != v_open:
            fronteras += 1
    return fronteras


def resolver_qubo_sa(qubo, num_reads=100, num_sweeps=1000, seed=42):
    """Ejecuta Simulated Annealing sobre el QUBO y analiza las muestras."""
    SimulatedAnnealingSampler = _importar_sampler()
    sampler = SimulatedAnnealingSampler()

    Q = convertir_a_diccionario_qubo(qubo)

    t0 = perf_counter()
    sampleset = sampler.sample_qubo(
        Q,
        num_reads=num_reads,
        num_sweeps=num_sweeps,
        seed=seed,
    )
    tiempo_sa = perf_counter() - t0

    muestras_evaluadas = []
    num_factibles_zona = 0
    num_factibles_navegables = 0

    for registro in sampleset.data(fields=["sample", "energy", "num_occurrences"], sorted_by="energy"):
        sol_dict = dict(registro.sample)
        energia_total = float(registro.energy) + qubo["constante"]
        open_cells = extraer_mapa_de_solucion(sol_dict)

        # 1. Validación de START y GOAL
        start_ok = START in open_cells
        goal_ok = GOAL in open_cells

        # 2. Validación de zonas
        muros_por_zona = {}
        zonas_ok = True
        for z_name, z_cells in ZONES.items():
            muros = sum(1 for c in z_cells if c not in open_cells)
            muros_por_zona[z_name] = muros
            if muros != N_WALLS_PER_ZONE:
                zonas_ok = False

        if start_ok and goal_ok and zonas_ok:
            num_factibles_zona += 1

        # 3. Validación de conectividad (BFS)
        camino_bfs = bfs_camino_minimo(open_cells)
        es_navegable = camino_bfs is not None
        if start_ok and goal_ok and zonas_ok and es_navegable:
            num_factibles_navegables += 1

        comp = contar_componentes(open_cells)
        fronteras = calcular_fronteras_reales(open_cells)

        muestras_evaluadas.append({
            "asignacion": sol_dict,
            "energia": energia_total,
            "energia_raw": float(registro.energy),
            "num_occurrences": int(registro.num_occurrences),
            "open_cells": open_cells,
            "num_open": len(open_cells),
            "num_walls": ROWS * COLS - len(open_cells),
            "start_ok": start_ok,
            "goal_ok": goal_ok,
            "zonas_ok": zonas_ok,
            "muros_por_zona": muros_por_zona,
            "es_navegable": es_navegable,
            "camino_bfs": camino_bfs,
            "longitud_bfs": len(camino_bfs) - 1 if camino_bfs else None,
            "componentes": comp,
            "fronteras": fronteras,
            "es_completamente_valida": start_ok and goal_ok and zonas_ok and es_navegable and comp == 1,
        })

    mejor_muestra = muestras_evaluadas[0]

    return {
        "muestras": muestras_evaluadas,
        "mejor_muestra": mejor_muestra,
        "tiempo_segundos": tiempo_sa,
        "num_reads": num_reads,
        "num_sweeps": num_sweeps,
        "seed": seed,
        "tasa_factibilidad_zonas": num_factibles_zona / num_reads,
        "tasa_factibilidad_navegable": num_factibles_navegables / num_reads,
        "num_variables": len(qubo["variables"]),
        "num_terminos_cuadraticos": len(qubo["cuadratico"]),
    }
