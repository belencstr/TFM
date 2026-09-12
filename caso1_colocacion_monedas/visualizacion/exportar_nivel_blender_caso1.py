"""Exportador de Nivel 3D para Blender — Caso 1: Colocación de Monedas.

Permite exportar soluciones obtenidas por diferentes métodos combinatorios y cuánticos:
1. Gonzalez multiinicio (k-center / radio minimax de cobertura).
2. PAM / k-medoids (p-median / suma mínima de distancias).
3. QAOA / QUBO a partir de registros experimentales congelados en JSON (sin reejecución estocástica).

Genera la estructura de datos requerida por `visualizar_caso1_blender.py`.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mapas.mapa_a import MAPA_A
from mapas.mapa_b import MAPA_B
from mapas.mapa_c import MAPA_C
from mapas.mapa_qaoa_minimo import MAPA_QAOA_MINIMO
from modelo.candidatas import obtener_candidatas, obtener_inicio_fin
from modelo.grafo import construir_grafo
from modelo.distancias import construir_matriz_navegable, distancias_navegables_desde
from solvers.gonzalez import gonzalez_multiinicio
from solvers.k_medoids import k_medoids_pam


MAPAS = {
    "A": ("Mapa A (Espacio Abierto)", MAPA_A),
    "B": ("Mapa B (Obstáculos y Cobertura)", MAPA_B),
    "C": ("Mapa C (Laberinto y Pasillos)", MAPA_C),
    "MIN": ("Mapa Mínimo QAOA (4 candidatas)", MAPA_QAOA_MINIMO),
}

EXPORT_DIR = RAIZ / "resultados"


def _metricas_seleccion(candidatas_sel, candidatas_todas, matriz):
    """Calcula radio de cobertura y métricas de separación para un conjunto de candidatas."""
    indices = [candidatas_todas.index(c) for c in candidatas_sel]
    n = len(candidatas_todas)
    dists_cob = [min(matriz[i][m] for m in indices) for i in range(n)] if indices else [0]
    radio = max(dists_cob) if dists_cob else 0

    d_pares = []
    for pos_i, i in enumerate(indices):
        for j in indices[pos_i + 1:]:
            d_pares.append(matriz[i][j])

    sep_min = min(d_pares) if d_pares else 0
    sep_med = (sum(d_pares) / len(d_pares)) if d_pares else 0.0
    sep_tot = sum(d_pares)

    return {
        "radio_cobertura": radio,
        "separacion_minima": sep_min,
        "separacion_media": round(sep_med, 2),
        "separacion_total": sep_tot,
        "coste_pmedian": sum(dists_cob),
    }


def exportar_solucion_mapa(id_mapa="B", k=5, metodo="gonzalez", archivo_resultado=None, candidatas_sel=None):
    """Exporta la solución de un mapa a formato JSON para visualización en Blender."""
    id_mapa_norm = id_mapa.upper()
    if id_mapa_norm not in MAPAS:
        raise ValueError(f"Mapa desconocido '{id_mapa}'. Opciones: {list(MAPAS.keys())}")

    nombre_mapa, mapa = MAPAS[id_mapa_norm]
    filas = len(mapa)
    columnas = len(mapa[0])

    candidatas = obtener_candidatas(mapa)
    inicio, fin = obtener_inicio_fin(mapa)
    grafo = construir_grafo(mapa)
    matriz = construir_matriz_navegable(candidatas, grafo)

    if candidatas_sel is not None:
        algoritmo_nombre = f"Solución Interactiva ({metodo.upper()})"
        tag_metodo = metodo.lower()
        k = len(candidatas_sel)
        m_calc = _metricas_seleccion(candidatas_sel, candidatas, matriz)
        metricas = {
            "radio_cobertura": m_calc["radio_cobertura"],
            "separacion_minima": m_calc["separacion_minima"],
            "separacion_media": m_calc["separacion_media"],
            "separacion_total": m_calc["separacion_total"],
            "coste_pmedian": m_calc["coste_pmedian"],
            "num_candidatas": len(candidatas),
        }

    elif metodo == "gonzalez":
        algoritmo_nombre = "Gonzalez Multi-start (k-center / Farthest-First Traversal)"
        tag_metodo = "gonzalez"
        sol_res = gonzalez_multiinicio(candidatas, matriz, k)
        candidatas_sel = sol_res["candidatas"]
        metricas = {
            "radio_cobertura": sol_res["radio_cobertura"],
            "separacion_minima": sol_res["separacion_minima"],
            "separacion_media": round(sol_res["separacion_media"], 2),
            "separacion_total": sol_res["separacion_total"],
            "id_inicio_optimo": sol_res.get("id_inicio"),
            "num_candidatas": len(candidatas),
        }

    elif metodo == "pam":
        algoritmo_nombre = "Partitioning Around Medoids (PAM / k-medoids)"
        tag_metodo = "pam"
        sol_res = k_medoids_pam(candidatas, matriz, k)
        candidatas_sel = sol_res["candidatas"]
        metricas = {
            "radio_cobertura": sol_res["radio_cobertura"],
            "separacion_minima": sol_res["separacion_minima"],
            "separacion_media": round(sol_res["separacion_media"], 2),
            "separacion_total": sol_res["separacion_total"],
            "coste_pmedian": sol_res["coste_total"],
            "num_candidatas": len(candidatas),
        }

    elif metodo == "qubo":
        algoritmo_nombre = "QAOA / QUBO (Resultado experimental congelado)"
        tag_metodo = "qubo"
        if not archivo_resultado:
            archivo_resultado = EXPORT_DIR / "benchmark_qaoa_compacto_4q.json"
        ruta_res = Path(archivo_resultado)
        if not ruta_res.is_absolute():
            ruta_res = RAIZ / ruta_res
        if not ruta_res.exists():
            raise FileNotFoundError(f"No se encontró el archivo de resultados QUBO: {ruta_res}")

        with open(ruta_res, "r", encoding="utf-8") as f:
            datos_q = json.load(f)

        rend = datos_q.get("rendimiento_experimental", {})
        sol_bits = rend.get("solucion_bits")
        if sol_bits is not None:
            indices_sel = [i for i, b in enumerate(sol_bits) if b == 1]
            candidatas_sel = [candidatas[i] for i in indices_sel]
            k = len(candidatas_sel)
        else:
            raise ValueError(f"El archivo {ruta_res} no contiene 'solucion_bits'.")

        m_calc = _metricas_seleccion(candidatas_sel, candidatas, matriz)
        metricas = {
            "radio_cobertura": m_calc["radio_cobertura"],
            "separacion_minima": m_calc["separacion_minima"],
            "separacion_media": m_calc["separacion_media"],
            "separacion_total": m_calc["separacion_total"],
            "coste_pmedian": rend.get("coste_pmedian", m_calc["coste_pmedian"]),
            "num_candidatas": len(candidatas),
            "archivo_origen": str(ruta_res.name),
        }

    else:
        raise ValueError(f"Método desconocido '{metodo}'. Opciones: 'gonzalez', 'pam', 'qubo'")

    monedas_coords = [(c["fila"], c["columna"]) for c in candidatas_sel]
    monedas_set = set(monedas_coords)

    # Distancias navegables desde cada moneda seleccionada
    dist_desde_monedas = []
    for c in candidatas_sel:
        coord = (c["fila"], c["columna"])
        d_dict = distancias_navegables_desde(grafo, coord)
        dist_desde_monedas.append(d_dict)

    # Celdas con clasificación y asignación a la moneda más cercana
    celdas = []
    cobertura_conteo = [0] * len(candidatas_sel)

    for r in range(filas):
        for c in range(columnas):
            char = mapa[r][c]
            is_wall = (char == "#")
            is_start = (inicio is not None and r == inicio[0] and c == inicio[1])
            is_end = (fin is not None and r == fin[0] and c == fin[1])
            is_coin = (r, c) in monedas_set

            closest_coin_idx = None
            min_dist_to_coin = None

            if not is_wall and candidatas_sel:
                dists = [dist_desde_monedas[m_idx].get((r, c), 9999) for m_idx in range(len(candidatas_sel))]
                min_dist_to_coin = min(dists)
                closest_coin_idx = dists.index(min_dist_to_coin)
                cobertura_conteo[closest_coin_idx] += 1

            celdas.append({
                "row": r,
                "col": c,
                "char": char,
                "is_wall": is_wall,
                "is_start": is_start,
                "is_end": is_end,
                "is_coin": is_coin,
                "closest_coin_idx": closest_coin_idx,
                "dist_to_coin": min_dist_to_coin,
            })

    monedas_data = []
    for idx, c in enumerate(candidatas_sel):
        monedas_data.append({
            "idx": idx,
            "id": c["id"],
            "row": c["fila"],
            "col": c["columna"],
            "assigned_cells": cobertura_conteo[idx],
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    datos_exportados = {
        "caso": "Caso 1 - Colocación de Monedas",
        "algoritmo": algoritmo_nombre,
        "metodo": tag_metodo,
        "mapa_id": id_mapa_norm,
        "mapa_nombre": nombre_mapa,
        "dimensiones": {
            "filas": filas,
            "columnas": columnas,
        },
        "k": len(candidatas_sel),
        "start": {"row": inicio[0], "col": inicio[1]} if inicio else None,
        "end": {"row": fin[0], "col": fin[1]} if fin else None,
        "monedas": monedas_data,
        "metricas": metricas,
        "celdas": celdas,
    }

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    nombre_base = f"caso1_nivel_blender_{tag_metodo}_mapa_{id_mapa_norm.lower()}_k{len(candidatas_sel)}"
    ruta_ts = EXPORT_DIR / f"{nombre_base}_{timestamp}.json"
    ruta_fija = EXPORT_DIR / f"{nombre_base}.json"

    # Rutas para compatibilidad hacia atrás
    rutas_a_guardar = [ruta_ts, ruta_fija]
    if tag_metodo == "gonzalez":
        ruta_legado = EXPORT_DIR / f"caso1_nivel_blender_mapa_{id_mapa_norm.lower()}_k{k}.json"
        rutas_a_guardar.append(ruta_legado)
        if id_mapa_norm == "B" and k == 5:
            rutas_a_guardar.append(EXPORT_DIR / "caso1_nivel_blender_k5.json")

    for ruta in rutas_a_guardar:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos_exportados, f, indent=2, ensure_ascii=False)

    print(f"[CASO 1] Solución exportada con éxito ({algoritmo_nombre}):")
    print(f"  - Mapa: {nombre_mapa}")
    print(f"  - Monedas: {len(candidatas_sel)}")
    print(f"  - Radio de cobertura: {metricas['radio_cobertura']}")
    print(f"  - Archivo canónico: {ruta_fija}")
    return ruta_fija


def main():
    parser = argparse.ArgumentParser(description="Exportador de niveles Caso 1 para Blender.")
    parser.add_argument(
        "--mapa", "-m",
        default="B",
        choices=["A", "B", "C", "MIN"],
        help="Mapa a procesar (A, B, C o MIN). Por defecto B.",
    )
    parser.add_argument(
        "-k",
        type=int,
        default=5,
        help="Número de monedas a seleccionar (por defecto 5).",
    )
    parser.add_argument(
        "--metodo",
        default="gonzalez",
        choices=["gonzalez", "pam", "qubo"],
        help="Método de selección de posiciones.",
    )
    parser.add_argument(
        "--resultado",
        type=str,
        default=None,
        help="Ruta al archivo JSON con resultados congelados para --metodo qubo.",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Exporta los mapas A, B y C con Gonzalez y PAM para tener el set completo.",
    )

    args = parser.parse_args()

    if args.todos or len(sys.argv) == 1:
        print("=" * 70)
        print("EXPORTANDO SOLUCIONES CANÓNICAS CASO 1 A FORMATO BLENDER...")
        print("=" * 70)
        for m in ("A", "B", "C"):
            exportar_solucion_mapa(id_mapa=m, k=5, metodo="gonzalez")
            exportar_solucion_mapa(id_mapa=m, k=5, metodo="pam")

        # Exportar también la solución congelada de QAOA compacto
        exportar_solucion_mapa(
            id_mapa="MIN",
            k=2,
            metodo="qubo",
            archivo_resultado=EXPORT_DIR / "benchmark_qaoa_compacto_4q.json",
        )
        print("\nExportación multi-método completada con éxito.")
    else:
        exportar_solucion_mapa(
            id_mapa=args.mapa,
            k=args.k,
            metodo=args.metodo,
            archivo_resultado=args.resultado,
        )


if __name__ == "__main__":
    main()
