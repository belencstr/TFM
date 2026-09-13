"""Caso 1 — Orquestador Unificado de Figuras Cuánticas y Blender (TFM).

Este script permite generar y verificar de forma reproducible todo el conjunto de
figuras científicas y visualizaciones 3D para el Caso 1:
1. Visualizaciones 3D en Blender:
   - Diorama del mapa mínimo cuántico (k=2, monedas óptimas QUBO/QAOA).
   - Diorama de Mapa A (k=5), completando el trío canónico con B y C.
2. Formulaciones QUBO:
   - Heatmap de matrices Q (20x20 directo vs 4x4 compacto) y grafo de interacción Ising.
   - Espectro discreto de energías de los 16 estados y análisis de dilución de Hilbert.
3. Algoritmo Variacional QAOA:
   - Paisaje 2D de energía y probabilidad con trayectoria de convergencia COBYLA.
   - Histograma de colapso de estados cuánticos y amplificación de óptimos vs shots.
   - Diagrama vectorial del circuito cuántico ansatz (p=1).
   - Curvas de escalabilidad y stress test de disparos (20Q vs 4Q).

EJECUCIÓN:
  python visualizacion/generar_todas_figuras_cuanticas.py
"""

from pathlib import Path
import subprocess
import sys
import time

SCRIPT_DIR = Path(__file__).resolve().parent
CASO1_DIR = SCRIPT_DIR.parent
FIGURAS_DIR = CASO1_DIR / "figuras"

FIGURAS_REQUERIDAS = [
    # Blender
    ("caso1_blender_qubo_render_mapa_min_k2.png", "Blender 3D", "Diorama 3D del mapa cuántico con monedas óptimas (QUBO/QAOA)"),
    ("caso1_blender_render_mapa_min_k2.png", "Blender 3D", "Render 3D canónico del mapa mínimo (k=2)"),
    ("caso1_blender_render_mapa_a_k5.png", "Blender 3D", "Render 3D diorama de Mapa A (Espacio Abierto, k=5)"),
    ("caso1_blender_render_mapa_b_k5.png", "Blender 3D", "Render 3D diorama de Mapa B (Obstáculos, k=5)"),
    ("caso1_blender_render_mapa_c_k5.png", "Blender 3D", "Render 3D diorama de Mapa C (Laberinto, k=5)"),
    # QUBO
    ("qubo_matrices_comparativa_20q_vs_4q.png", "QUBO", "Matrices Q (20Q vs 4Q) y Grafo de Acoplamiento Ising"),
    ("qubo_espectro_energias_y_factibilidad.png", "QUBO", "Espectro de energías de los 16 estados y dilución de Hilbert"),
    # QAOA
    ("qaoa_paisaje_energia_y_optimizacion.png", "QAOA", "Paisaje 2D de energía <H_C> y P_opt con trayectoria COBYLA"),
    ("qaoa_distribucion_probabilidades_estados.png", "QAOA", "Histograma de probabilidades cuánticas vs superposición uniforme"),
    ("qaoa_circuito_cuantico_4q.png", "QAOA", "Diagrama vectorial del circuito cuántico QAOA (p=1)"),
    ("qaoa_stress_test_shots_escalabilidad.png", "QAOA", "Curvas de escalabilidad y probabilidad empírica vs shots"),
    ("comparativa_qaoa_20q_vs_4q.png", "QAOA Comparativa", "Informe visual comparativo 20Q vs 4Q (Hilbert, tiempo, TTS99)"),
]


def ejecutar_script_python(ruta_script):
    """Ejecuta un script auxiliar usando el intérprete de Python actual."""
    nombre = Path(ruta_script).name
    print(f"\n[EJECUTANDO] {nombre}...")
    t0 = time.time()
    res = subprocess.run([sys.executable, str(ruta_script)], capture_output=True, text=True)
    duracion = time.time() - t0
    if res.returncode != 0:
        print(f"Error al ejecutar {nombre}:")
        print(res.stderr)
        return False
    print(f"[OK] {nombre} completado en {duracion:.2f} s.")
    if res.stdout.strip():
        for linea in res.stdout.strip().split("\n"):
            if "->" in linea or "guardada" in linea:
                print(f"  {linea.strip()}")
    return True


def verificar_figuras():
    """Comprueba la existencia y tamaño de todas las figuras requeridas."""
    print("\n" + "=" * 90)
    print("VERIFICACIÓN DE FIGURAS — CASO 1: PARTE CUÁNTICA Y BLENDER")
    print("=" * 90)
    print(f"{'Archivo':<46} | {'Módulo':<16} | {'Tamaño':<10} | {'Estado'}")
    print("-" * 90)

    todas_ok = True
    for nombre, modulo, desc in FIGURAS_REQUERIDAS:
        ruta = FIGURAS_DIR / nombre
        if ruta.exists() and ruta.stat().st_size > 0:
            size_kb = ruta.stat().st_size / 1024.0
            if size_kb > 1024:
                size_str = f"{size_kb / 1024.0:.2f} MB"
            else:
                size_str = f"{size_kb:.1f} KB"
            print(f"{nombre:<46} | {modulo:<16} | {size_str:<10} | OK")
        else:
            print(f"{nombre:<46} | {modulo:<16} | {'---':<10} | FALTA")
            todas_ok = False

    print("=" * 90)
    return todas_ok


def main():
    print("=" * 90)
    print("ORQUESTADOR DE FIGURAS CUÁNTICAS Y BLENDER — CASO 1")
    print("=" * 90)

    # 1. Generar figuras QUBO
    script_qubo = SCRIPT_DIR / "generar_figuras_qubo.py"
    if script_qubo.exists():
        ejecutar_script_python(script_qubo)

    # 2. Generar figuras QAOA
    script_qaoa = SCRIPT_DIR / "generar_figuras_qaoa.py"
    if script_qaoa.exists():
        ejecutar_script_python(script_qaoa)

    # 3. Comprobar catálogo completo
    exito = verificar_figuras()
    if exito:
        print("\n¡Todas las figuras cuánticas y de Blender del Caso 1 están generadas y verificadas!")
        print(f"Directorio de figuras: {FIGURAS_DIR}\n")
    else:
        print("\nAtención: Algunas figuras no se encontraron.")
        sys.exit(1)


if __name__ == "__main__":
    main()
