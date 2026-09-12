# Generación Procedural de Contenido (PCG) en Videojuegos mediante Computación Cuántica y Optimización Clásica

> **Trabajo de Fin de Máster (TFM)**  
> **Máster Universitario en Computación Cuántica**  
> **Autora:** Belén Castañera  
> **Director:** Paulet  

---

## 🌟 Resumen del Proyecto

Este repositorio contiene el código fuente, modelos matemáticos, experimentos reproducibles y pipelines de renderizado 3D desarrollados para el Trabajo de Fin de Máster. La investigación analiza la viabilidad, escalabilidad y transformaciones de codificación necesarias para aplicar **Computación Cuántica (QUBO, Recocido Cuántico y QAOA)** en conjunción con **Optimización Clásica Exacta (Google CP-SAT)** en problemas de **Generación Procedural de Contenido (PCG)** en videojuegos.

El trabajo aborda tres escenarios representativos de dificultad creciente:
1. **Caso 1 (Colocación de Coleccionables / $p$-median):** Comparativa entre heurísticos clásicos (PAM), búsqueda exhaustiva, Simulated Annealing sobre QUBO y **QAOA Compacto (4 qubits)** frente al modelo lineal directo ingenuo (20 qubits). Demuestra cómo la reformulación algebraica compacta reduce el espacio de búsqueda en 5 órdenes de magnitud y hace viable el algoritmo variacional.
2. **Caso 2 (Niveles de Plataformas Jump & Run):** Modelado de físicas cinemáticas acotadas (subida vertical máxima $\le 2$, caída física $\le 3$, saltos sin atajos) mediante CP-SAT y **QUBO Reducido ($C=3.0$)**, estudiando el colapso por rugosidad de espacios masivos (QUBO equivalente de 5.504 variables).
3. **Caso 3 (Dungeon Crawler 2D con Gameplay y Rutas):** Formulación conjunta de geometría (balance zonal ferromagnético Ising), ruta principal obligatoria Start $\to$ Goal, rama secundaria de exploración, cofres del tesoro y monstruos enemigos. Incluye el pipeline automatizado de exportación y renderizado fotorrealista en **Blender 3D**.

---

## 🎮 Demostración Interactiva en Jupyter Notebook

Para explorar los resultados, ejecutar los solvers y ver la generación de niveles en tiempo real con renderizado 3D integrado, se incluye un notebook auto-contenido y completamente ejecutado:

👉 **[`demo_pipeline_tfm.ipynb`](demo_pipeline_tfm.ipynb)**

El notebook permite:
* Seleccionar parámetros de entrada en vivo (semillas, dimensiones, coleccionables).
* Comparar tiempos de ejecución y probabilidades de éxito en tiempo real.
* Generar las plantas de nivel 2D interactivas con `matplotlib`.
* Disparar el renderizado fotorrealista en segundo plano con Blender 5.2 y desplegar la escena 3D resultante directamente en el notebook.

---

## 🏛️ Arquitectura Metodológica y Flujo de Trabajo

El flujo metodológico del proyecto combina métodos exactos clásicos con formulaciones cuadráticas cuánticas:

```
   ┌────────────────────────────────────────────────────────┐
   │         PARÁMETROS DE ENTRADA AL PROCEDURAL            │
   │  (Dimensiones, saltos, densidad, coleccionables, etc.) │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │         FORMULACIÓN MATEMÁTICA FORMAL (ILP/MIP)        │
   └─────────────┬───────────────────────────┬──────────────┘
                 │                           │
                 ▼                           ▼
   ┌───────────────────────────┐ ┌───────────────────────────┐
   │ VALIDACIÓN CLÁSICA EXACTA │ │     FORMULACIÓN QUBO      │
   │   (Google OR-Tools CP-SAT)│ │ (Matriz Q, offsets, penal)│
   │ [VERIFICACIÓN DETERMINISTA│ └─────────────┬─────────────┘
   │   DE ÓPTIMO / FACTIBILIDAD│               │
   └─────────────┬─────────────┘               │
                 │ Bucle de refinamiento       ▼
                 │ y verificación cotas   ┌─────────────────────────────────────────┐
                 └───────────────────────►│          RESOLUCIÓN Y MUESTREO          │
                                          │                                         │
                                          │  [Heurística Clásica sobre QUBO]        │
                                          │  • Simulated Annealing (D-Wave Ocean)   │
                                          │                                         │
                                          │  [Computación Cuántica]                 │
                                          │  • Quantum Annealing (QPU física)*      │
                                          │  • QAOA Variacional (Qiskit / Gate-based│
                                          └────────────────────┬────────────────────┘
                                                               │
                                                               ▼
   ┌────────────────────────────────────────────────────────┐
   │        VALIDACIÓN DE FACTIBILIDAD Y MÉTRICAS           │
   │     (Ausencia de atajos, TTS99, energía óptima)        │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │              EXPORTACIÓN JSON NORMALIZADA              │
   │        (Geometría, coordenadas, rutas, entidades)      │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │             BLENDER 3D (RENDERIZADO HEADLESS)          │
   │     (Texturas procedurales, monstruos, cofres, luces)  │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │              ESCENA 3D Y DIORAMA FINAL                 │
   └────────────────────────────────────────────────────────┘
```
*\* Formulación matemáticamente apta para quantum annealing, sujeta a incrustación topológica (minor embedding) y restricciones de conectividad hardware.*

---

### Justificación del Enfoque Híbrido y el Bucle de Validación Clásico
1. **Rol de Google CP-SAT como Solver Exacto Basado en Restricciones:** CP-SAT combina propagación de dominios, aprendizaje de cláusulas en conflicto (CDCL proveniente de solvers SAT) y relajaciones lineales mediante branch-and-cut. No realiza una búsqueda ingenua por fuerza bruta, sino una poda analítica rigurosa capaz de certificar deterministamente la optimalidad global o demostrar matemáticamente la infactibilidad de la instancia.
2. **Necesidad de un Oráculo de Verdad Terreno:** Al diseñar formulaciones QUBO desde cero, utilizar directamente un solver heurístico (como Simulated Annealing o una QPU física) sin conocer a priori la solución óptima teórica impide diagnosticar fallos: si el algoritmo no halla una solución factible, es imposible saber si la formulación es matemáticamente errónea o si el solver estocástico cayó en un mínimo local.
3. **Simulación de Referencia y Hardware Cuántico:** Las ejecuciones variacionales (QAOA con Qiskit) y de recocido estocástico se realizan en simulación clásica de referencia controlada (*StatevectorSampler* y *SimulatedAnnealingSampler* de D-Wave Ocean). Para el desarrollo de este trabajo no se dispuso de acceso directo a una QPU comercial de recocido cuántico en tiempo de ejecución. No obstante, las matrices QUBO desarrolladas son directamente aptas para recocido cuántico (*quantum annealing*), requiriendo en hardware físico un mapeo de grafo (*minor embedding*) adaptado a las topologías Pegasus o Zephyr de D-Wave.

---

## 📁 Estructura del Repositorio

```text
├── demo_pipeline_tfm.ipynb          # Notebook interactivo demostrador del pipeline completo (pre-ejecutado)
├── requirements.txt                 # Dependencias Python verificadas
├── .gitignore                       # Filtros de exclusión limpios (código puro y datos reproducibles)
│
├── common/                          # Métricas metodológicas comunes
│   └── metricas_tts.py              # Cálculo unificado de Time-To-Solution (TTS99) con ceil discreto
│
├── caso1_colocacion_monedas/        # CASO 1: Colocación de Coleccionables (p-median)
│   ├── modelo/                      # Grafos navegables, distancias y formulaciones QUBO (directa y compacta)
│   ├── solvers/                     # PAM, Búsqueda Exhaustiva, SA QUBO y QAOA Compacto (4 qubits)
│   ├── experimentos/                # Barridos experimentales de TTS, comparativa 20q vs 4q y evolución unitaria
│   ├── figuras/                     # Gráficas académicas comparativas
│   ├── resultados/                  # Benchmarks congelados en JSON y reportes experimentales
│   └── visualizacion/               # Scripts de exportación y renderizado en Blender
│
├── caso2_plataformas/               # CASO 2: Generación de Niveles de Plataformas (Jump & Run)
│   ├── modelo/                      # Grafo cinemático de saltos físicos admisibles (subida <= 2, caída <= 3)
│   ├── cuantico/                    # Formulaciones QUBO (Equivalente vs Reducido C=3.0) y SA
│   ├── solvers/                     # Solvers CP-SAT y validadores de ruta
│   ├── experimentos/                # Barridos de sweeps, parámetros C y anti-atajos
│   ├── figuras/                     # Gráficas de trayectorias
│   └── visualizacion/               # Scripts de escena para Blender
│
├── caso3_mapa/                      # CASO 3: Dungeon 2D con Rutas y Gameplay Completo
│   ├── clasico/                     # Implementación CP-SAT v3 (modelo exacto con ramas y gameplay)
│   ├── formulacion/                 # Modelos QUBO Desacoplado (48v), Integrado (96v) y Completo (117v)
│   ├── solvers/                     # Solver Simulated Annealing con validación topológica dura
│   ├── experimentos/                # Estudios de robustez (20 semillas), comparativas y logs
│   ├── visualizacion/               # Exportador JSON y generador avanzado de escena 3D fotorrealista en Blender
│   └── BITACORA_CASO3.md            # Bitácora detallada de decisiones de diseño y evolución
│
└── recursos_3d/                     # Materiales y recursos complementarios
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el repositorio y configurar el entorno virtual

```bash
git clone https://github.com/belencstr/TFM.git
cd TFM

# Crear entorno virtual en Windows
python -m venv venv
.\venv\Scripts\activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Ejecutar el Notebook Demostrador

```bash
# Lanzar Jupyter Lab / Notebook
jupyter lab demo_pipeline_tfm.ipynb
# o
jupyter notebook demo_pipeline_tfm.ipynb
```

### 3. Ejecutar los Experimentos Principales por Consola

* **Caso 1 (Comparativa QAOA 20q vs 4q):**
  ```bash
  python caso1_colocacion_monedas/experimentos/comparar_qaoa_20q_vs_4q.py
  ```
* **Caso 2 (Barrido TTS QUBO Reducido):**
  ```bash
  python caso2_plataformas/cuantico/experimentos/tts_sa_qubo_reducido_18x5.py
  ```
* **Caso 3 (Resolución CP-SAT v3 y exportación a Blender):**
  ```bash
  python caso3_mapa/visualizacion/exportar_nivel_blender_caso3.py
  ```
* **Renderizado 3D en Blender (Headless):**
  ```bash
  blender -b -P caso3_mapa/visualizacion/visualizar_caso3_blender.py
  ```

---

## 📊 Principales Resultados Cuantitativos Consolidados

A continuación se sintetiza la evidencia cuantitativa de los tres casos de estudio, diferenciando con precisión la naturaleza de cada solver y las formulaciones exploradas:

| Caso de Estudio | Dimensión / Variables | Solver Clásico Exacto | Método / Muestreador sobre QUBO | Rendimiento Experimental ($TTS_{99}$) | Conclusión Metodológica Principal |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Caso 1: Monedas** | 4 qubits (compacto) vs 20 qubits (directo) | Búsqueda Exhaustiva / PAM | **QAOA Variacional** ($p=1$, COBYLA) y **Simulated Annealing** | **QAOA 4q:** $TTS = 0.2872\text{ s}$ (ref. congelada)<br>**QAOA 20q:** $TTS$ no estimable ($p_{\text{opt,emp}}=0$) | El precalculo matricial $C(j, l)$ reduce el espacio de Hilbert en 5 órdenes de magnitud y hace viable el muestreo variacional. |
| **Caso 2: Plataformas** | 5.504 vars (equiv.) vs Reducido ($C=3.0$) | Google CP-SAT | **Simulated Annealing** (heurístico clásico) | **QUBO Reducido:**<br>$TTS_{\text{fact}} \approx 1.894\text{ s}$<br>$TTS_{\text{completa}} \approx 9.075\text{ s}$<br>**QUBO Equiv:** $TTS$ no estimable ($p_{\text{opt,emp}}=0$) | Los espacios QUBO masivos con altas penalizaciones colapsan los solvers heurísticos en mínimos locales; la poda cinemática previa es indispensable. |
| **Caso 3: Mazmorra (Integrado)** | 96 variables (Geometría + Ruta $q$) | Google CP-SAT v3 | **Simulated Annealing** (heurístico clásico) | Factibilidad: $93.60 \pm 2.35\%$<br>$TTS_{99} = 4.39 \pm 0.60\text{ ms}$ | La formulación desacoplada temporal de la ruta garantiza transitabilidad con altísima tasa de éxito. |
| **Caso 3: Mazmorra (Completo)** | 117 variables (Geom + Ruta + Gameplay + Rama) | Google CP-SAT v3 | **Simulated Annealing** (heurístico clásico) | Factibilidad: $54.35 \pm 4.17\%$<br>$TTS_{99} = 19.47 \pm 5.06\text{ ms}$ | Incorporar restricciones de branching y gameplay reduce la factibilidad al ~54%, pero mantiene un $TTS$ de milisegundos plenamente apto para PCG. |

---

## 📄 Memoria del Trabajo de Fin de Máster

El texto íntegro de la memoria académica, estado del arte, anexos matemáticos y bibliografía asociada se custodian en la documentación oficial del máster. Para consultar el documento completo, referirse a la secretaría del programa o contactar directamente con los autores.
