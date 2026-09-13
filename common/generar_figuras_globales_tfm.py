"""Nivel Global TFM — Generador de Figuras de Síntesis y Arquitectura Metodológica.

Genera dos figuras sinópticas fundamentales para la memoria del TFM:
1. doc_tfm/figuras_globales/tfm_sintesis_comparativa_tres_casos.png:
   - Taxonomía y progresión de complejidad de los tres casos del TFM (Caso 1, Caso 2, Caso 3).
   - Espacio de búsqueda, variables cuánticas, solvers clásicos vs cuánticos y viabilidad (TTS_99).
2. doc_tfm/figuras_globales/tfm_pipeline_metodologico_hibrido.png:
   - Diagrama formal de bloques del pipeline metodológico híbrido PCG cuántico-clásico.
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
FIGURAS_DIR = REPO_ROOT / "doc_tfm" / "figuras_globales"
FIGURAS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# FIGURA 1: SÍNTESIS COMPARATIVA DE LOS TRES CASOS DEL TFM
# =============================================================================

def generar_figura_sintesis_tres_casos():
    """Genera la infografía comparativa exhaustiva que resume los 3 casos de la tesis."""
    print("Generando Figura Global 1: Síntesis Comparativa de los Tres Casos del TFM...")

    fig = plt.figure(figsize=(16, 9.2))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1.0], hspace=0.36, wspace=0.28)

    # --- Panel 1: Dimensión del Espacio de Hilbert (Escala Log) ---
    ax1 = fig.add_subplot(gs[0, 0])
    casos = ["Caso 1\n(Monedas)", "Caso 2\n(Plataformas)", "Caso 3\n(Dungeon 2D)"]
    x = np.arange(len(casos))
    w = 0.35

    vars_naive = [20, 5504, 368]
    vars_compact = [4, 90, 96]

    ax1.bar(x - w/2, vars_naive, w, label="Mapeo Ingenuo / Completo", color="#c0392b", edgecolor="#78281f")
    ax1.bar(x + w/2, vars_compact, w, label="Reformulación Compacta / Reducida", color="#27ae60", edgecolor="#145a32")
    ax1.set_yscale("log")
    ax1.set_ylabel("Variables Binarias / Qubits (Log)", fontsize=10, fontweight="bold")
    ax1.set_title("Progresión de Escala de Variables\n(Impacto de la Codificación Algebraica)", fontsize=11, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(casos, fontsize=9.5, fontweight="bold")
    ax1.set_ylim(1, 1e4)
    ax1.grid(axis="y", which="both", linestyle="--", alpha=0.4)
    ax1.legend(loc="upper left", fontsize=8.5)

    ax1.text(0 - w/2, 28, "20Q", ha="center", va="bottom", fontweight="bold", color="#c0392b", fontsize=9)
    ax1.text(0 + w/2, 6, "4Q", ha="center", va="bottom", fontweight="bold", color="#145a32", fontsize=9)
    ax1.text(1 - w/2, 7000, "5.504", ha="center", va="bottom", fontweight="bold", color="#c0392b", fontsize=9)
    ax1.text(1 + w/2, 120, "90", ha="center", va="bottom", fontweight="bold", color="#145a32", fontsize=9)
    ax1.text(2 - w/2, 500, "368", ha="center", va="bottom", fontweight="bold", color="#c0392b", fontsize=9)
    ax1.text(2 + w/2, 130, "96", ha="center", va="bottom", fontweight="bold", color="#145a32", fontsize=9)

    # --- Panel 2: Tasa de Éxito / Factibilidad (%) ---
    ax2 = fig.add_subplot(gs[0, 1])
    p_naive = [0.0, 0.0, 8.3]
    p_compact = [65.6, 31.0, 93.6]

    ax2.bar(x - w/2, p_naive, w, label="Mapeo Ingenuo (Infactible/Colapso)", color="#e74c3c", edgecolor="#922b21")
    ax2.bar(x + w/2, p_compact, w, label="Modelo Optimizado TFM", color="#2ecc71", edgecolor="#196f3d")
    ax2.set_ylabel("Tasa de Muestras Válidas (%)", fontsize=10, fontweight="bold")
    ax2.set_title("Probabilidad de Factibilidad Empírica\n(Rescate de la Búsqueda Cuántica)", fontsize=11, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(casos, fontsize=9.5, fontweight="bold")
    ax2.set_ylim(0, 115)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.legend(loc="upper left", fontsize=8.5)

    for i in range(len(casos)):
        ax2.text(i - w/2, p_naive[i] + 2, f"{p_naive[i]:.1f}%", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=8.5)
        ax2.text(i + w/2, p_compact[i] + 2, f"{p_compact[i]:.1f}%", ha="center", va="bottom", fontweight="bold", color="#196f3d", fontsize=8.5)

    # --- Panel 3: Time-to-Target TTS_99 (Segundos en Escala Log) ---
    ax3 = fig.add_subplot(gs[0, 2])
    tts_naive = [1e4, 1e4, 0.063]  # 1e4 simbólico para inf
    tts_compact = [0.28, 1.88, 0.00439]

    ax3.bar(x - w/2, tts_naive, w, label="Mapeo Ingenuo (TTS = ∞)", color="#922b21", edgecolor="#4a1510")
    ax3.bar(x + w/2, tts_compact, w, label="Modelo Optimizado (Subsegundo)", color="#1abc9c", edgecolor="#117864")
    ax3.set_yscale("log")
    ax3.set_ylabel("Time-To-Target $TTS_{99}$ (s, log)", fontsize=10, fontweight="bold")
    ax3.set_title("Viabilidad Temporal de Solución ($TTS_{99}$)\n(Convergencia vs Divergencia)", fontsize=11, fontweight="bold")
    ax3.set_xticks(x)
    ax3.set_xticklabels(casos, fontsize=9.5, fontweight="bold")
    ax3.set_ylim(1e-3, 5e4)
    ax3.grid(axis="y", which="both", linestyle="--", alpha=0.4)
    ax3.legend(loc="upper left", fontsize=8.5)

    ax3.text(0 - w/2, 1.5e4, "∞", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=11)
    ax3.text(0 + w/2, 0.45, "0.28 s", ha="center", va="bottom", fontweight="bold", color="#117864", fontsize=8.5)
    ax3.text(1 - w/2, 1.5e4, "∞", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=11)
    ax3.text(1 + w/2, 3.0, "1.88 s", ha="center", va="bottom", fontweight="bold", color="#117864", fontsize=8.5)
    ax3.text(2 - w/2, 0.09, "63 ms", ha="center", va="bottom", fontweight="bold", color="#922b21", fontsize=8.5)
    ax3.text(2 + w/2, 0.007, "4.4 ms", ha="center", va="bottom", fontweight="bold", color="#117864", fontsize=8.5)

    # --- Panel Inferior: Tabla Sinóptica de Rigor Metodológico ---
    ax_tab = fig.add_subplot(gs[1, :])
    ax_tab.axis("off")

    column_labels = [
        "Dimensión Evaluada",
        "Caso 1: Colocación de Monedas",
        "Caso 2: Plataformas Jump & Run",
        "Caso 3: Dungeon Crawler 2D",
    ]
    tabla_data = [
        ["Naturaleza del PCG", "Colocación de entidades discretas", "Geometría 1D + cinemática física", "Topología 2D completa desde cero"],
        ["Modelo Clásico Exacto", "k-center (Gonzalez) / PAM (p-median)", "Google CP-SAT (v4 saltos/huecos)", "Google CP-SAT (Core y Demostrador v3)"],
        ["Paradigma Cuántico", "QAOA Variacional (Gate-based, Qiskit)", "Simulated/Quantum Annealing (D-Wave)", "Simulated/Quantum Annealing (D-Wave)"],
        ["Espacio de Hilbert", "2^4 = 16 estados (vs 1.048.576 en 20Q)", "2^90 estados (vs 2^5504 sin acotar)", "2^96 estados (96 variables binarias)"],
        ["Mecanismo Clave", "Precomputación analítica de pares C(j,l)", "Grafo acotado de saltos (Δy ≤ 2, Δy ≥ -3)", "Balance ferromagnético 4 zonas + ruta q"],
        ["Hallazgo Científico", "Hiperdilución 0.009% exige modelo 4Q", "Transición crítica de fase en C = 3.0", "Ruta embebida q eleva éxito de 8.3% a 93.6%"],
    ]

    tabla = ax_tab.table(
        cellText=tabla_data,
        colLabels=column_labels,
        cellLoc="center",
        loc="center",
        bbox=[0.0, 0.0, 1.0, 1.0],
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(9.5)
    for (row, col), cell in tabla.get_celld().items():
        cell.set_edgecolor("#bdc3c7")
        if row == 0:
            cell.set_facecolor("#2c3e50")
            cell.set_text_props(color="white", fontweight="bold")
        elif col == 0:
            cell.set_facecolor("#ecf0f1")
            cell.set_text_props(fontweight="bold")
        else:
            if col == 1: cell.set_facecolor("#fcf3cf")
            elif col == 2: cell.set_facecolor("#e8f8f5")
            elif col == 3: cell.set_facecolor("#ebf5fb")

    fig.suptitle("Síntesis Comparativa Global del TFM — Progresión de Dificultad y Paradigmas Cuánticos", fontsize=13, fontweight="bold", y=0.98)

    ruta_salida = FIGURAS_DIR / "tfm_sintesis_comparativa_tres_casos.png"
    plt.savefig(ruta_salida, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


# =============================================================================
# FIGURA 2: ARQUITECTURA METODOLÓGICA DEL PIPELINE HÍBRIDO
# =============================================================================

def generar_figura_pipeline_metodologico():
    """Genera el diagrama formal de bloques del pipeline metodológico híbrido."""
    print("Generando Figura Global 2: Arquitectura del Pipeline Metodológico Híbrido...")

    fig, ax = plt.subplots(figsize=(15, 8.5))
    ax.set_facecolor("#0f141d")
    ax.axis("off")

    def dibujar_bloque(x, y, w, h, titulo, subtitulo, color_borde, color_fondo, icono=""):
        rect = patches.FancyBboxPatch(
            (x - w/2.0, y - h/2.0), w, h,
            boxstyle="round,pad=0.15,rounding_size=0.25",
            facecolor=color_fondo, edgecolor=color_borde, linewidth=2.5, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x, y + h*0.18, f"{icono} {titulo}".strip(), color="white", fontweight="bold", fontsize=11, ha="center", va="center", zorder=3)
        ax.text(x, y - h*0.22, subtitulo, color="#bdc3c7", fontsize=8.5, ha="center", va="center", zorder=3)

    def dibujar_flecha(p1, p2, texto="", color="#3498db"):
        ax.annotate(
            "", xy=p2, xytext=p1,
            arrowprops=dict(arrowstyle="-|>", color=color, lw=2.5, mutation_scale=18),
            zorder=4
        )
        if texto:
            mx, my = (p1[0] + p2[0])/2.0, (p1[1] + p2[1])/2.0
            ax.text(mx, my + 0.25, texto, color="#f39c12", fontweight="bold", fontsize=8.5, ha="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#1a252f", ec="#f39c12", lw=1.0), zorder=5)

    # 1. Bloque de Entrada
    dibujar_bloque(2.0, 7.0, 3.2, 1.4, "1. ESPECIFICACIÓN PCG", "Dimensiones, gravedad, saltos,\nzonas, inicio y fin", "#3498db", "#1a365d")

    # 2. Oráculo Clásico CP-SAT
    dibujar_bloque(7.5, 7.0, 3.4, 1.4, "2. GOOGLE CP-SAT", "Oráculo Clásico Exacto:\nDemostración de factibilidad", "#2ecc71", "#145a32")

    # 3. Formulación QUBO
    dibujar_bloque(13.0, 7.0, 3.2, 1.4, "3. MODELO QUBO", "Matrices Q, penalizaciones\nteóricas a priori (P > cota)", "#9b59b6", "#4a235a")

    # Flechas fila 1
    dibujar_flecha((3.6, 7.0), (5.8, 7.0), "Parámetros")
    dibujar_flecha((9.2, 7.0), (11.4, 7.0), "Cota Óptima")

    # 4. Solvers Cuánticos / Recocido
    dibujar_bloque(13.0, 4.0, 3.4, 1.4, "4. RESOLUCIÓN CUÁNTICA", "• QAOA Variacional (Qiskit)\n• Simulated Annealing (D-Wave)", "#e67e22", "#6e2c00")
    dibujar_flecha((13.0, 6.3), (13.0, 4.7), "Matriz Q")

    # 5. Validación Rigurosa de Factibilidad
    dibujar_bloque(7.5, 4.0, 3.4, 1.4, "5. VALIDACIÓN ESTRICTA", "Comprobación sin atajos, TTS_99,\nconexión y navegabilidad BFS", "#e74c3c", "#641e16")
    dibujar_flecha((11.3, 4.0), (9.2, 4.0), "Muestras")

    # Bucle de retroalimentación
    dibujar_flecha((7.5, 4.7), (7.5, 6.3), "Bucle Verificación", color="#f1c40f")

    # 6. Exportación JSON Normalizada
    dibujar_bloque(2.0, 4.0, 3.2, 1.4, "6. EXPORTACIÓN JSON", "Esquema universal:\ngeometría, celdas, rutas", "#1abc9c", "#0e6251")
    dibujar_flecha((5.8, 4.0), (3.6, 4.0), "Solución Válida")

    # 7. Pipeline Blender 3D
    dibujar_bloque(2.0, 1.2, 3.2, 1.4, "7. BLENDER 5.2 LTS", "Motor procedural Headless:\nmateriales PBR, luces, diorama", "#f39c12", "#7e5109")
    dibujar_flecha((2.0, 3.3), (2.0, 1.9), "Archivo JSON")

    # 8. Renderizado Final TFM
    dibujar_bloque(7.5, 1.2, 3.4, 1.4, "8. ARTEFACTO VISUAL TFM", "Diorama 3D fotorrealista\ny figuras científicas publicables", "#e056fd", "#4834d4")
    dibujar_flecha((3.6, 1.2), (5.8, 1.2), "Render CYCLES")

    # Marco exterior
    ax.set_xlim(0.0, 15.0)
    ax.set_ylim(0.0, 8.5)

    ax.text(7.5, 8.25, "Arquitectura Metodológica del Pipeline Híbrido Cuántico-Clásico de PCG", color="white", fontweight="bold", fontsize=13, ha="center")

    ruta_salida = FIGURAS_DIR / "tfm_pipeline_metodologico_hibrido.png"
    plt.savefig(ruta_salida, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


def main():
    print("=" * 70)
    print("GENERANDO SUITE DE FIGURAS GLOBALES DEL TFM")
    print("=" * 70)
    generar_figura_sintesis_tres_casos()
    generar_figura_pipeline_metodologico()
    print("Figuras globales del TFM generadas exitosamente.\n")


if __name__ == "__main__":
    main()
