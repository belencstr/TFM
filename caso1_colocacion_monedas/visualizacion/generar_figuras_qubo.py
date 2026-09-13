"""Caso 1 — Generador de Figuras Académicas del QUBO (Matrices, Espectro y Dilución).

Genera dos figuras visuales científicas de alta calidad (300 DPI) para la memoria del TFM:
1. figuras/qubo_matrices_comparativa_20q_vs_4q.png:
   - Heatmap de la matriz QUBO directa Q_{20x20} (variables x_j e y_ij, bloques de penalizaciones A, B, C).
   - Heatmap de la matriz QUBO compacta Q_{4x4} con valores numéricos explícitos.
   - Grafo de acoplamiento Ising entre qubits (pesos J_ij y campos locales h_i).
2. figuras/qubo_espectro_energias_y_factibilidad.png:
   - Espectro discreto de energías de los 16 estados del modelo compacto (óptimos, subóptimos y no factibles).
   - Diagrama comparativo del espacio de Hilbert y la hiperdilución de factibilidad (20Q vs 4Q).
"""

from collections import defaultdict
import itertools
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
import numpy as np

# Configurar rutas del repositorio
SCRIPT_DIR = Path(__file__).resolve().parent
CASO1_DIR = SCRIPT_DIR.parent
REPO_ROOT = CASO1_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CASO1_DIR) not in sys.path:
    sys.path.insert(0, str(CASO1_DIR))

from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas
from modelo.grafo import construir_grafo
from modelo.distancias import construir_matriz_navegable
from modelo.qubo_pmedian import construir_qubo_pmedian
from modelo.qubo_pmedian_compacto import (
    construir_qubo_pmedian_compacto,
    comprobar_factibilidad_compacto,
    coste_pmedian_compacto,
    energia_qubo_compacto,
)
from solvers.k_medoids import k_medoids_pam
from solvers.busqueda_exhaustiva import k_medoids_exhaustivo

FIGURAS_DIR = CASO1_DIR / "figuras"
FIGURAS_DIR.mkdir(parents=True, exist_ok=True)


def qubo_a_matriz_numpy(qubo):
    """Convierte la estructura QUBO (lineal, cuadrático, variables) en matriz NumPy simétrica/triangular."""
    vars_list = qubo["variables"]
    n = len(vars_list)
    var_to_idx = {v: i for i, v in enumerate(vars_list)}
    Q = np.zeros((n, n), dtype=float)

    # Diagonal (términos lineales)
    for v, coef in qubo["lineal"].items():
        if v in var_to_idx:
            idx = var_to_idx[v]
            Q[idx, idx] = float(coef)

    # Fuera de diagonal (términos cuadráticos)
    for (u, v), coef in qubo["cuadratico"].items():
        if u in var_to_idx and v in var_to_idx:
            i, j = var_to_idx[u], var_to_idx[v]
            if i > j:
                i, j = j, i
            Q[i, j] += float(coef)

    return Q, vars_list


def generar_figura_matrices_qubo():
    """Genera la comparativa visual de matrices y el grafo de interacción Ising."""
    print("Generando Figura 1: Matrices QUBO (20Q vs 4Q) y Grafo Ising...")
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    matriz = construir_matriz_navegable(candidatas, grafo)

    # 1. QUBO 20Q (PLI directo)
    pam = k_medoids_pam(candidatas, matriz, 2)
    qubo_20q = construir_qubo_pmedian(matriz, k=2, cota_factible=pam["coste_total"])
    Q_20, vars_20 = qubo_a_matriz_numpy(qubo_20q)

    # 2. QUBO 4Q (Compacto)
    qubo_4q = construir_qubo_pmedian_compacto(matriz, k=2, cota_factible=pam["coste_total"])
    Q_4, vars_4 = qubo_a_matriz_numpy(qubo_4q)

    fig = plt.figure(figsize=(16, 6.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.3, 1.0, 1.1], wspace=0.32)

    # --- Panel A: Matriz QUBO 20x20 ---
    ax_a = fig.add_subplot(gs[0])
    im_a = ax_a.imshow(Q_20, cmap="coolwarm", aspect="equal")
    ax_a.set_title("QUBO Directo: $Q_{20 \\times 20}$ (20 qubits)\nVariables $x_j$ (medoides) e $y_{ij}$ (asignación)", fontsize=11, fontweight="bold")
    ax_a.set_xticks(range(0, 20, 2))
    ax_a.set_yticks(range(0, 20, 2))
    ax_a.set_xticklabels([vars_20[i] for i in range(0, 20, 2)], rotation=45, fontsize=8)
    ax_a.set_yticklabels([vars_20[i] for i in range(0, 20, 2)], fontsize=8)

    # Resaltar bloques x e y
    rect_x = patches.Rectangle((-0.5, -0.5), 4, 4, linewidth=2, edgecolor="#e74c3c", facecolor="none", linestyle="--")
    rect_y = patches.Rectangle((3.5, 3.5), 16, 16, linewidth=2, edgecolor="#2980b9", facecolor="none", linestyle="--")
    ax_a.add_patch(rect_x)
    ax_a.add_patch(rect_y)
    ax_a.text(1.5, -1.2, "Bloque $x$ (4x4)", color="#c0392b", fontweight="bold", fontsize=8.5, ha="center")
    ax_a.text(11.5, 20.8, "Bloque $y_{ij}$ (16x16)", color="#2471a3", fontweight="bold", fontsize=8.5, ha="center")

    cbar_a = fig.colorbar(im_a, ax=ax_a, fraction=0.046, pad=0.04)
    cbar_a.set_label("Coeficiente QUBO", fontsize=9)

    # --- Panel B: Matriz QUBO 4x4 Compacta ---
    ax_b = fig.add_subplot(gs[1])
    im_b = ax_b.imshow(Q_4, cmap="Blues", aspect="equal")
    ax_b.set_title("QUBO Compacto: $Q_{4 \\times 4}$ (4 qubits, $k=2$)\nPrecomputación analítica de pares $C(j, l)$", fontsize=11, fontweight="bold")
    ax_b.set_xticks(range(4))
    ax_b.set_yticks(range(4))
    ax_b.set_xticklabels(vars_4, fontsize=10, fontweight="bold")
    ax_b.set_yticklabels(vars_4, fontsize=10, fontweight="bold")

    # Anotar valores numéricos exactos en cada celda
    for r in range(4):
        for c in range(4):
            val = Q_4[r, c]
            txt_color = "white" if val > np.mean(Q_4) else "black"
            if val != 0 or r == c:
                ax_b.text(c, r, f"{val:+.1f}", ha="center", va="center", color=txt_color, fontweight="bold", fontsize=10)
            else:
                ax_b.text(c, r, "0.0", ha="center", va="center", color="#7f8c8d", fontsize=9)

    cbar_b = fig.colorbar(im_b, ax=ax_b, fraction=0.046, pad=0.04)
    cbar_b.set_label("Energía / Coste", fontsize=9)

    # --- Panel C: Grafo de Interacción Ising / Qubits ---
    ax_c = fig.add_subplot(gs[2])
    G = nx.Graph()
    for i, v in enumerate(vars_4):
        G.add_node(v, bias=Q_4[i, i])

    for i in range(4):
        for j in range(i + 1, 4):
            peso = Q_4[i, j]
            if peso != 0:
                G.add_edge(vars_4[i], vars_4[j], weight=peso)

    # Posiciones fijas en rombo estético
    pos = {
        "x_0": np.array([0.0, 1.0]),
        "x_1": np.array([1.0, 0.0]),
        "x_2": np.array([0.0, -1.0]),
        "x_3": np.array([-1.0, 0.0]),
    }

    edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
    edge_labels = {(u, v): f"$J={G[u][v]['weight']:+.1f}$" for u, v in G.edges()}

    nx.draw_networkx_nodes(
        G, pos, ax=ax_c,
        node_color="#34495e", node_size=1700, edgecolors="#1abc9c", linewidths=2.5
    )
    nx.draw_networkx_labels(
        G, pos, ax=ax_c, font_color="white", font_size=11, font_weight="bold"
    )
    nx.draw_networkx_edges(
        G, pos, ax=ax_c, width=2.5, edge_color="#e67e22", alpha=0.85
    )
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, ax=ax_c, font_color="#d35400", font_size=8.5, font_weight="bold"
    )

    # Etiquetas de bias de cada qubit
    for v, (x, y) in pos.items():
        bias_val = G.nodes[v]["bias"]
        offset_y = 0.25 if y >= 0 else -0.25
        ax_c.text(x, y + offset_y, f"$h_{{{v[-1]}}}={bias_val:+.1f}$", color="#2c3e50",
                  fontweight="bold", fontsize=9, ha="center", bbox=dict(boxstyle="round,pad=0.2", fc="#ecf0f1", ec="#bdc3c7", lw=0.8))

    ax_c.set_title("Topología de Conectividad Cuántica\nGrafo Ising completo $K_4$ ($J_{ij}$ y $h_i$)", fontsize=11, fontweight="bold")
    ax_c.set_xlim(-1.6, 1.6)
    ax_c.set_ylim(-1.6, 1.6)
    ax_c.axis("off")

    plt.subplots_adjust(left=0.06, right=0.96, top=0.88, bottom=0.12, wspace=0.32)
    ruta_salida = FIGURAS_DIR / "qubo_matrices_comparativa_20q_vs_4q.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


def generar_figura_espectro_y_factibilidad():
    """Genera el espectro de energías de los 16 estados del modelo compacto y el gráfico de dilución."""
    print("Generando Figura 2: Espectro de Energías y Dilución del Espacio...")
    candidatas = obtener_candidatas(MAPA_QAOA_MINIMO)
    grafo = construir_grafo(MAPA_QAOA_MINIMO)
    matriz = construir_matriz_navegable(candidatas, grafo)

    pam = k_medoids_pam(candidatas, matriz, 2)
    qubo_4q = construir_qubo_pmedian_compacto(matriz, k=2, cota_factible=pam["coste_total"])
    optimo_exacto = k_medoids_exhaustivo(candidatas, matriz, 2)["coste_total"]

    # Evaluar los 16 estados
    estados = []
    for bits in itertools.product([0, 1], repeat=4):
        asignacion = {f"x_{j}": bits[j] for j in range(4)}
        fact = comprobar_factibilidad_compacto(qubo_4q, asignacion)
        energia = energia_qubo_compacto(qubo_4q, asignacion)
        label_bin = "".join(str(b) for b in bits)

        coste = None
        es_optimo = False
        if fact["factible"]:
            coste = coste_pmedian_compacto(matriz, fact["seleccionadas"])
            if abs(coste - optimo_exacto) < 1e-6:
                es_optimo = True
                categoria = "Óptimo Factible"
                color = "#27ae60"
            else:
                categoria = "Subóptimo Factible"
                color = "#f39c12"
        else:
            categoria = f"No Factible (k={sum(bits)})"
            color = "#c0392b"

        estados.append({
            "label": label_bin,
            "bits": bits,
            "energia": energia,
            "factible": fact["factible"],
            "es_optimo": es_optimo,
            "coste": coste,
            "categoria": categoria,
            "color": color,
        })

    estados.sort(key=lambda e: e["energia"])

    fig, (ax_esp, ax_dil) = plt.subplots(2, 1, figsize=(13, 9.5), gridspec_kw={"height_ratios": [1.4, 1.0]})
    plt.subplots_adjust(hspace=0.38)

    # --- 1. Espectro Discreto de Energías (16 estados) ---
    x_pos = np.arange(len(estados))
    barras = ax_esp.bar(
        x_pos, [e["energia"] for e in estados],
        color=[e["color"] for e in estados], width=0.65, edgecolor="#2c3e50", linewidth=1.2
    )

    ax_esp.set_xticks(x_pos)
    ax_esp.set_xticklabels([f"|{e['label']}⟩" for e in estados], rotation=45, fontsize=9.5, fontweight="bold")
    ax_esp.set_ylabel("Energía QUBO $H(x)$", fontsize=11, fontweight="bold")
    ax_esp.set_title("Espectro Completo de Energías del QUBO Compacto (16 estados en $2^4$)\nSeparación nítida entre Estados Factibles ($k=2$) y Estados Penalizados ($k \\neq 2$)", fontsize=12, fontweight="bold")
    ax_esp.grid(axis="y", linestyle="--", alpha=0.5)

    # Etiquetas sobre barras
    for idx, e in enumerate(estados):
        val = e["energia"]
        if e["es_optimo"]:
            txt = f"★ Óptimo\n(Coste={e['coste']:.0f})"
            ax_esp.text(idx, val + 0.3, txt, ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1e8449")
        elif e["factible"]:
            txt = f"Coste={e['coste']:.0f}"
            ax_esp.text(idx, val + 0.3, txt, ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#d35400")
        else:
            txt = f"k={sum(e['bits'])}"
            ax_esp.text(idx, val + 0.3, txt, ha="center", va="bottom", fontsize=8, color="#922b21")

    # Leyenda estética
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color="#27ae60", lw=6, label="Óptimo Global Factible (Coste = 2.0)"),
        Line2D([0], [0], color="#f39c12", lw=6, label="Subóptimo Factible (Coste = 4.0)"),
        Line2D([0], [0], color="#c0392b", lw=6, label="No Factible (Violación Cardinalidad $\\sum x_j \\neq 2$)"),
    ]
    ax_esp.legend(handles=legend_elements, loc="upper left", framealpha=0.9, fontsize=10)

    # --- 2. Comparativa de Dilución del Espacio de Estados (20Q vs 4Q) ---
    modelos = ["QUBO Directo PLI\n(20 Qubits / Vars)", "QUBO Compacto k=2\n(4 Qubits / Vars)"]
    totales = [2**20, 2**4]
    factibles = [96, 6]
    optimos = [6, 2]

    x_m = np.arange(len(modelos))
    width = 0.25

    rects1 = ax_dil.bar(x_m - width, totales, width, label="Espacio Total de Hilbert ($2^N$)", color="#34495e", edgecolor="#1a252f")
    rects2 = ax_dil.bar(x_m, factibles, width, label="Estados Factibles", color="#2980b9", edgecolor="#1b4f72")
    rects3 = ax_dil.bar(x_m + width, optimos, width, label="Estados Óptimos", color="#27ae60", edgecolor="#145a32")

    ax_dil.set_yscale("log")
    ax_dil.set_ylabel("Número de Estados (Escala Log)", fontsize=11, fontweight="bold")
    ax_dil.set_title("Efecto de la Codificación: Dilución vs Densidad de Estados Factibles", fontsize=12, fontweight="bold")
    ax_dil.set_xticks(x_m)
    ax_dil.set_xticklabels(modelos, fontsize=11, fontweight="bold")
    ax_dil.set_ylim(1, 4e6)
    ax_dil.grid(axis="y", which="both", linestyle="--", alpha=0.4)
    ax_dil.legend(loc="upper right", fontsize=10)

    # Anotar porcentajes de factibilidad
    ax_dil.text(0, factibles[0] * 2.2, f"96 estados\n({(96/1048576)*100:.4f}%)", ha="center", va="bottom", fontweight="bold", color="#2980b9", fontsize=9.5)
    ax_dil.text(0 + width, optimos[0] * 2.2, f"6 estados\n({(6/1048576)*100:.4f}%)", ha="center", va="bottom", fontweight="bold", color="#27ae60", fontsize=9.5)

    ax_dil.text(1, factibles[1] * 1.8, f"6 estados\n(37.50%)", ha="center", va="bottom", fontweight="bold", color="#2980b9", fontsize=9.5)
    ax_dil.text(1 + width, optimos[1] * 1.8, f"2 estados\n(12.50%)", ha="center", va="bottom", fontweight="bold", color="#27ae60", fontsize=9.5)

    ax_dil.text(0 - width, totales[0] * 1.3, "1.048.576", ha="center", va="bottom", fontweight="bold", color="#34495e", fontsize=9.5)
    ax_dil.text(1 - width, totales[1] * 1.3, "16", ha="center", va="bottom", fontweight="bold", color="#34495e", fontsize=9.5)

    plt.tight_layout()
    ruta_salida = FIGURAS_DIR / "qubo_espectro_energias_y_factibilidad.png"
    plt.savefig(ruta_salida, dpi=300)
    plt.close()
    print(f"-> Figura guardada: {ruta_salida}")


def main():
    print("=" * 70)
    print("GENERANDO SUITE DE FIGURAS QUBO PARA CASO 1 (TFM)")
    print("=" * 70)
    generar_figura_matrices_qubo()
    generar_figura_espectro_y_factibilidad()
    print("Figuras QUBO generadas exitosamente.\n")


if __name__ == "__main__":
    main()
