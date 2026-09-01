import os,sys
from datetime import datetime

RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from modelo.grafo_saltos_segmentos_v4 import (
    obtener_anclas_candidatas,
    construir_grafo_segmentos_v4,
    contar_aristas,
)

from cuantico.formulacion.qubo_caso2_18x5 import *

RUTA_CLASICA=[
    (0,2),
    (3,3),
    (6,1),
    (10,3),
    (13,3),
    (17,2),
]

class Tee:
    def __init__(self,*streams): self.streams=streams
    def write(self,data):
        for s in self.streams:
            s.write(data); s.flush()
    def flush(self):
        for s in self.streams: s.flush()

def ejecutar():
    candidatas=obtener_anclas_candidatas(ANCHO,ALTO,START,GOAL)
    posiciones=[START]+candidatas+[GOAL]
    grafo=construir_grafo_segmentos_v4(posiciones,START,GOAL)

    Q,offset=construir_qubo(grafo)
    muestra=muestra_desde_ruta(grafo,RUTA_CLASICA)
    energia=energia_qubo(Q,offset,muestra)
    ev=evaluar_restricciones(grafo,muestra)

    print("="*88)
    print("CASO 2 — VALIDACION QUBO 18x5")
    print("="*88)
    print(f"Mapa: {ANCHO} x {ALTO}")
    print(f"Variables binarias = |E| = {contar_aristas(grafo)}")
    print(f"Terminos QUBO no nulos: {len(Q)}")
    print(f"Offset: {offset}")
    print()
    print("Ruta clasica sin atajos:")
    print(" -> ".join(str(p) for p in RUTA_CLASICA))
    print()
    print(f"Saltos: {ev['numero_saltos']}")
    print(f"Subidas: {ev['numero_subidas']}")
    print(f"Bajadas: {ev['numero_bajadas']}")
    print(f"Planos: {ev['numero_planos']}")
    print(f"Violaciones flujo: {len(ev['violaciones_flujo'])}")
    print(f"Energia por componentes: {ev['energia_componentes']}")
    print(f"Energia QUBO expandido: {energia}")
    print(f"Ruta factible segun QUBO: {ev['factible_qubo']}")

    if abs(energia)>1e-9:
        raise AssertionError("La ruta clasica deberia tener energia QUBO 0.")

    print()
    print("VALIDACION SUPERADA: Q(ruta clasica) = 0")

def main():
    carpeta=os.path.join(RAIZ,"cuantico","resultados")
    os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"validacion_qubo_ruta_clasica_18x5_{marca}.txt")
    original=sys.stdout
    try:
        with open(ruta,"w",encoding="utf-8") as f:
            sys.stdout=Tee(original,f)
            ejecutar()
            print()
            print(f"Registro guardado en: {ruta}")
    finally:
        sys.stdout=original
    print(f"\nTXT generado correctamente: {ruta}")

if __name__=="__main__":
    main()