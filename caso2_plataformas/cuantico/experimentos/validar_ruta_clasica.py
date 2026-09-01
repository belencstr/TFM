import os,sys
from datetime import datetime

RAIZ=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0,RAIZ)

from modelo.grafo_saltos_segmentos_v4 import obtener_anclas_candidatas, construir_grafo_segmentos_v4, contar_aristas
from cuantico.formulacion.qubo import *

RUTA_CLASICA=[(0,2),(2,0),(6,2),(9,4),(12,4),(15,2)]

class Tee:
    def __init__(self,*s): self.s=s
    def write(self,d):
        for x in self.s: x.write(d); x.flush()
    def flush(self):
        for x in self.s: x.flush()

def ejecutar():
    candidatas=obtener_anclas_candidatas(ANCHO,ALTO,START,GOAL)
    posiciones=[START]+candidatas+[GOAL]
    grafo=construir_grafo_segmentos_v4(posiciones,START,GOAL)
    Q,offset=construir_qubo(grafo)
    muestra=muestra_desde_ruta(grafo,RUTA_CLASICA)
    energia=energia_qubo(Q,offset,muestra)
    ev=evaluar_restricciones(grafo,muestra)

    print("="*88)
    print("CASO 2 — VALIDACION INICIAL DE LA FORMULACION QUBO")
    print("="*88)
    print(f"Mapa: {ANCHO} x {ALTO}")
    print(f"START: {START} | GOAL: {GOAL}")
    print(f"L*: {L_OBJETIVO}")
    print(f"Subidas objetivo: {SUBIDAS_OBJETIVO}")
    print(f"Bajadas objetivo: {BAJADAS_OBJETIVO}")
    print(f"Pesos: A={A}, B={B}, C={C}, D={D}, E={E}, F={F}")
    print(f"Variables binarias = |E| = {contar_aristas(grafo)}")
    print(f"Terminos QUBO no nulos: {len(Q)}")
    print(f"Offset: {offset}")
    print()
    print("Ruta clasica:")
    print(" -> ".join(str(p) for p in RUTA_CLASICA))
    print()
    print("Comprobacion:")
    print(f"  Salidas START: {ev['salida_start']}")
    print(f"  Entradas GOAL: {ev['entrada_goal']}")
    print(f"  Saltos: {ev['numero_saltos']}")
    print(f"  Subidas: {ev['numero_subidas']}")
    print(f"  Bajadas: {ev['numero_bajadas']}")
    print(f"  Planos: {ev['numero_planos']}")
    print(f"  Violaciones flujo: {len(ev['violaciones_flujo'])}")
    print()
    print("Penalizaciones:")
    print(f"  Inicio: {ev['penalizacion_inicio']}")
    print(f"  Meta: {ev['penalizacion_meta']}")
    print(f"  Flujo: {ev['penalizacion_flujo']}")
    print(f"  Longitud: {ev['penalizacion_longitud']}")
    print(f"  Subidas: {ev['penalizacion_subidas']}")
    print(f"  Bajadas: {ev['penalizacion_bajadas']}")
    print()
    print(f"Energia por componentes: {ev['energia_componentes']}")
    print(f"Energia QUBO expandido: {energia}")
    coinciden=abs(ev['energia_componentes']-energia)<1e-9
    print(f"Energias coinciden: {coinciden}")
    print(f"Ruta factible segun QUBO: {ev['factible_qubo']}")

    if not coinciden:
        raise AssertionError("Las energias no coinciden.")
    if abs(energia)>1e-9:
        raise AssertionError("La ruta clasica deberia tener energia 0.")

    print()
    print("VALIDACION SUPERADA: Q(ruta clasica) = 0")

def main():
    carpeta=os.path.join(RAIZ,"cuantico","resultados")
    os.makedirs(carpeta,exist_ok=True)
    marca=datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta=os.path.join(carpeta,f"validacion_qubo_ruta_clasica_{ANCHO}x{ALTO}_{marca}.txt")
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