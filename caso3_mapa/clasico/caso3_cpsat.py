from collections import deque
from datetime import datetime
from pathlib import Path
from time import perf_counter
import csv

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from ortools.sat.python import cp_model


# ============================================================
# CONFIGURACIÓN DEL CASO 3
# ============================================================

ROWS = 6
COLS = 8

# Se colocan en esquinas opuestas para que la distancia Manhattan
# mínima sea exactamente 12 movimientos.
START = (0, 0)
GOAL = (5, 7)

# Ruta principal: 13 celdas = 12 movimientos.
PATH_CELLS = 13

# El mapa se divide en cuatro zonas 3x4.
# Cada zona contiene exactamente 5 obstáculos.
N_WALLS_PER_ZONE = 5

N_REWARDS = 2
N_ENEMIES = 2

SEED = 42
MAX_TIME = 30.0


# ============================================================
# CARPETAS DE SALIDA
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

RESULTS_DIR = BASE_DIR / "experimentos" / "resultados"
FIGURES_DIR = BASE_DIR / "experimentos" / "figuras"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# GRID
# ============================================================

CELLS = [
    (r, c)
    for r in range(ROWS)
    for c in range(COLS)
]


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors(cell):
    r, c = cell
    result = []

    for dr, dc in [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
    ]:
        nr = r + dr
        nc = c + dc

        if 0 <= nr < ROWS and 0 <= nc < COLS:
            result.append((nr, nc))

    return result


def grid_edges():
    edges = []

    for r, c in CELLS:
        if r + 1 < ROWS:
            edges.append(((r, c), (r + 1, c)))

        if c + 1 < COLS:
            edges.append(((r, c), (r, c + 1)))

    return edges


EDGES = grid_edges()


# ============================================================
# ZONAS DEL MAPA
# ============================================================

# Cuatro regiones iguales de 3x4.
# La distribución exacta evita que CP-SAT coloque todos los
# obstáculos en una única masa.

ZONES = {
    "A": [
        (r, c)
        for r in range(0, 3)
        for c in range(0, 4)
    ],
    "B": [
        (r, c)
        for r in range(0, 3)
        for c in range(4, 8)
    ],
    "C": [
        (r, c)
        for r in range(3, 6)
        for c in range(0, 4)
    ],
    "D": [
        (r, c)
        for r in range(3, 6)
        for c in range(4, 8)
    ],
}

N_WALLS = len(ZONES) * N_WALLS_PER_ZONE
N_OPEN = ROWS * COLS - N_WALLS


# ============================================================
# PODA DE VARIABLES DE RUTA
# ============================================================

def candidate_cells_for_step(t):
    """
    Conserva únicamente las celdas que pueden aparecer en el
    paso t de una ruta de longitud PATH_CELLS.

    Como START y GOAL están en esquinas opuestas y la ruta tiene
    exactamente la distancia Manhattan mínima, la poda es fuerte:
    cada celda solo puede aparecer en un paso concreto.
    """

    remaining = PATH_CELLS - 1 - t
    candidates = []

    for cell in CELLS:
        d_start = manhattan(START, cell)
        d_goal = manhattan(cell, GOAL)

        reachable_from_start = (
            d_start <= t
            and (t - d_start) % 2 == 0
        )

        reachable_to_goal = (
            d_goal <= remaining
            and (remaining - d_goal) % 2 == 0
        )

        if reachable_from_start and reachable_to_goal:
            candidates.append(cell)

    return candidates


CANDIDATES = {
    t: candidate_cells_for_step(t)
    for t in range(PATH_CELLS)
}


# ============================================================
# VALIDACIÓN INDEPENDIENTE MEDIANTE BFS
# ============================================================

def bfs_shortest_path(open_cells):
    if START not in open_cells or GOAL not in open_cells:
        return None

    queue = deque([START])
    parent = {START: None}

    while queue:
        current = queue.popleft()

        if current == GOAL:
            break

        for nxt in neighbors(current):
            if nxt not in open_cells:
                continue

            if nxt in parent:
                continue

            parent[nxt] = current
            queue.append(nxt)

    if GOAL not in parent:
        return None

    path = []
    node = GOAL

    while node is not None:
        path.append(node)
        node = parent[node]

    path.reverse()
    return path


def count_components(open_cells):
    unseen = set(open_cells)
    components = 0

    while unseen:
        components += 1

        first = next(iter(unseen))
        queue = deque([first])
        unseen.remove(first)

        while queue:
            current = queue.popleft()

            for nxt in neighbors(current):
                if nxt in unseen:
                    unseen.remove(nxt)
                    queue.append(nxt)

    return components


# ============================================================
# MODELO CP-SAT
# ============================================================

def solve_case3(seed=SEED):
    model = cp_model.CpModel()

    # --------------------------------------------------------
    # 1. GEOMETRÍA DEL NIVEL
    # --------------------------------------------------------
    # x[cell] = 1 -> suelo transitable
    # x[cell] = 0 -> obstáculo

    x = {
        cell: model.new_bool_var(f"x_{cell[0]}_{cell[1]}")
        for cell in CELLS
    }

    model.add(x[START] == 1)
    model.add(x[GOAL] == 1)

    # Cinco paredes exactas en cada cuadrante 3x4.
    # Como x=1 representa suelo:
    # sum(x en zona) = 12 - 5 = 7.
    for zone_name, zone_cells in ZONES.items():
        model.add(
            sum(x[cell] for cell in zone_cells)
            == len(zone_cells) - N_WALLS_PER_ZONE
        )

    # --------------------------------------------------------
    # 2. RUTA PRINCIPAL
    # --------------------------------------------------------
    # q[t, cell] = 1 si la ruta ocupa cell en el paso t.

    q = {}

    for t in range(PATH_CELLS):
        for cell in CANDIDATES[t]:
            q[t, cell] = model.new_bool_var(
                f"q_{t}_{cell[0]}_{cell[1]}"
            )

    # Exactamente una celda por paso.
    for t in range(PATH_CELLS):
        model.add(
            sum(q[t, cell] for cell in CANDIDATES[t]) == 1
        )

    model.add(q[0, START] == 1)
    model.add(q[PATH_CELLS - 1, GOAL] == 1)

    # La ruta solo atraviesa suelo.
    for (t, cell), variable in q.items():
        model.add(variable <= x[cell])

    # No repetir una celda.
    # Con la poda actual es casi redundante, pero se conserva
    # para que la formulación quede explícita y reutilizable.
    for cell in CELLS:
        appearances = [
            q[t, cell]
            for t in range(PATH_CELLS)
            if (t, cell) in q
        ]

        if len(appearances) > 1:
            model.add(sum(appearances) <= 1)

    # Continuidad: pasos consecutivos deben ser vecinos.
    for t in range(PATH_CELLS - 1):
        for cell_a in CANDIDATES[t]:
            valid_neighbors = set(neighbors(cell_a))

            for cell_b in CANDIDATES[t + 1]:
                if cell_b not in valid_neighbors:
                    model.add(
                        q[t, cell_a]
                        + q[t + 1, cell_b]
                        <= 1
                    )

    # --------------------------------------------------------
    # 3. PREMIOS Y ENEMIGOS
    # --------------------------------------------------------
    # Los elementos se indexan por paso de la ruta, no por celda.
    # Así quedan automáticamente situados sobre suelo transitable.

    reward = {
        t: model.new_bool_var(f"reward_{t}")
        for t in range(PATH_CELLS)
    }

    enemy = {
        t: model.new_bool_var(f"enemy_{t}")
        for t in range(PATH_CELLS)
    }

    model.add(sum(reward.values()) == N_REWARDS)
    model.add(sum(enemy.values()) == N_ENEMIES)

    # START y GOAL nunca contienen elementos.
    for t in [0, PATH_CELLS - 1]:
        model.add(reward[t] == 0)
        model.add(enemy[t] == 0)

    # Un paso no puede contener premio y enemigo a la vez.
    for t in range(PATH_CELLS):
        model.add(reward[t] + enemy[t] <= 1)

    # No se colocan dos elementos de gameplay en pasos consecutivos.
    for t in range(PATH_CELLS - 1):
        model.add(
            reward[t]
            + enemy[t]
            + reward[t + 1]
            + enemy[t + 1]
            <= 1
        )

    # Progresión sencilla del nivel:
    # premio temprano -> enemigo -> premio -> enemigo final.
    model.add(sum(reward[t] for t in range(2, 4)) == 1)
    model.add(sum(enemy[t] for t in range(5, 7)) == 1)
    model.add(sum(reward[t] for t in range(8, 10)) == 1)
    model.add(sum(enemy[t] for t in range(10, 12)) == 1)

    # --------------------------------------------------------
    # 4. OBJETIVO: COHERENCIA ESPACIAL
    # --------------------------------------------------------
    # Se penaliza cada frontera entre suelo y pared.
    # Al estar obligados a repartir 5 paredes en cada zona,
    # ya no puede aparecer la solución degenerada de acumular
    # todas las paredes en un único lado del mapa.

    boundary = {}

    for idx, (a, b) in enumerate(EDGES):
        boundary[idx] = model.new_bool_var(
            f"boundary_{idx}"
        )

        model.add_abs_equality(
            boundary[idx],
            x[a] - x[b]
        )

    model.minimize(sum(boundary.values()))

    # --------------------------------------------------------
    # 5. RESOLUCIÓN
    # --------------------------------------------------------

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = MAX_TIME
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = 1

    t0 = perf_counter()
    status = solver.solve(model)
    elapsed = perf_counter() - t0

    status_names = {
        cp_model.UNKNOWN: "UNKNOWN",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.OPTIMAL: "OPTIMAL",
    }

    status_name = status_names.get(status, str(status))

    if status not in (
        cp_model.FEASIBLE,
        cp_model.OPTIMAL,
    ):
        print("No se ha encontrado solución.")
        print("Estado:", status_name)
        return None

    # --------------------------------------------------------
    # 6. EXTRAER SOLUCIÓN
    # --------------------------------------------------------

    open_cells = {
        cell
        for cell in CELLS
        if solver.boolean_value(x[cell])
    }

    witness_path = []

    for t in range(PATH_CELLS):
        selected = None

        for cell in CANDIDATES[t]:
            if solver.boolean_value(q[t, cell]):
                selected = cell
                break

        witness_path.append(selected)

    reward_steps = [
        t
        for t in range(PATH_CELLS)
        if solver.boolean_value(reward[t])
    ]

    enemy_steps = [
        t
        for t in range(PATH_CELLS)
        if solver.boolean_value(enemy[t])
    ]

    reward_cells = [
        witness_path[t]
        for t in reward_steps
    ]

    enemy_cells = [
        witness_path[t]
        for t in enemy_steps
    ]

    bfs_path = bfs_shortest_path(open_cells)
    components = count_components(open_cells)

    walls_by_zone = {}

    for zone_name, zone_cells in ZONES.items():
        walls_by_zone[zone_name] = sum(
            1
            for cell in zone_cells
            if cell not in open_cells
        )

    return {
        "status": status_name,
        "time": elapsed,
        "objective": solver.objective_value,
        "open_cells": open_cells,
        "witness_path": witness_path,
        "reward_steps": reward_steps,
        "enemy_steps": enemy_steps,
        "reward_cells": reward_cells,
        "enemy_cells": enemy_cells,
        "bfs_path": bfs_path,
        "components": components,
        "walls_by_zone": walls_by_zone,
    }


# ============================================================
# REPRESENTACIÓN ASCII
# ============================================================

def print_map(result):
    open_cells = result["open_cells"]
    path = set(result["witness_path"])
    rewards = set(result["reward_cells"])
    enemies = set(result["enemy_cells"])

    print()
    print("Leyenda: # pared | . suelo | * ruta | R premio | E enemigo")
    print()

    for r in range(ROWS):
        row = ""

        for c in range(COLS):
            cell = (r, c)

            if cell == START:
                row += "S "

            elif cell == GOAL:
                row += "G "

            elif cell in rewards:
                row += "R "

            elif cell in enemies:
                row += "E "

            elif cell in path:
                row += "* "

            elif cell in open_cells:
                row += ". "

            else:
                row += "# "

        print(row)


# ============================================================
# GUARDADO
# ============================================================

def save_results(result):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    stem = (
        f"cpsat_{ROWS}x{COLS}_seed{SEED}_{timestamp}"
    )

    txt_path = RESULTS_DIR / f"{stem}.txt"
    csv_path = RESULTS_DIR / f"{stem}.csv"

    bfs_path = result["bfs_path"]

    bfs_length = (
        len(bfs_path) - 1
        if bfs_path is not None
        else None
    )

    route_vars = sum(
        len(v)
        for v in CANDIDATES.values()
    )

    lines = [
        "====================================",
        "CASO 3 - CP-SAT",
        "NIVEL 2D BASADO EN TILES",
        "====================================",
        "",
        f"Tamaño: {ROWS}x{COLS}",
        f"START: {START}",
        f"GOAL: {GOAL}",
        f"Semilla: {SEED}",
        "",
        f"Suelo transitable: {len(result['open_cells'])}",
        f"Obstáculos: {ROWS * COLS - len(result['open_cells'])}",
        f"Obstáculos por zona: {result['walls_by_zone']}",
        f"Ruta principal: {PATH_CELLS} celdas / {PATH_CELLS - 1} movimientos",
        f"Premios: {N_REWARDS}",
        f"Enemigos: {N_ENEMIES}",
        f"Variables de ruta tras poda: {route_vars}",
        "",
        f"Estado: {result['status']}",
        f"Objetivo (fronteras suelo/pared): {result['objective']}",
        f"Tiempo: {result['time']:.6f} s",
        f"Componentes transitables: {result['components']}",
        f"Mapa navegable START->GOAL: {bfs_path is not None}",
        f"Longitud ruta principal: {len(result['witness_path']) - 1}",
        f"Longitud mínima BFS: {bfs_length}",
        "",
        "Ruta principal:",
        str(result["witness_path"]),
        "",
        "Ruta mínima BFS:",
        str(result["bfs_path"]),
        "",
        f"Premios - pasos: {result['reward_steps']}",
        f"Premios - celdas: {result['reward_cells']}",
        "",
        f"Enemigos - pasos: {result['enemy_steps']}",
        f"Enemigos - celdas: {result['enemy_cells']}",
        "",
        "Celdas transitables:",
        str(sorted(result["open_cells"])),
    ]

    txt_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    path_cells = set(result["witness_path"])
    reward_cells = set(result["reward_cells"])
    enemy_cells = set(result["enemy_cells"])

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)

        writer.writerow(
            [
                "row",
                "col",
                "type",
            ]
        )

        for r, c in CELLS:
            cell = (r, c)

            if cell == START:
                cell_type = "START"

            elif cell == GOAL:
                cell_type = "GOAL"

            elif cell in reward_cells:
                cell_type = "REWARD"

            elif cell in enemy_cells:
                cell_type = "ENEMY"

            elif cell in path_cells:
                cell_type = "PATH"

            elif cell in result["open_cells"]:
                cell_type = "FLOOR"

            else:
                cell_type = "WALL"

            writer.writerow(
                [
                    r,
                    c,
                    cell_type,
                ]
            )

    return timestamp, txt_path, csv_path


# ============================================================
# VISUALIZACIÓN
# ============================================================

def plot_map(result, timestamp):
    # 0 = pared, 1 = suelo
    matrix = np.zeros(
        (ROWS, COLS),
        dtype=int,
    )

    for cell in result["open_cells"]:
        matrix[cell] = 1

    fig, ax = plt.subplots(
        figsize=(10, 7)
    )

    # Colores discretos: pared oscura, suelo claro.
    cmap = ListedColormap(
        [
            "#2b2b2b",
            "#f2f2f2",
        ]
    )

    ax.imshow(
        matrix,
        cmap=cmap,
        vmin=0,
        vmax=1,
    )

    # Cuadrícula de tiles.
    ax.set_xticks(
        np.arange(-0.5, COLS, 1),
        minor=True,
    )

    ax.set_yticks(
        np.arange(-0.5, ROWS, 1),
        minor=True,
    )

    ax.grid(
        which="minor",
        linewidth=1.5,
    )

    ax.tick_params(
        which="minor",
        bottom=False,
        left=False,
    )

    ax.set_xticks(range(COLS))
    ax.set_yticks(range(ROWS))

    # Ruta principal.
    path = result["witness_path"]

    xs = [cell[1] for cell in path]
    ys = [cell[0] for cell in path]

    ax.plot(
        xs,
        ys,
        marker="o",
        linewidth=2.5,
        label="Ruta principal",
    )

    # START.
    ax.scatter(
        START[1],
        START[0],
        marker="s",
        s=240,
        label="START",
        zorder=5,
    )

    # GOAL.
    ax.scatter(
        GOAL[1],
        GOAL[0],
        marker="*",
        s=330,
        label="GOAL",
        zorder=5,
    )

    # Premios.
    if result["reward_cells"]:
        reward_x = [
            cell[1]
            for cell in result["reward_cells"]
        ]

        reward_y = [
            cell[0]
            for cell in result["reward_cells"]
        ]

        ax.scatter(
            reward_x,
            reward_y,
            marker="D",
            s=180,
            label="Premio",
            zorder=6,
        )

    # Enemigos.
    if result["enemy_cells"]:
        enemy_x = [
            cell[1]
            for cell in result["enemy_cells"]
        ]

        enemy_y = [
            cell[0]
            for cell in result["enemy_cells"]
        ]

        ax.scatter(
            enemy_x,
            enemy_y,
            marker="X",
            s=210,
            label="Enemigo",
            zorder=6,
        )

    ax.set_title(
        "Caso 3 - nivel 2D generado con CP-SAT"
    )

    ax.legend(
        loc="upper right"
    )

    fig.tight_layout()

    figure_path = (
        FIGURES_DIR
        / (
            f"cpsat_{ROWS}x{COLS}_"
            f"seed{SEED}_{timestamp}.png"
        )
    )

    fig.savefig(
        figure_path,
        dpi=200,
        bbox_inches="tight",
    )

    print()
    print("Figura guardada en:")
    print(figure_path)

    plt.show()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    print("====================================")
    print("CASO 3 - CP-SAT")
    print("NIVEL 2D BASADO EN TILES")
    print("====================================")

    print()
    print(f"Tamaño: {ROWS}x{COLS}")
    print(f"Celdas: {ROWS * COLS}")
    print(f"START: {START}")
    print(f"GOAL: {GOAL}")
    print(f"Suelo objetivo: {N_OPEN}")
    print(f"Obstáculos objetivo: {N_WALLS}")
    print(
        "Obstáculos por zona:",
        N_WALLS_PER_ZONE,
    )
    print(
        f"Ruta principal: "
        f"{PATH_CELLS} celdas / "
        f"{PATH_CELLS - 1} movimientos"
    )
    print(f"Premios: {N_REWARDS}")
    print(f"Enemigos: {N_ENEMIES}")

    print()
    print(
        "Variables de ruta tras poda:",
        sum(
            len(v)
            for v in CANDIDATES.values()
        ),
    )

    result = solve_case3()

    if result is not None:
        bfs_path = result["bfs_path"]

        bfs_length = (
            len(bfs_path) - 1
            if bfs_path is not None
            else None
        )

        print()
        print("Estado:", result["status"])

        print(
            "Objetivo "
            "(fronteras suelo/pared):",
            result["objective"],
        )

        print(
            "Tiempo:",
            f"{result['time']:.6f} s",
        )

        print(
            "Obstáculos por zona:",
            result["walls_by_zone"],
        )

        print(
            "Componentes transitables:",
            result["components"],
        )

        print(
            "Mapa navegable START->GOAL:",
            bfs_path is not None,
        )

        print(
            "Longitud ruta principal:",
            len(result["witness_path"]) - 1,
        )

        print(
            "Longitud mínima BFS:",
            bfs_length,
        )

        print()
        print("Premios:")

        for step, cell in zip(
            result["reward_steps"],
            result["reward_cells"],
        ):
            print(
                f"  paso {step}: {cell}"
            )

        print()
        print("Enemigos:")

        for step, cell in zip(
            result["enemy_steps"],
            result["enemy_cells"],
        ):
            print(
                f"  paso {step}: {cell}"
            )

        print()
        print("Ruta principal:")
        print(result["witness_path"])

        print_map(result)

        (
            timestamp,
            txt_path,
            csv_path,
        ) = save_results(result)

        print()
        print("Resultados guardados:")
        print(txt_path)
        print(csv_path)

        plot_map(
            result,
            timestamp,
        )