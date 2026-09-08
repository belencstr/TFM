"""Experimento de resolución con Simulated Annealing para el QUBO Completo del Caso 3.

Resuelve el nivel completo integrando:
1. Geometría (48 celdas, 5 muros/zona, coherencia Ising).
2. Ruta principal (q_{t,c}, ruta START->GOAL de 12 pasos codificada mediante penalizaciones Hamiltonianas cuadráticas).
3. Gameplay en ruta (1 recompensa en t in [2..4], 2 enemigos en t in [5..7] y [9..11]).
4. Rama secundaria de exploración (catálogo geométrico de 12 patrones b_k con conexión en ruta y callejón sin salida con premio).

Evalúa la factibilidad de forma exhaustiva y genera visualización ASCII detallada.
"""

from datetime import datetime
import json
from pathlib import Path
from time import perf_counter
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
    PATH_CELLS,
    neighbors,
)
from formulacion.qubo_caso3_completo import (
    construir_qubo_completo,
    BRANCH_PATTERNS,
    REWARD_ROUTE_STEPS,
    ENEMY_1_STEPS,
    ENEMY_2_STEPS,
    var_reward_route,
    var_enemy_1,
    var_enemy_2,
    var_branch_pattern,
)
from solvers.simulated_annealing_caso3 import (
    _importar_sampler,
    convertir_a_diccionario_qubo,
    extraer_mapa_de_solucion,
    bfs_camino_minimo,
    validar_ruta_q,
    contar_componentes,
    calcular_fronteras_reales,
    calcular_tts,
)

RESULTADOS_DIR = BASE_DIR / "experimentos" / "resultados"
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)


def validar_nivel_completo(sol_dict, open_cells):
    """Valida exhaustivamente todas las restricciones del nivel completo QUBO."""
    # 1. Start y Goal
    if START not in open_cells or GOAL not in open_cells:
        return False, None, "START o GOAL bloqueados"

    # 2. Zonas
    muros_por_zona = {}
    for z_name, z_cells in ZONES.items():
        m = sum(1 for c in z_cells if c not in open_cells)
        muros_por_zona[z_name] = m
        if m != N_WALLS_PER_ZONE:
            return False, None, f"Zona {z_name} con {m} muros (esperado {N_WALLS_PER_ZONE})"

    # 3. Ruta principal q
    es_ruta_ok, ruta_celdas, motivo_q = validar_ruta_q(sol_dict, open_cells)
    if not es_ruta_ok:
        return False, None, f"Fallo en ruta q: {motivo_q}"

    # 4. Gameplay en ruta
    # 4.1. Recompensa
    active_rewards = [t for t in REWARD_ROUTE_STEPS if sol_dict.get(var_reward_route(t), 0) == 1]
    if len(active_rewards) != 1:
        return False, None, f"Recompensa de ruta tiene {len(active_rewards)} selecciones (esperado 1)"
    step_reward = active_rewards[0]
    cell_reward = ruta_celdas[step_reward]

    # 4.2. Enemigo 1
    active_ene1 = [t for t in ENEMY_1_STEPS if sol_dict.get(var_enemy_1(t), 0) == 1]
    if len(active_ene1) != 1:
        return False, None, f"Enemigo 1 tiene {len(active_ene1)} selecciones (esperado 1)"
    step_ene1 = active_ene1[0]
    cell_ene1 = ruta_celdas[step_ene1]

    # 4.3. Enemigo 2
    active_ene2 = [t for t in ENEMY_2_STEPS if sol_dict.get(var_enemy_2(t), 0) == 1]
    if len(active_ene2) != 1:
        return False, None, f"Enemigo 2 tiene {len(active_ene2)} selecciones (esperado 1)"
    step_ene2 = active_ene2[0]
    cell_ene2 = ruta_celdas[step_ene2]

    # 4.4. No consecutividad
    if step_reward == 4 and step_ene1 == 5:
        return False, None, "Recompensa y Enemigo 1 consecutivos (pasos 4 y 5)"

    # 5. Rama secundaria
    active_branches = [p for p in BRANCH_PATTERNS if sol_dict.get(var_branch_pattern(p["id"]), 0) == 1]
    if len(active_branches) != 1:
        return False, None, f"Rama secundaria tiene {len(active_branches)} selecciones (esperado 1)"
    branch = active_branches[0]
    u, a, b = branch["u"], branch["a"], branch["b"]

    # Conexión con ruta
    if u not in ruta_celdas:
        return False, None, f"La celda de conexión u={u} no pertenece a la ruta"

    # Apertura de celdas de rama
    if a not in open_cells or b not in open_cells:
        return False, None, f"Celdas de rama no transitables (a in suelo: {a in open_cells}, b in suelo: {b in open_cells})"

    # Celdas fuera de ruta
    if a in ruta_celdas or b in ruta_celdas:
        return False, None, f"Celdas de rama intersectan la ruta principal"

    # b es callejón sin salida (dead-end): su único vecino en open_cells es a
    vecinos_b_abiertos = [w for w in neighbors(b) if w in open_cells]
    if vecinos_b_abiertos != [a]:
        return False, None, f"b={b} no es callejón sin salida (vecinos abiertos: {vecinos_b_abiertos})"

    # a solo conecta con u y b
    vecinos_a_abiertos = set(v for v in neighbors(a) if v in open_cells)
    if vecinos_a_abiertos != {u, b}:
        return False, None, f"a={a} tiene conexiones parásitas (vecinos abiertos: {vecinos_a_abiertos}, esperado: {{u, b}})"

    info_gameplay = {
        "ruta": ruta_celdas,
        "step_reward": step_reward,
        "cell_reward": cell_reward,
        "step_ene1": step_ene1,
        "cell_ene1": cell_ene1,
        "step_ene2": step_ene2,
        "cell_ene2": cell_ene2,
        "branch_pattern_id": branch["id"],
        "branch_desc": branch["desc"],
        "branch_u": u,
        "branch_a": a,
        "branch_b": b,
        "branch_reward_cell": b,
    }

    return True, info_gameplay, "OK"


def render_ascii_map(open_cells, gameplay_info=None):
    """Genera representación ASCII rica del nivel completo."""
    grid = [["█" for _ in range(COLS)] for _ in range(ROWS)]

    # 1. Suelo
    for r, c in open_cells:
        grid[r][c] = "·"

    # 2. Rama
    if gameplay_info:
        a = gameplay_info["branch_a"]
        b = gameplay_info["branch_b"]
        grid[a[0]][a[1]] = "*"
        grid[b[0]][b[1]] = "$"  # Premio de rama

    # 3. Ruta principal
    if gameplay_info:
        for r, c in gameplay_info["ruta"]:
            grid[r][c] = "o"

        # Gameplay en ruta
        cr = gameplay_info["cell_reward"]
        ce1 = gameplay_info["cell_ene1"]
        ce2 = gameplay_info["cell_ene2"]
        grid[cr[0]][cr[1]] = "R"
        grid[ce1[0]][ce1[1]] = "E"
        grid[ce2[0]][ce2[1]] = "E"

    # 4. Start y Goal
    grid[START[0]][START[1]] = "S"
    grid[GOAL[0]][GOAL[1]] = "G"

    lineas = []
    lineas.append("   " + " ".join(f"{c}" for c in range(COLS)))
    lineas.append("  +" + "--" * COLS + "+")
    for r in range(ROWS):
        fila_str = f"{r} | " + " ".join(grid[r][c] for c in range(COLS)) + " |"
        lineas.append(fila_str)
    lineas.append("  +" + "--" * COLS + "+")
    lineas.append("Leyenda: S=Start, G=Goal, o=Ruta, R=Premio ruta, E=Enemigo, *=Rama, $=Cofre rama, ·=Suelo, █=Muro")
    return "\n".join(lineas)


def exportar_qubo_completo_blender(mejor_val, seed, timestamp, tiempo_sa=0.0):
    """Exporta la solución completa válida a JSON compatible con el visualizador 3D de Blender."""
    if not mejor_val or not mejor_val.get("gameplay_info"):
        return None

    g = mejor_val["gameplay_info"]
    open_cells = set(mejor_val["open_cells"])
    ruta_q = g["ruta"]
    path_set = set(ruta_q)
    rew_cell = g["cell_reward"]
    ene1_cell = g["cell_ene1"]
    ene2_cell = g["cell_ene2"]
    route_rewards = {rew_cell}
    route_enemies = {ene1_cell, ene2_cell}
    branch_att = g["branch_u"]
    branch_a = g["branch_a"]
    branch_b = g["branch_b"]
    branch_reward = branch_b
    branch_path = [branch_att, branch_a, branch_b]

    cells_data = []
    for r in range(ROWS):
        for c in range(COLS):
            cell = (r, c)
            is_open = cell in open_cells

            if cell == START:
                cell_type = "START"
            elif cell == GOAL:
                cell_type = "GOAL"
            elif cell == branch_reward:
                cell_type = "BRANCH_REWARD"
            elif cell == branch_a:
                cell_type = "BRANCH"
            elif cell in route_rewards:
                cell_type = "REWARD"
            elif cell in route_enemies:
                cell_type = "ENEMY"
            elif cell in path_set:
                cell_type = "PATH"
            elif is_open:
                cell_type = "FLOOR"
            else:
                cell_type = "WALL"

            cells_data.append({
                "row": r,
                "col": c,
                "type": cell_type,
                "is_open": is_open,
                "is_path": cell in path_set,
                "is_branch": cell in (branch_a, branch_b),
                "is_reward": cell in route_rewards or cell == branch_reward,
                "is_enemy": cell in route_enemies,
            })

    # Ejecución explícita del algoritmo BFS real sobre la geometría generada
    camino_bfs = bfs_camino_minimo(open_cells, START, GOAL)
    longitud_bfs = len(camino_bfs) - 1 if camino_bfs else None

    data = {
        "metadata": {
            "caso": 3,
            "titulo": "Mapa 2D con obstáculos y gameplay - QUBO Completo (117 vars)",
            "solver": "QUBO Completo (117 vars) + Simulated Annealing (P=100)",
            "status": "VALID_SAMPLE",
            "seed": seed,
            "timestamp": timestamp,
            "solve_time_seconds": round(tiempo_sa, 6),
            "objective_value": mejor_val["fronteras"],
            "grid_rows": ROWS,
            "grid_cols": COLS,
            "total_cells": ROWS * COLS,
            "floor_cells_count": len(open_cells),
            "wall_cells_count": ROWS * COLS - len(open_cells),
            "components_count": mejor_val["componentes"],
            "bfs_path_length": longitud_bfs,
            "witness_path_length": len(ruta_q) - 1,
            "branch_pattern_id": g["branch_pattern_id"],
            "branch_pattern_desc": g["branch_desc"],
        },
        "points_of_interest": {
            "start": {"row": START[0], "col": START[1]},
            "goal": {"row": GOAL[0], "col": GOAL[1]},
            "route_rewards": [{"row": rew_cell[0], "col": rew_cell[1]}],
            "route_enemies": [
                {"row": ene1_cell[0], "col": ene1_cell[1]},
                {"row": ene2_cell[0], "col": ene2_cell[1]},
            ],
            "branch_attachment": {"row": branch_att[0], "col": branch_att[1]},
            "branch_a": {"row": branch_a[0], "col": branch_a[1]},
            "branch_b": {"row": branch_b[0], "col": branch_b[1]},
            "branch_reward": {"row": branch_reward[0], "col": branch_reward[1]},
        },
        "paths": {
            "main_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(ruta_q)],
            "validated_main_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(ruta_q)],
            "branch_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(branch_path)],
            "bfs_shortest_path": [{"row": r, "col": c, "step": idx} for idx, (r, c) in enumerate(camino_bfs)] if camino_bfs else None,
        },
        "cells": cells_data,
    }

    json_ts_path = RESULTADOS_DIR / f"caso3_nivel_blender_qubo_full_6x8_seed{seed}_{timestamp}.json"
    json_fixed_path = RESULTADOS_DIR / "caso3_nivel_blender_qubo_full_6x8.json"

    with open(json_ts_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    with open(json_fixed_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exportación para Blender (QUBO Full) guardada en:")
    print(f"  {json_ts_path}")
    print(f"  {json_fixed_path}")
    return json_fixed_path


def ejecutar_sa_qubo_completo(num_reads=100, num_sweeps=1500, seed=42):
    print("=" * 76)
    print("CASO 3 — RESOLUCIÓN DEL QUBO COMPLETO MEDIANTE SIMULATED ANNEALING")
    print("Geometría + Ruta Integrada + 2 Enemigos + 1 Premio + Rama Secundaria")
    print(f"Parámetros: Reads={num_reads}, Sweeps={num_sweeps}, Semilla={seed}")
    print("=" * 76)
    print()

    print("Construyendo matriz QUBO Completa (117 variables)...")
    qubo = construir_qubo_completo()
    Q = convertir_a_diccionario_qubo(qubo)
    print(f"QUBO listo: {qubo['num_vars']} variables, {len(qubo['cuadratico'])} acoplamientos cuadráticos.")
    print()

    print("Muestreando con Simulated Annealing...")
    SimulatedAnnealingSampler = _importar_sampler()
    sampler = SimulatedAnnealingSampler()

    t0 = perf_counter()
    sampleset = sampler.sample_qubo(
        Q,
        num_reads=num_reads,
        num_sweeps=num_sweeps,
        seed=seed,
    )
    tiempo_sa = perf_counter() - t0
    print(f"Muestreo completado en {tiempo_sa:.3f} s.")
    print()

    muestras_evaluadas = []
    muestras_validas = []
    num_exito = 0

    for reg in sampleset.data(fields=["sample", "energy", "num_occurrences"], sorted_by="energy"):
        sol_dict = dict(reg.sample)
        energia_total = float(reg.energy) + qubo["constante"]
        open_cells = extraer_mapa_de_solucion(sol_dict)

        es_valido, g_info, motivo = validar_nivel_completo(sol_dict, open_cells)
        if es_valido:
            num_exito += int(reg.num_occurrences)

        comp = contar_componentes(open_cells)
        fronteras = calcular_fronteras_reales(open_cells)

        info = {
            "energia": energia_total,
            "energia_raw": float(reg.energy),
            "num_occurrences": int(reg.num_occurrences),
            "open_cells": open_cells,
            "es_valido": es_valido,
            "motivo_fallo": motivo,
            "gameplay_info": g_info,
            "componentes": comp,
            "fronteras": fronteras,
            "sol_dict": sol_dict,
        }
        muestras_evaluadas.append(info)
        if es_valido:
            muestras_validas.append(info)

    p_exito = num_exito / float(num_reads)
    tts_99 = calcular_tts(tiempo_sa, num_reads, p_exito, confianza=0.99)
    tts_str = f"{tts_99*1000:.2f} ms" if tts_99 < float("inf") else "inf"

    mejor_min_e = muestras_evaluadas[0]
    mejor_val = muestras_validas[0] if muestras_validas else None

    print("=" * 76)
    print("RESULTADOS EXPERIMENTALES DEL QUBO COMPLETO")
    print("=" * 76)
    print(f"Tasa de éxito / Nivel válido completo: {p_exito*100:.1f}% ({num_exito}/{num_reads} reads)")
    print(f"Time To Solution (TTS_99) en CPU: {tts_str}")
    print(f"Tiempo total de muestreo: {tiempo_sa:.3f} s ({tiempo_sa/num_reads*1000:.2f} ms/read)")
    print()

    if mejor_val:
        print("MEJOR SOLUCIÓN VÁLIDA OBTENIDA:")
        print(f"  Energía Hamiltoniana: {mejor_val['energia']:.1f}")
        print(f"  Fronteras reales Ising: {mejor_val['fronteras']}")
        print(f"  Componentes conexas de suelo: {mejor_val['componentes']}")
        g = mejor_val["gameplay_info"]
        print(f"  Ruta principal (longitud): {len(g['ruta']) - 1} pasos")
        print(f"  Recompensa de ruta: Paso {g['step_reward']} en celda {g['cell_reward']}")
        print(f"  Enemigos de ruta: Enemigo 1 en paso {g['step_ene1']} ({g['cell_ene1']}), Enemigo 2 en paso {g['step_ene2']} ({g['cell_ene2']})")
        print(f"  Rama secundaria: Patrón #{g['branch_pattern_id']} ({g['branch_desc']})")
        print(f"    - Conexión con ruta: u={g['branch_u']}")
        print(f"    - Paso 1 de rama: a={g['branch_a']}")
        print(f"    - Final en callejón sin salida: b={g['branch_b']} (Cofre de recompensa)")
        print()
        print("MAPA DEL NIVEL COMPLETO GENERADO POR QUBO:")
        print(render_ascii_map(mejor_val["open_cells"], g))
    else:
        print("Aviso: No se encontró ninguna muestra que satisfaga simultáneamente el 100% de restricciones duras en estos 100 reads.")
        print(f"Mejor muestra por energía bruta: {mejor_min_e['fronteras']} fronteras (Fallo: {mejor_min_e['motivo_fallo']})")
        print(render_ascii_map(mejor_min_e["open_cells"], None))

    print("=" * 76)

    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTADOS_DIR / f"qubo_completo_sa_seed{seed}_{timestamp}.json"
    data_to_save = {
        "seed": seed,
        "num_reads": num_reads,
        "num_sweeps": num_sweeps,
        "p_exito": p_exito,
        "tts_99_ms": tts_99 * 1000 if tts_99 < float("inf") else None,
        "tiempo_total_s": tiempo_sa,
        "mejor_valida": {
            "fronteras": mejor_val["fronteras"],
            "componentes": mejor_val["componentes"],
            "gameplay": mejor_val["gameplay_info"],
            "open_cells": sorted(list(mejor_val["open_cells"])),
        } if mejor_val else None,
    }
    json_path.write_text(json.dumps(data_to_save, indent=2), encoding="utf-8")
    print(f"Resultados guardados en: {json_path}")

    # Exportar a Blender si hay solución válida
    if mejor_val:
        exportar_qubo_completo_blender(mejor_val, seed=seed, timestamp=timestamp, tiempo_sa=tiempo_sa)

    return {
        "p_exito": p_exito,
        "tts_99": tts_99,
        "mejor_valida": mejor_val,
        "mejor_energia": mejor_min_e,
    }


if __name__ == "__main__":
    ejecutar_sa_qubo_completo(num_reads=100, num_sweeps=1500, seed=42)
