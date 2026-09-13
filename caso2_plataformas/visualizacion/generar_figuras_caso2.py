"""Caso 2 — Generador de Figuras Académicas y Analíticas para el TFM.

Genera tres figuras visuales de rigor científico para la memoria del TFM:
1. figuras/caso2_transicion_fase_parametro_C.png:
   - Sensibilidad del parámetro de penalización C de conservación de flujo (C in [1, 3]).
   - Cumplimiento de restricciones y ratio de soluciones factibles con/sin atajo.
2. figuras/caso2_escalabilidad_rugosidad_90q_vs_5504q.png:
   - Colapso por rugosidad energética del QUBO equivalente completo (5.504 variables, 576.333 acoplamientos).
   - Atrapamiento en barreras energéticas (E_min = 103 vs 4.0) vs éxito del QUBO reducido (90 variables, TTS 1.87s).
3. figuras/caso2_cinematica_saltos_2d.png:
   - Diagrama 2D del nivel de plataformas generado con física kinemática acotada (subida <= 2, caída <= 3).
   - Parábolas de salto entre plataformas sobre la cuadrícula 18x5 y foso de lava.
"""

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Configurar rutas del repositorio
SCRIPT_DIR = Path(__file__).resolve().parent
CASO2_DIR = SCRIPT_DIR.parent
REPO_ROOT = CASO2_DIR.parent

FIGURAS_DIR = CASO2_DIR / "figuras"
RESULTADOS_DIR = CASO2_DIR / "cuantico" / "resultados"
FIGURAS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# FIGURA 1: TRANSICIÓN DE FASE DEL PESO C DE FLUJO
# =============================================================================

def generar_figura_transicion_fase_C():
    """Genera la figura de transición de fase del parámetro C a partir de datos experimentales congelados."""
    print("Generando Figura 1: Transición de Fase del Parámetro C de Flujo...")

    # Datos experimentales congelados de barrido_C_18x5_20260827_183001.txt
    c_vals = [1.0, 2.0, 3.0]
    p_fact_total = [18.0, 22.0, 26.0]
    flujo_pct = [33.0, 96.0, 98.0]
    longitud_pct = [89.0, 46.0, 41.0]
    subidas_pct = [98.0, 77.0, 85.0]
    bajadas_pct = [98.0, 65.0, 75.0]

    sin_atajo = [1, 4, 7]
    con_atajo = [17, 18, 19]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.8))
    plt.subplots_adjust(wspace=0.28, left=0.07, right=0.95, top=0.86, bottom=0.14)

    # --- Panel 1: Cumplimiento de Restricciones Individuales vs C ---
    ax1.plot(c_vals, flujo_pct, "o-", color="#e74c3c", linewidth=2.4, markersize=8, label="Conservación de Flujo")
    ax1.plot(c_vals, p_fact_total, "s-", color="#27ae60", linewidth=2.2, markersize=8, label="Factibilidad Total QUBO")
    ax1.plot(c_vals, longitud_pct, "^--", color="#3498db", linewidth=1.8, markersize=7, label="Cota de Longitud")
    ax1.plot(c_vals, subidas_pct, "d:", color="#f39c12", linewidth=1.8, markersize=7, label="Mínimo de Subidas")
    ax1.plot(c_vals, bajadas_pct, "v:", color="#9b59b6", linewidth=1.8, markersize=7, label="Mínimo de Bajadas")

    # Resaltar punto óptimo de transición C=3.0
    ax1.axvline(3.0, color="#2c3e50", linestyle="--", alpha=0.6)
    ax1.text(3.0, 12, "Frontera Óptima\n$C = 3.0$", ha="center", va="bottom", fontsize=9.5, fontweight="bold", color="#2c3e50",
             bbox=dict(boxstyle="round,pad=0.3", fc="#f8f9f9", ec="#bdc3c7"))

    ax1.set_xlabel("Peso de Penalización de Flujo ($C$)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Muestras que Cumplen la Restricción (%)", fontsize=11, fontweight="bold")
    ax1.set_title("Sensibilidad de Restricciones ante el Peso $C$\n(Colapso de flujo en $C=1.0$ vs estabilización en $C=3.0$)", fontsize=11, fontweight="bold")
    ax1.set_xticks(c_vals)
    ax1.set_xticklabels(["C = 1.0\n(Subpenalizado)", "C = 2.0\n(Transición)", "C = 3.0\n(Óptimo Calibrado)"], fontsize=9.5)
    ax1.set_ylim(5, 105)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(loc="lower left", fontsize=9, framealpha=0.95)

    # --- Panel 2: Calidad de Ruta (Soluciones sin Atajo vs con Atajo) ---
    x_pos = np.arange(len(c_vals))
    width = 0.35

    rects_sin = ax2.bar(x_pos - width/2, sin_atajo, width, label="Rutas Válidas Sin Atajo ($\\Delta L = 0$)", color="#2ecc71", edgecolor="#1e8449", linewidth=1.2)
    rects_con = ax2.bar(x_pos + width/2, con_atajo, width, label="Rutas con Atajo Inválido ($\\Delta L > 0$)", color="#e74c3c", edgecolor="#922b21", linewidth=1.2)

    ax2.set_xlabel("Configuración del Peso $C$", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Número de Muestras (de 100 lecturas)", fontsize=11, fontweight="bold")
    ax2.set_title("Eliminación de Atajos y Calidad Cinemática\n(Progresión hacia rutas válidas en $C=3.0$)", fontsize=11, fontweight="bold")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([f"C = {c}" for c in c_vals], fontsize=10, fontweight="bold")
    ax2.set_ylim(0, 24)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.legend(loc="upper left", fontsize=9.5, framealpha=0.95)

    for i in range(len(c_vals)):
        ax2.text(i - width/2, sin_atajo[i] + 0.5, f"{sin_atajo[i]}", ha="center", va="bottom", fontweight="bold", color="#1e8449", fontsize=10)
        ax2.text(i + width/2, con_atajo[i] + 0.5, f"{con_atajo[i]}", ha="center", va="bottom", fontweight="bold", color="#c0392b", fontsize=10)

    ruta_salida = FIGURAS_DIR / "caso2_transicion_fase_parametro_C.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


# =============================================================================
# FIGURA 2: COLAPSO POR RUGOSIDAD ENERGÉTICA (90 VARS vs 5.504 VARS)
# =============================================================================

def generar_figura_escalabilidad_y_rugosidad():
    """Genera la comparativa cuantitativa entre el QUBO reducido y el QUBO equivalente masivo."""
    print("Generando Figura 2: Escalabilidad y Rugosidad Energética (90Q vs 5.504Q)...")

    modelos = ["QUBO Reducido\n(18x5, 90 vars)", "QUBO Equivalente Completo\n(18x5, 5.504 vars)"]

    # Datos empíricos
    vars_totales = [90, 5504]
    terminos_cuad = [278, 576333]
    e_min_alcanzada = [0.0, 103.0]
    e_optima_teorica = [0.0, 4.0]
    p_opt = [31.0, 0.0]

    fig, (ax_vars, ax_e, ax_tts) = plt.subplots(1, 3, figsize=(16, 5.5))
    plt.subplots_adjust(wspace=0.32, left=0.06, right=0.96, top=0.86, bottom=0.14)

    # --- Panel A: Dimensión y Densidad de Acoplamientos (Escala Log) ---
    x_m = np.arange(len(modelos))
    w = 0.35

    ax_vars.bar(x_m - w/2, vars_totales, w, label="Variables Binarias ($N$)", color="#34495e", edgecolor="#1a252f")
    ax_vars.bar(x_m + w/2, terminos_cuad, w, label="Términos Cuadráticos ($Q_{ij}$)", color="#e67e22", edgecolor="#b9770e")
    ax_vars.set_yscale("log")
    ax_vars.set_ylabel("Cantidad (Escala Logarítmica)", fontsize=10, fontweight="bold")
    ax_vars.set_title("Explosión Combinatoria de Variables\n(Mapeo ingenuo vs Reformulación reducida)", fontsize=11, fontweight="bold")
    ax_vars.set_xticks(x_m)
    ax_vars.set_xticklabels(modelos, fontsize=9.5, fontweight="bold")
    ax_vars.set_ylim(10, 2e6)
    ax_vars.grid(axis="y", which="both", linestyle="--", alpha=0.4)
    ax_vars.legend(loc="upper left", fontsize=9)

    ax_vars.text(0 - w/2, vars_totales[0] * 1.5, "90", ha="center", va="bottom", fontweight="bold", fontsize=9.5)
    ax_vars.text(0 + w/2, terminos_cuad[0] * 1.5, "278", ha="center", va="bottom", fontweight="bold", fontsize=9.5)
    ax_vars.text(1 - w/2, vars_totales[1] * 1.5, "5.504", ha="center", va="bottom", fontweight="bold", fontsize=9.5)
    ax_vars.text(1 + w/2, terminos_cuad[1] * 1.5, "576.333", ha="center", va="bottom", fontweight="bold", fontsize=9.5)

    # --- Panel B: Atrapamiento en Barreras Energéticas (Landscape Ruggedness) ---
    width = 0.35
    ax_e.bar(x_m - width/2, e_optima_teorica, width, label="Energía Óptima Global ($E^*$)", color="#27ae60", edgecolor="#196f3d")
    ax_e.bar(x_m + width/2, e_min_alcanzada, width, label="Mínimo Alcanzado por SA ($E_{\\text{min}}$)", color="#c0392b", edgecolor="#78281f")

    ax_e.set_ylabel("Energía QUBO", fontsize=10, fontweight="bold")
    ax_e.set_title("Colapso por Rugosidad del Paisaje Energético\n(Barreras infranqueables en 5.504 variables)", fontsize=11, fontweight="bold")
    ax_e.set_xticks(x_m)
    ax_e.set_xticklabels(modelos, fontsize=9.5, fontweight="bold")
    ax_e.set_ylim(-5, 125)
    ax_e.grid(axis="y", linestyle="--", alpha=0.4)
    ax_e.legend(loc="upper left", fontsize=9)

    ax_e.text(0 + width/2, 3, "E = 0.0\n(ÓPTIMO)", ha="center", va="bottom", fontweight="bold", color="#196f3d", fontsize=9)
    ax_e.text(1 + width/2, 105, "E = 103.0\n(ΔE = +99.0)", ha="center", va="bottom", fontweight="bold", color="#c0392b", fontsize=9)

    # Anotación explicativa
    ax_e.text(1, 40, "Atrapamiento severo en\nmínimos locales espurios\n($p_{\\text{opt}} = 0.0\\%$)",
              ha="center", va="center", color="#78281f", fontweight="bold", fontsize=8.5,
              bbox=dict(boxstyle="round,pad=0.3", fc="#fdedec", ec="#e74c3c"))

    # --- Panel C: Time-To-Target TTS_99 ---
    tts_vals = [1.875, 1e4]  # 1e4 simbólico para infinito con anotación
    colores_tts = ["#27ae60", "#c0392b"]
    ax_tts.bar(modelos, tts_vals, color=colores_tts, width=0.45, edgecolor="#2c3e50")
    ax_tts.set_yscale("log")
    ax_tts.set_ylabel("Time-To-Target $TTS_{99}$ (segundos, log)", fontsize=10, fontweight="bold")
    ax_tts.set_title("Viabilidad Práctica de Resolución\n($TTS_{99}$ acotado vs Divergencia)", fontsize=11, fontweight="bold")
    ax_tts.set_ylim(0.1, 5e4)
    ax_tts.grid(axis="y", which="both", linestyle="--", alpha=0.4)

    ax_tts.text(0, 2.5, "1.88 s\n(50 sweeps)", ha="center", va="bottom", fontweight="bold", color="#196f3d", fontsize=9.5)
    ax_tts.text(1, 1.2e4, "$TTS = \\infty$\n(Muestras = 0%)", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=9.5)

    ruta_salida = FIGURAS_DIR / "caso2_escalabilidad_rugosidad_90q_vs_5504q.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


# =============================================================================
# FIGURA 3: DIAGRAMA CINEMÁTICO 2D DE SALTOS Y FÍSICA ACOTADA
# =============================================================================

def generar_figura_cinematica_saltos_2d():
    """Genera la visualización 2D de la cinemática de saltos y física acotada."""
    print("Generando Figura 3: Cinemática de Saltos 2D y Parábolas de Nivel...")

    # Cargar el JSON del nivel congelado
    json_path = RESULTADOS_DIR / "caso2_nivel_blender_qubo_reducido_18x5.json"
    if not json_path.exists():
        raise FileNotFoundError(f"No se encontró {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ancho = data["escenario"]["ancho"]
    alto = data["escenario"]["alto"]
    start = (data["start"]["x"], data["start"]["y"])
    goal = (data["goal"]["x"], data["goal"]["y"])
    plataformas = [(p["x"], p["y"]) for p in data["plataformas"]]
    ruta = [(p["x"], p["y"]) for p in data["ruta"]]

    fig, ax = plt.subplots(figsize=(15, 6.2))
    plt.subplots_adjust(left=0.06, right=0.96, top=0.88, bottom=0.15)

    # 1. Fondo de cuadrícula y foso de lava inferior
    ax.set_facecolor("#1a1a24")
    foso_lava = patches.Rectangle((-0.5, -0.5), ancho, 1.0, facecolor="#c0392b", alpha=0.35, hatch="///", edgecolor="#e74c3c")
    ax.add_patch(foso_lava)
    ax.text(ancho / 2.0, -0.05, "FOSO DE LAVA INFERIOR (CAÍDA MORTAL)", color="#e74c3c", fontweight="bold", fontsize=10, ha="center")

    # Rejilla
    ax.set_xticks(range(ancho))
    ax.set_yticks(range(alto))
    ax.grid(True, color="#34495e", linestyle=":", alpha=0.6)

    # 2. Dibujar plataformas de ancho 2
    for x, y in plataformas:
        # Plataforma rectangular biselada
        plat_rect = patches.Rectangle((x - 0.4, y - 0.25), 1.8, 0.4, linewidth=2, edgecolor="#1abc9c", facecolor="#16a085", zorder=3)
        ax.add_patch(plat_rect)
        ax.text(x + 0.5, y + 0.35, f"P({x},{y})", color="#a3e4d7", fontsize=9, fontweight="bold", ha="center")

    # Start y Goal especiales
    start_rect = patches.Rectangle((start[0] - 0.4, start[1] - 0.25), 1.8, 0.4, linewidth=2.5, edgecolor="#2ecc71", facecolor="#27ae60", zorder=3)
    ax.add_patch(start_rect)
    ax.text(start[0] + 0.5, start[1] + 0.35, "START (0,2)", color="#a9dfbf", fontsize=9.5, fontweight="bold", ha="center")

    goal_rect = patches.Rectangle((goal[0] - 0.4, goal[1] - 0.25), 1.8, 0.4, linewidth=2.5, edgecolor="#f1c40f", facecolor="#f39c12", zorder=3)
    ax.add_patch(goal_rect)
    ax.text(goal[0] + 0.5, goal[1] + 0.35, "GOAL (17,2)", color="#f9e79f", fontsize=9.5, fontweight="bold", ha="center")

    # 3. Dibujar arcos parabólicos balísticos de salto
    for i in range(len(ruta) - 1):
        x1, y1 = ruta[i]
        x2, y2 = ruta[i + 1]

        # Trayectoria parabólica: y(x) = y1 + (y2 - y1)*t + 4*H_apex*t*(1 - t)
        xs = np.linspace(x1 + 0.5, x2 + 0.5, 50)
        t = np.linspace(0, 1, 50)
        h_apex = 0.85 if y2 >= y1 else 0.50
        ys = y1 + (y2 - y1) * t + 4 * h_apex * t * (1 - t)

        dx = x2 - x1
        dy = y2 - y1
        tipo_salto = f"Subida (+{dy})" if dy > 0 else (f"Caída ({dy})" if dy < 0 else "Plano (0)")
        color_arco = "#f39c12" if dy > 0 else ("#3498db" if dy < 0 else "#ecf0f1")

        ax.plot(xs, ys, color=color_arco, linewidth=2.5, linestyle="-", zorder=4)

        # Flecha direccional en el centro del arco
        mid_idx = len(xs) // 2
        ax.annotate(
            "",
            xy=(xs[mid_idx + 1], ys[mid_idx + 1]),
            xytext=(xs[mid_idx], ys[mid_idx]),
            arrowprops=dict(arrowstyle="->", color=color_arco, lw=2.5),
            zorder=5,
        )

        # Etiqueta de la física acotada
        ax.text(
            (x1 + x2)/2.0 + 0.5, np.max(ys) + 0.25,
            f"Salto {i+1}\nΔx={dx}, Δy={dy:+} ({tipo_salto})",
            color=color_arco, fontsize=8, fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", fc="#2c3e50", ec=color_arco, alpha=0.9),
        )

    # Cuadro informativo de reglas cinemáticas acotadas
    reglas_texto = (
        "Restricciones Cinemáticas Físicas:\n"
        "• Salto Horizontal: Δx ∈ [2, 4] casillas\n"
        "• Subida Máxima Vertical: Δy ≤ +2\n"
        "• Caída Máxima Balística: Δy ≥ -3\n"
        "• Prevención de Atajos: Grafo DAG acotado\n"
        "• Solución QUBO: 5 saltos válidos conectados"
    )
    ax.text(
        0.02, 0.95, reglas_texto, transform=ax.transAxes, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#2c3e50", edgecolor="#1abc9c", alpha=0.95),
        fontsize=9.5, fontweight="bold", color="#ecf0f1"
    )

    ax.set_xlim(-0.8, ancho + 0.8)
    ax.set_ylim(-0.8, alto + 0.8)
    ax.set_xlabel("Eje Horizontal de Progresión ($X$)", fontsize=11, fontweight="bold", color="white")
    ax.set_ylabel("Altura de Plataforma ($Y$)", fontsize=11, fontweight="bold", color="white")
    ax.tick_params(colors="white")
    ax.set_title("Cinemática de Saltos y Ruta Óptima sobre la Cuadrícula $18 \\times 5$\n(Formulación QUBO Reducida + Simulated Annealing con Físicas Acotadas)", fontsize=12, fontweight="bold", color="white")

    ruta_salida = FIGURAS_DIR / "caso2_cinematica_saltos_2d.png"
    plt.savefig(ruta_salida, dpi=300, facecolor=fig.get_facecolor())
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


def main():
    print("=" * 70)
    print("GENERANDO SUITE DE FIGURAS ANALÍTICAS PARA CASO 2 (TFM)")
    print("=" * 70)
    generar_figura_transicion_fase_C()
    generar_figura_escalabilidad_y_rugosidad()
    generar_figura_cinematica_saltos_2d()
    print("Figuras de Caso 2 generadas exitosamente.\n")


if __name__ == "__main__":
    main()
