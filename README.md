# Generación Procedural de Contenido (PCG) en Videojuegos mediante Computación Cuántica y Optimización Clásica

> **Trabajo de Fin de Máster (TFM)**  
> **Máster Universitario en Computación Cuántica**  
> **Autora:** Belén Castro  
> **Director:** Paulet  

---

## 🌟 Resumen del Proyecto

Este repositorio contiene el código fuente, modelos matemáticos, algoritmos de resolución y pipelines de renderizado 3D desarrollados para el Trabajo de Fin de Máster. La investigación explora la aplicabilidad, escalabilidad y límites de algoritmos de **Computación Cuántica (QUBO, Annealing Cuántico y QAOA)** en conjunción con **Optimización Clásica Exacta (CP-SAT / ILP)** para resolver problemas de **Generación Procedural de Contenido (PCG)** en videojuegos.

El trabajo se articula en tres escenarios representativos de complejidad creciente:
1. **Caso 1 (Colocación de Coleccionables / $p$-median):** Comparativa entre heurísticos clásicos (PAM), búsqueda exhaustiva, Simulated Annealing sobre QUBO y **QAOA Compacto (4 qubits)** frente al modelo ingenuo directo (20 qubits).
2. **Caso 2 (Niveles de Plataformas Jump & Run):** Modelado de físicas acotadas (subida vertical máxima $\le 2$, caída $\le 3$, saltos sin atajos) mediante CP-SAT y **QUBO Reducido ($C=3.0$)**, analizando la no-convergencia de espacios masivos (QUBO equivalente de 5.504 variables).
3. **Caso 3 (Dungeon Crawler 2D con Gameplay y Rutas):** Formulación conjunta de geometría (balance zonal ferromagnético Ising), ruta principal obligatoria Start $\to$ Goal, rama secundaria de exploración, cofres del tesoro y monstruos enemigos. Incluye el pipeline automatizado de exportación y renderizado fotorrealista en **Blender 3D**.

---

## 🎮 Demostración Interactiva en Jupyter Notebook

Para explorar los resultados, ejecutar los solvers y ver la generación de niveles en tiempo real con renderizado 3D integrado, se incluye un notebook auto-contenido:

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
   │ (CP-SAT / Branch & Bound) │ │ (Matriz Q, offsets, penal)│
   │      [VERDAD TERRENO]     │ └─────────────┬─────────────┘
   └─────────────┬─────────────┘               │
                 │ Bucle de refinamiento       ▼
                 │ y verificación cotas   ┌───────────────────┐
                 └───────────────────────►│ SOLVERS CUÁNTICOS │
                                          │ • SA / QA (D-Wave)│
                                          │ • QAOA (Qiskit)   │
                                          └─────────┬─────────┘
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

### Justificación del Enfoque Híbrido y el Bucle de Validación Clásico
1. **Solvers Exhaustivos vs Heurísticos:** Al diseñar formulaciones QUBO desde cero, utilizar directamente un solver heurístico (como Simulated Annealing o una QPU física) sin conocer a priori la solución óptima teórica impide diagnosticar fallos: si el algoritmo no halla una solución factible, es imposible saber si la formulación es matemáticamente errónea o si el solver cayó en un mínimo local.
2. **CP-SAT como Oráculo de Verdad Terreno:** Se emplea Google CP-SAT (búsqueda sistemática por Branch-and-Bound y propagación de restricciones) como oráculo exacto para certificar factibilidad, unicidad y cotas óptimas antes de trasladar el problema a matrices QUBO.
3. **Simulación de Hardware Cuántico:** Las ejecuciones variacionales (QAOA con Qiskit) y de annealing cuántico se realizan en simulación clásica de referencia (*StatevectorSampler* y *SimulatedAnnealingSampler* de D-Wave Ocean). El acceso comercial a QPUs de D-Wave cerró sus cuotas gratuitas universitarias, con tarifas de cómputo prohibitivas para investigación de máster; sin embargo, todos los modelos QUBO del repositorio son directamente trasladables a procesadores físicos D-Wave Advantage.

---

## 📁 Estructura del Repositorio

```text
├── demo_pipeline_tfm.ipynb          # Notebook interactivo demostrador del pipeline completo
├── requirements.txt                 # Dependencias Python verificadas
├── .gitignore                       # Filtros de exclusión limpios (código puro)
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

## 📊 Principales Resultados Cuantitativos

| Caso de Estudio | Dimensión / Variables | Método Clásico | Método Cuántico | Rendimiento / $TTS_{99}$ | Conclusión |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Caso 1: Monedas** | 4 qubits (compacto) vs 20 qubits | PAM / Exhaustivo | QAOA ($p=1$, COBYLA) | $TTS = 0.28\text{ s}$ (4q) frente a $\infty$ (20q) | El precalculo matricial $C(j, l)$ reduce el espacio de Hilbert en 5 órdenes de magnitud y hace viable a QAOA. |
| **Caso 2: Plataformas** | 5.504 vars (equiv) vs Reducido | CP-SAT | Simulated Annealing | $TTS = 1.87\text{ s}$ (Reducido) | Espacios ingenuos masivos colapsan los solvers heurísticos en mínimos locales; la reducción es indispensable. |
| **Caso 3: Mazmorra** | 117 variables (Full) | CP-SAT v3 | Simulated Annealing | Factibilidad $>90\%$, $TTS \approx 0.05\text{ s}$ | CP-SAT valida la consistencia lógica antes de exportar a QUBO y generar el diorama 3D. |

---

## 📄 Memoria del Trabajo de Fin de Máster

El texto íntegro de la memoria académica, estado del arte, anexos matemáticos y bibliografía asociada se custodian en la documentación oficial del máster. Para consultar el documento completo, referirse a la secretaría del programa o contactar directamente con los autores.
