"""Exportador de Nivel 3D para Blender — Caso 1: Colocación de Monedas (k-center).

Ejecuta el algoritmo de Gonzalez (farthest-first traversal) multiinicio para
seleccionar k posiciones óptimas para monedas, calcula la cobertura de cada celda
navegable y exporta la estructura completa a JSON para su visualización en Blender.
"""

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
from modelo.candidatas import obtener_candidatas, obtener_inicio_fin
from modelo.grafo import construir_grafo
from modelo.distancias import construir_matriz_navegable, distancias_navegables_desde
from solvers.gonzalez import gonzalez_multiinicio


MAPAS = {
    "A": ("Mapa A (Espacio Abierto)", MAPA_A),
    "B": ("Mapa B (Obstáculos y Cobertura)", MAPA_B),
    "C": ("Mapa C (Laberinto y Pasillos)", MAPA_C),
}

EXPORT_DIR = RAIZ / "resultados"


def exportar_solucion_mapa(id_mapa="B", k=5):
    """Resuelve y exporta un mapa de Caso 1 a formato JSON para Blender."""
    if id_mapa not in MAPAS:
        raise ValueError(f"Mapa desconocido '{id_mapa}'. Opciones: {list(MAPAS.keys())}")

    nombre_mapa, mapa = MAPAS[id_mapa]
    filas = len(mapa)
    columnas = len(mapa[0])

    candidatas = obtener_candidatas(mapa)
    inicio, fin = obtener_inicio_fin(mapa)
    grafo = construir_grafo(mapa)
    matriz = construir_matriz_navegable(candidatas, grafo)

    solucion = gonzalez_multiinicio(candidatas, matriz, k)
    monedas_coords = [(c["fila"], c["columna"]) for c in solucion["candidatas"]]
    monedas_set = set(monedas_coords)

    # Para cada moneda, calculamos distancias desde ella a todo el grafo
    dist_desde_monedas = []
    for i, c in enumerate(solucion["candidatas"]):
        coord = (c["fila"], c["columna"])
        d_dict = distancias_navegables_desde(grafo, coord)
        dist_desde_monedas.append(d_dict)

    # Celdas con tipo y asignación a la moneda más cercana
    celdas = []
    cobertura_conteo = [0] * k

    for r in range(filas):
        for c in range(columnas):
            char = mapa[r][c]
            is_wall = (char == "#")
            is_start = (inicio is not None and r == inicio[0] and c == inicio[1])
            is_end = (fin is not None and r == fin[0] and c == fin[1])
            is_coin = (r, c) in monedas_set

            closest_coin_idx = None
            min_dist_to_coin = None

            if not is_wall:
                # Buscar moneda más cercana
                dists = [dist_desde_monedas[m_idx].get((r, c), 9999) for m_idx in range(k)]
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
    for idx, c in enumerate(solucion["candidatas"]):
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
        "algoritmo": "Gonzalez Multi-start (Farthest-First Traversal)",
        "mapa_id": id_mapa,
        "mapa_nombre": nombre_mapa,
        "dimensiones": {
            "filas": filas,
            "columnas": columnas,
        },
        "k": k,
        "start": {"row": inicio[0], "col": inicio[1]} if inicio else None,
        "end": {"row": fin[0], "col": fin[1]} if fin else None,
        "monedas": monedas_data,
        "metricas": {
            "radio_cobertura": solucion["radio_cobertura"],
            "separacion_minima": solucion["separacion_minima"],
            "separacion_media": round(solucion["separacion_media"], 2),
            "separacion_total": solucion["separacion_total"],
            "id_inicio_optimo": solucion["id_inicio"],
            "num_candidatas": len(candidatas),
        },
        "celdas": celdas,
    }

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename_ts = f"caso1_nivel_blender_mapa_{id_mapa.lower()}_k{k}_{timestamp}.json"
    filename_fijo = f"caso1_nivel_blender_mapa_{id_mapa.lower()}_k{k}.json"
    filename_default = "caso1_nivel_blender_k5.json"

    ruta_ts = EXPORT_DIR / filename_ts
    ruta_fija = EXPORT_DIR / filename_fijo
    ruta_def = EXPORT_DIR / filename_default

    for ruta in (ruta_ts, ruta_fija, ruta_def):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos_exportados, f, indent=2, ensure_ascii=False)

    print(f"[CASO 1] Solución exportada con éxito:")
    print(f"  - Mapa: {nombre_mapa}")
    print(f"  - Monedas: {k}")
    print(f"  - Radio de cobertura R(S): {solucion['radio_cobertura']}")
    print(f"  - Archivo fijo: {ruta_fija}")
    print(f"  - Archivo default: {ruta_def}")
    return ruta_fija


if __name__ == "__main__":
    # Exportar los tres mapas para que estén disponibles inmediatamente
    print("=" * 70)
    print("EXPORTANDO SOLUCIONES CASO 1 A FORMATO BLENDER...")
    print("=" * 70)
    for m in ("A", "B", "C"):
        exportar_solucion_mapa(m, k=5)
    # Dejar el Mapa B (el más representativo con obstáculos) como default
    exportar_solucion_mapa("B", k=5)
    print("\nTodos los mapas del Caso 1 han sido exportados para Blender.")
