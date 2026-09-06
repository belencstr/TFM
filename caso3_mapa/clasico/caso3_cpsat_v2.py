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

# Esquinas opuestas: la distancia Manhattan mínima es 12.
START = (0, 0)
GOAL = (5, 7)

# Ruta principal: 13 celdas = 12 movimientos.
PATH_CELLS = 13

# Cuatro zonas 3x4, con cinco obstáculos en cada una.
N_WALLS_PER_ZONE = 5

# Gameplay:
# - 2 premios sobre la ruta principal.
# - 1 enemigo sobre la ruta principal.
# - 1 enemigo en una rama secundaria sin salida.
N_REWARDS = 2
N_ROUTE_ENEMIES = 1

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
    Conserva solo celdas compatibles con el paso t de una ruta
    de longitud fija START->GOAL.

    Como la ruta tiene exactamente la longitud Manhattan mínima,
    la poda asigna cada celda posible a un único paso.
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
# CANDIDATAS PARA LA RAMA SECUNDARIA
# ============================================================

# La rama no puede quedar pegada a START ni a GOAL.
# El enemigo secundario aparecerá en esta celda final.
BRANCH_CANDIDATES = [
    cell
    for cell in CELLS
    if manhattan(START, cell) >= 3
    and manhattan(cell, GOAL) >= 3
]


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

    # Cinco paredes exactas en cada zona 3x4.
    for zone_cells in ZONES.values():
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

    # Exactamente una posición por paso.
    for t in range(PATH_CELLS):
        model.add(
            sum(q[t, cell] for cell in CANDIDATES[t]) == 1
        )

    model.add(q[0, START] == 1)
    model.add(q[PATH_CELLS - 1, GOAL] == 1)

    # La ruta solo puede atravesar suelo.
    for (t, cell), variable in q.items():
        model.add(variable <= x[cell])

    # p[cell] = 1 si la celda pertenece a la ruta principal.
    p = {}

    for cell in CELLS:
        p[cell] = model.new_bool_var(
            f"path_{cell[0]}_{cell[1]}"
        )

        appearances = [
            q[t, cell]
            for t in range(PATH_CELLS)
            if (t, cell) in q
        ]

        if appearances:
            model.add(
                p[cell] == sum(appearances)
            )
        else:
            model.add(p[cell] == 0)

    # No repetir una celda.
    for cell in CELLS:
        appearances = [
            q[t, cell]
            for t in range(PATH_CELLS)
            if (t, cell) in q
        ]

        if len(appearances) > 1:
            model.add(sum(appearances) <= 1)

    # Continuidad entre pasos consecutivos.
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
    # 3. RAMA SECUNDARIA CON CALLEJÓN SIN SALIDA
    # --------------------------------------------------------
    # branch[cell] = 1 si cell es el final de la rama secundaria.
    #
    # Esa celda:
    # - es transitable,
    # - no forma parte de la ruta principal,
    # - tiene exactamente un vecino transitable,
    # - ese único vecino pertenece a la ruta principal.
    #
    # Por tanto se comporta como un pequeño desvío opcional
    # terminado en un callejón sin salida.

    branch = {
        cell: model.new_bool_var(
            f"branch_{cell[0]}_{cell[1]}"
        )
        for cell in BRANCH_CANDIDATES
    }

    model.add(
        sum(branch.values()) == 1
    )

    for cell, branch_var in branch.items():
        model.add(
            branch_var <= x[cell]
        )

        # La celda final de la rama no pertenece a la ruta.
        model.add(
            branch_var + p[cell] <= 1
        )

        # Si es la rama, tiene un único vecino transitable.
        model.add(
            sum(x[nxt] for nxt in neighbors(cell)) == 1
        ).only_enforce_if(branch_var)

        # Y ese único vecino pertenece a la ruta principal.
        model.add(
            sum(p[nxt] for nxt in neighbors(cell)) == 1
        ).only_enforce_if(branch_var)

    # --------------------------------------------------------
    # 4. PREMIOS Y ENEMIGO DE RUTA
    # --------------------------------------------------------
    # Los premios y el enemigo principal se indexan por paso.

    reward = {
        t: model.new_bool_var(f"reward_{t}")
        for t in range(PATH_CELLS)
    }

    route_enemy = {
        t: model.new_bool_var(f"route_enemy_{t}")
        for t in range(PATH_CELLS)
    }

    model.add(
        sum(reward.values()) == N_REWARDS
    )

    model.add(
        sum(route_enemy.values()) == N_ROUTE_ENEMIES
    )

    # START y GOAL libres.
    for t in [0, PATH_CELLS - 1]:
        model.add(reward[t] == 0)
        model.add(route_enemy[t] == 0)

    # Premio y enemigo no pueden ocupar el mismo paso.
    for t in range(PATH_CELLS):
        model.add(
            reward[t] + route_enemy[t] <= 1
        )

    # Elementos de ruta no consecutivos.
    for t in range(PATH_CELLS - 1):
        model.add(
            reward[t]
            + route_enemy[t]
            + reward[t + 1]
            + route_enemy[t + 1]
            <= 1
        )

    # Progresión sencilla:
    # premio temprano -> enemigo -> premio tardío.
    model.add(
        sum(reward[t] for t in range(2, 5)) == 1
    )

    model.add(
        sum(route_enemy[t] for t in range(5, 8)) == 1
    )

    model.add(
        sum(reward[t] for t in range(8, 11)) == 1
    )

    # --------------------------------------------------------
    # 5. OBJETIVO: COHERENCIA ESPACIAL
    # --------------------------------------------------------
    # Minimiza fronteras suelo/pared.
    # La distribución obligatoria por zonas evita que todas las
    # paredes se acumulen en un único extremo del mapa.

    boundary = {}

    for idx, (a, b) in enumerate(EDGES):
        boundary[idx] = model.new_bool_var(
            f"boundary_{idx}"
        )

        model.add_abs_equality(
            boundary[idx],
            x[a] - x[b]
        )

    model.minimize(
        sum(boundary.values())
    )

    # --------------------------------------------------------
    # 6. SOLVER
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

    status_name = status_names.get(
        status,
        str(status),
    )

    if status not in (
        cp_model.FEASIBLE,
        cp_model.OPTIMAL,
    ):
        print("No se ha encontrado solución.")
        print("Estado:", status_name)
        return None

    # --------------------------------------------------------
    # 7. EXTRAER SOLUCIÓN
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

    route_enemy_steps = [
        t
        for t in range(PATH_CELLS)
        if solver.boolean_value(route_enemy[t])
    ]

    reward_cells = [
        witness_path[t]
        for t in reward_steps
    ]

    route_enemy_cells = [
        witness_path[t]
        for t in route_enemy_steps
    ]

    branch_cell = next(
        cell
        for cell, variable in branch.items()
        if solver.boolean_value(variable)
    )

    branch_attachment = next(
        nxt
        for nxt in neighbors(branch_cell)
        if nxt in open_cells
    )

    # El segundo enemigo ocupa automáticamente el final
    # de la rama secundaria.
    branch_enemy_cell = branch_cell

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
        "reward_cells": reward_cells,
        "route_enemy_steps": route_enemy_steps,
        "route_enemy_cells": route_enemy_cells,
        "branch_cell": branch_cell,
        "branch_attachment": branch_attachment,
        "branch_enemy_cell": branch_enemy_cell,
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
    route_enemies = set(result["route_enemy_cells"])
    branch_enemy = result["branch_enemy_cell"]

    print()
    print(
        "Leyenda: # pared | . suelo | * ruta | "
        "R premio | E enemigo | B enemigo en rama"
    )
    print()

    for r in range(ROWS):
        row = ""

        for c in range(COLS):
            cell = (r, c)

            if cell == START:
                row += "S "

            elif cell == GOAL:
                row += "G "

            elif cell == branch_enemy:
                row += "B "

            elif cell in rewards:
                row += "R "

            elif cell in route_enemies:
                row += "E "

            elif cell in path:
                row += "* "

            elif cell in open_cells:
                row += ". "

            else:
                row += "# "

        print(row)


# ============================================================
# GUARDADO DE RESULTADOS
# ============================================================

def save_results(result):
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    stem = (
        f"cpsat_{ROWS}x{COLS}_"
        f"seed{SEED}_{timestamp}"
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
        (
            f"Ruta principal: {PATH_CELLS} celdas / "
            f"{PATH_CELLS - 1} movimientos"
        ),
        f"Premios: {N_REWARDS}",
        "Enemigos totales: 2",
        "  - Enemigos en ruta: 1",
        "  - Enemigos en rama secundaria: 1",
        f"Variables de ruta tras poda: {route_vars}",
        f"Candidatas de rama: {len(BRANCH_CANDIDATES)}",
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
        f"Enemigo de ruta - pasos: {result['route_enemy_steps']}",
        f"Enemigo de ruta - celdas: {result['route_enemy_cells']}",
        "",
        f"Rama secundaria - conexión: {result['branch_attachment']}",
        f"Rama secundaria - final: {result['branch_cell']}",
        f"Enemigo de rama: {result['branch_enemy_cell']}",
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
    route_enemy_cells = set(result["route_enemy_cells"])
    branch_enemy_cell = result["branch_enemy_cell"]

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

            elif cell == branch_enemy_cell:
                cell_type = "BRANCH_ENEMY"

            elif cell in reward_cells:
                cell_type = "REWARD"

            elif cell in route_enemy_cells:
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
    matrix = np.zeros(
        (ROWS, COLS),
        dtype=int,
    )

    for cell in result["open_cells"]:
        matrix[cell] = 1

    fig, ax = plt.subplots(
        figsize=(10, 7)
    )

    cmap = ListedColormap(
        [
            "#2b2b2b",  # pared
            "#f2f2f2",  # suelo
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
        zorder=4,
    )

    # Rama secundaria.
    attachment = result["branch_attachment"]
    branch_cell = result["branch_cell"]

    ax.plot(
        [
            attachment[1],
            branch_cell[1],
        ],
        [
            attachment[0],
            branch_cell[0],
        ],
        linestyle="--",
        linewidth=2.5,
        label="Rama secundaria",
        zorder=4,
    )

    # START.
    ax.scatter(
        START[1],
        START[0],
        marker="s",
        s=240,
        label="START",
        zorder=6,
    )

    # GOAL.
    ax.scatter(
        GOAL[1],
        GOAL[0],
        marker="*",
        s=330,
        label="GOAL",
        zorder=6,
    )

    # Premios.
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
        zorder=7,
    )

    # Enemigo de ruta.
    route_enemy_x = [
        cell[1]
        for cell in result["route_enemy_cells"]
    ]

    route_enemy_y = [
        cell[0]
        for cell in result["route_enemy_cells"]
    ]

    ax.scatter(
        route_enemy_x,
        route_enemy_y,
        marker="X",
        s=220,
        label="Enemigo en ruta",
        zorder=7,
    )

    # Enemigo de rama.
    ax.scatter(
        branch_cell[1],
        branch_cell[0],
        marker="X",
        s=260,
        label="Enemigo en rama",
        zorder=8,
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
    print("Enemigos: 2 (1 ruta + 1 rama)")

    print()
    print(
        "Variables de ruta tras poda:",
        sum(
            len(v)
            for v in CANDIDATES.values()
        ),
    )

    print(
        "Candidatas de rama:",
        len(BRANCH_CANDIDATES),
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
        print("Enemigo de ruta:")

        for step, cell in zip(
            result["route_enemy_steps"],
            result["route_enemy_cells"],
        ):
            print(
                f"  paso {step}: {cell}"
            )

        print()
        print("Rama secundaria:")
        print(
            "  conexión con ruta:",
            result["branch_attachment"],
        )
        print(
            "  final de rama:",
            result["branch_cell"],
        )
        print(
            "  enemigo:",
            result["branch_enemy_cell"],
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