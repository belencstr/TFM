"""Solver de Simulated Annealing para los modelos QUBO del Caso 3.

Incorpora:
1. Validación rigurosa de las variables q_{t, c} del QUBO Integrado (validar_ruta_q):
   - Exactamente una celda por paso t in [0..12].
   - START en t=0 y GOAL en t=12.
   - Continuidad ortogonal entre pasos consecutivos.
   - Compatibilidad estricta con suelo transitable (x_c = 1).
2. Cálculo de Time To Solution (TTS) para una confianza del 99%:
   R_99 = ceil( ln(1 - 0.99) / ln(1 - p_exito) )
   TTS_99 = R_99 * t_read
3. Doble reporte de mejor muestra:
   - mejor_muestra_energia: menor energía raw (reveladora teóricamente).
   - mejor_muestra_valida: menor energía entre las factibles según restricciones duras.
4. Métrica de calidad: número de componentes conexas de suelo.
"""

from collections import deque
from time import perf_counter
from pathlib import Path
import math
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.metricas_tts import calcular_tts99

from formulacion.qubo_caso3 import (
    ROWS,
    COLS,
    CELLS,
    START,
    GOAL,
    ZONES,
    N_WALLS_PER_ZONE,
    CANDIDATES,
    PATH_CELLS,
    neighbors,
    var_x,
    var_q,
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
    Q = {}
    for var, coef in qubo["lineal"].items():
        Q[(var, var)] = float(coef)
    for (u, v), coef in qubo["cuadratico"].items():
        Q[(u, v)] = Q.get((u, v), 0.0) + float(coef)
    return Q


def bfs_camino_minimo(open_cells, start=START, goal=GOAL):
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
    from clasico.caso3_cpsat_v3 import EDGES
    fronteras = 0
    for u, v in EDGES:
        if (u in open_cells) != (v in open_cells):
            fronteras += 1
    return fronteras


def validar_ruta_q(sol_dict, open_cells):
    """Valida exhaustivamente si las variables q_{t, c} forman una ruta continua sobre suelo.

    Returns:
        (es_valida, ruta_celdas, motivo_fallo)
    """
    ruta_celdas = []

    for t in range(PATH_CELLS):
        activas = [c for c in CANDIDATES[t] if sol_dict.get(var_q(t, c[0], c[1]), 0) == 1]
        if len(activas) != 1:
            return False, None, f"Paso {t} tiene {len(activas)} celdas activas (esperado: 1)"
        ruta_celdas.append(activas[0])

    # START y GOAL
    if ruta_celdas[0] != START:
        return False, None, f"Paso 0 no es START: {ruta_celdas[0]}"
    if ruta_celdas[-1] != GOAL:
        return False, None, f"Paso {PATH_CELLS-1} no es GOAL: {ruta_celdas[-1]}"

    # Continuidad
    for t in range(PATH_CELLS - 1):
        a = ruta_celdas[t]
        b = ruta_celdas[t + 1]
        dist = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if dist != 1:
            return False, None, f"Discontinuidad entre paso {t} {a} y {t+1} {b} (dist={dist})"

    # Suelo transitable
    for t, c in enumerate(ruta_celdas):
        if c not in open_cells:
            return False, None, f"Paso {t} en {c} no es suelo transitable (x=0)"

    return True, ruta_celdas, "OK"


def calcular_tts(tiempo_total, num_reads, p_exito, confianza=0.99):
    """Calcula Time To Solution (TTS) para un nivel de confianza dado (por defecto 99%).

    Delega en common.metricas_tts.calcular_tts99 utilizando la formulación discreta ceil.
    """
    if num_reads <= 0:
        raise ValueError(f"num_reads debe ser un entero positivo. Recibido: {num_reads}")
    if tiempo_total <= 0:
        return 0.0
    t_read = tiempo_total / num_reads
    _, tts_val = calcular_tts99(p_exito, t_read, confidence=confianza)
    return tts_val


def resolver_qubo_sa(
    qubo,
    num_reads=100,
    num_sweeps=1000,
    seed=42,
    es_modelo_integrado=False,
):
    """Ejecuta Simulated Annealing y evalúa rigurosamente factibilidad y TTS."""
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
    muestras_validas = []
    num_exito = 0

    for registro in sampleset.data(fields=["sample", "energy", "num_occurrences"], sorted_by="energy"):
        sol_dict = dict(registro.sample)
        energia_total = float(registro.energy) + qubo["constante"]
        open_cells = extraer_mapa_de_solucion(sol_dict)

        start_ok = START in open_cells
        goal_ok = GOAL in open_cells

        # Zonas
        muros_por_zona = {}
        zonas_ok = True
        for z_name, z_cells in ZONES.items():
            m = sum(1 for c in z_cells if c not in open_cells)
            muros_por_zona[z_name] = m
            if m != N_WALLS_PER_ZONE:
                zonas_ok = False

        # Navegabilidad clásica (BFS)
        camino_bfs = bfs_camino_minimo(open_cells)
        es_navegable_bfs = camino_bfs is not None

        # Validación ruta q si es modelo integrado
        if es_modelo_integrado:
            es_ruta_q_ok, ruta_q, motivo_q = validar_ruta_q(sol_dict, open_cells)
        else:
            es_ruta_q_ok = False
            ruta_q = None
            motivo_q = "N/A (modelo desacoplado)"

        # Criterio de ÉXITO (Factibilidad dura):
        # - Desacoplado: START/GOAL + Zonas + Navegable BFS
        # - Integrado: START/GOAL + Zonas + Ruta q válida sobre suelo
        if es_modelo_integrado:
            es_factible = start_ok and goal_ok and zonas_ok and es_ruta_q_ok
        else:
            es_factible = start_ok and goal_ok and zonas_ok and es_navegable_bfs

        if es_factible:
            num_exito += int(registro.num_occurrences)

        comp = contar_componentes(open_cells)
        fronteras = calcular_fronteras_reales(open_cells)

        info_muestra = {
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
            "es_navegable_bfs": es_navegable_bfs,
            "camino_bfs": camino_bfs,
            "longitud_bfs": len(camino_bfs) - 1 if camino_bfs else None,
            "es_ruta_q_valida": es_ruta_q_ok,
            "ruta_q": ruta_q,
            "motivo_fallo_q": motivo_q,
            "componentes": comp,
            "fronteras": fronteras,
            "es_factible": es_factible,
            "calidad_perfecta": es_factible and comp == 1,
        }

        muestras_evaluadas.append(info_muestra)
        if es_factible:
            muestras_validas.append(info_muestra)

    # Probabilidad de éxito
    p_exito = num_exito / float(num_reads)

    # Time To Solution 99%
    tts_99 = calcular_tts(tiempo_sa, num_reads, p_exito, confianza=0.99)

    # Dos mejores muestras: por energía y por validez
    mejor_muestra_energia = muestras_evaluadas[0]
    mejor_muestra_valida = muestras_validas[0] if muestras_validas else None

    return {
        "muestras": muestras_evaluadas,
        "mejor_muestra_energia": mejor_muestra_energia,
        "mejor_muestra_valida": mejor_muestra_valida,
        "tiempo_segundos": tiempo_sa,
        "num_reads": num_reads,
        "num_sweeps": num_sweeps,
        "seed": seed,
        "p_exito": p_exito,
        "tts_99_segundos": tts_99,
        "num_variables": len(qubo["variables"]),
        "num_terminos_cuadraticos": len(qubo["cuadratico"]),
        "es_modelo_integrado": es_modelo_integrado,
    }
