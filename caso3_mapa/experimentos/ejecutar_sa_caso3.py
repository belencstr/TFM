"""Experimento: Ejecución de Simulated Annealing sobre el QUBO del Caso 3.

Compara la solución obtenida por Simulated Annealing frente al óptimo
clásico de CP-SAT v3 y analiza:
- Tasa de satisfacción de restricciones (START, GOAL y zonas).
- Tasa de navegabilidad (existencia de ruta START->GOAL según BFS).
- Coherencia espacial (número de fronteras suelo/pared vs Ising).
- Número de componentes conexas transitables.
- Tiempos de ejecución.
"""

from datetime import datetime
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from formulacion.qubo_caso3 import construir_qubo_geometria, ROWS, COLS, START, GOAL
from solvers.simulated_annealing_caso3 import resolver_qubo_sa

RESULTADOS_DIR = BASE_DIR / "experimentos" / "resultados"
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)


def imprimir_mapa_ascii(open_cells, camino_bfs=None):
    path_set = set(camino_bfs) if camino_bfs else set()
    print()
    print("Leyenda: S Inicio | G Meta | * Camino BFS | . Suelo | # Muro")
    print()
    for r in range(ROWS):
        fila = ""
        for c in range(COLS):
            cell = (r, c)
            if cell == START:
                fila += "S "
            elif cell == GOAL:
                fila += "G "
            elif cell in path_set:
                fila += "* "
            elif cell in open_cells:
                fila += ". "
            else:
                fila += "# "
        print(fila)
    print()


def ejecutar_experimento_sa(
    peso_frontera=1.0,
    peso_zona=12.0,
    peso_start_goal=50.0,
    num_reads=100,
    num_sweeps=1000,
    seed=42,
):
    print("=" * 65)
    print("CASO 3 — EXPERIMENTO SIMULATED ANNEALING SOBRE QUBO")
    print("=" * 65)

    print(f"Cuadrícula: {ROWS}x{COLS} ({ROWS*COLS} variables binarias)")
    print(f"Parámetros QUBO: peso_frontera={peso_frontera}, peso_zona={peso_zona}, peso_sg={peso_start_goal}")
    print(f"Parámetros SA: reads={num_reads}, sweeps={num_sweeps}, seed={seed}")
    print()

    qubo = construir_qubo_geometria(
        peso_frontera=peso_frontera,
        peso_zona=peso_zona,
        peso_start_goal=peso_start_goal,
    )

    print(f"Variables QUBO: {qubo['num_vars']}")
    print(f"Términos cuadráticos: {len(qubo['cuadratico'])}")
    print(f"Constante del Hamiltoniano: {qubo['constante']:.2f}")
    print()
    print("Ejecutando Simulated Annealing...")

    res = resolver_qubo_sa(qubo, num_reads=num_reads, num_sweeps=num_sweeps, seed=seed)

    mejor = res["mejor_muestra"]

    print("=" * 65)
    print("RESULTADOS OBTENIDOS")
    print("=" * 65)
    print(f"Tiempo SA: {res['tiempo_segundos']:.4f} s")
    print(f"Energía mejor muestra: {mejor['energia']:.4f} (raw: {mejor['energia_raw']:.4f})")
    print(f"Fronteras suelo/pared reales: {mejor['fronteras']}")
    print(f"Cumple START y GOAL: {mejor['start_ok']} y {mejor['goal_ok']}")
    print(f"Cumple partición en zonas (5 muros c/u): {mejor['zonas_ok']} ({mejor['muros_por_zona']})")
    print(f"Navegable START->GOAL (BFS): {mejor['es_navegable']} (Longitud: {mejor['longitud_bfs']})")
    print(f"Componentes conexas: {mejor['componentes']} (Conectividad perfecta: {mejor['componentes'] == 1})")
    print(f"Tasa factibilidad zonas: {res['tasa_factibilidad_zonas']*100:.1f}%")
    print(f"Tasa mapas navegables: {res['tasa_factibilidad_navegable']*100:.1f}%")

    imprimir_mapa_ascii(mejor["open_cells"], mejor["camino_bfs"])

    # Guardar en archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_txt = RESULTADOS_DIR / f"qubo_sa_{ROWS}x{COLS}_seed{seed}_{timestamp}.txt"

    lineas = [
        "============================================================",
        "CASO 3 — SIMULATED ANNEALING SOBRE MODELO QUBO",
        "============================================================",
        f"Fecha: {timestamp}",
        f"Cuadrícula: {ROWS}x{COLS} ({ROWS*COLS} celdas)",
        f"START: {START}, GOAL: {GOAL}",
        f"Semilla: {seed}",
        f"Num Reads: {num_reads}, Num Sweeps: {num_sweeps}",
        f"Pesos QUBO: frontera={peso_frontera}, zona={peso_zona}, start_goal={peso_start_goal}",
        "",
        f"Variables binarias: {qubo['num_vars']}",
        f"Términos cuadráticos: {len(qubo['cuadratico'])}",
        f"Tiempo de resolución: {res['tiempo_segundos']:.4f} s",
        "",
        f"Energía de la mejor muestra: {mejor['energia']:.4f}",
        f"Fronteras suelo/pared (Ising): {mejor['fronteras']}",
        f"Muros totales: {mejor['num_walls']} (Esperado: 20)",
        f"Suelo total: {mejor['num_open']} (Esperado: 28)",
        f"Distribución por zonas: {mejor['muros_por_zona']}",
        f"Factible en zonas: {mejor['zonas_ok']}",
        f"Navegable START->GOAL: {mejor['es_navegable']}",
        f"Longitud camino BFS: {mejor['longitud_bfs']}",
        f"Componentes transitables: {mejor['componentes']}",
        f"Tasa factibilidad zonas: {res['tasa_factibilidad_zonas']*100:.1f}%",
        f"Tasa navegabilidad válida: {res['tasa_factibilidad_navegable']*100:.1f}%",
        "",
        "Celdas transitables de la mejor muestra:",
        str(sorted(mejor["open_cells"])),
        "",
        "Camino mínimo BFS:",
        str(mejor["camino_bfs"]),
    ]

    archivo_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe guardado en: {archivo_txt}")

    return res, archivo_txt


if __name__ == "__main__":
    ejecutar_experimento_sa()
