"""Generador de la Memoria Oficial del Caso 3 para el TFM en formato Word (.docx).

Redacta de forma exhaustiva, rigurosa y en primera persona reflexiva
el capítulo correspondiente al Caso 3 del TFM:
- Generación procedural de geometría 2D basada en cuadrícula con obstáculos y gameplay.
- Modelado clásico en CP-SAT: Demostrador Final (368 vars) vs CP-SAT Core (96 vars).
- Visualización 3D avanzada en Blender con texturas procedurales y render fotorrealista.
- Derivación analítica a priori de multiplicadores de penalización (P > 82 aristas).
- Formulación matemática QUBO: Modelo Desacoplado (48 vars) vs Modelo Integrado (96 vars).
- Validación de variables q de ruta en el QUBO y métricas de calidad (componentes conexas).
- Evaluación de robustez estocástica en 20 semillas con cálculo de Time To Solution (TTS_99).
- Comparativa metodológica integral de 4 vías (CP-SAT Demostrador, CP-SAT Core, QUBO Desacoplado, QUBO Integrado).
- Anexo técnico con derivaciones algebraicas cuadráticas término a término.
"""

from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

BASE_DIR = Path(__file__).resolve().parents[2]
DOCX_PRINCIPAL = BASE_DIR / "TFM-caso3.docx"
DOCX_COMPLETO = BASE_DIR / "TFM-caso3_completo.docx"
DOCX_ACTUALIZADO = BASE_DIR / "TFM-caso3_actualizado.docx"
DOCX_CARPETA = BASE_DIR / "caso3_mapa" / "TFM-caso3.docx"

FIGURA_BLENDER_DEMO = BASE_DIR / "caso3_mapa" / "experimentos" / "figuras" / "caso3_blender_render_6x8.png"
FIGURA_BLENDER_QUBO = BASE_DIR / "caso3_mapa" / "experimentos" / "figuras" / "caso3_blender_qubo_render_6x8.png"
FIGURA_MATPLOTLIB = BASE_DIR / "caso3_mapa" / "experimentos" / "figuras" / "cpsat_6x8_seed42_20260906_175424.png"


def aplicar_formato_celda(cell, bg_color="F2F4F7", bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    """Aplica sombreado de fondo, fuente y alineación a una celda de tabla."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
    tcPr.append(shd)
    for p in cell.paragraphs:
        p.alignment = align
        for r in p.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(9.5)
            r.font.bold = bold


def agregar_callout(doc, texto, titulo="NOTA METODOLÓGICA"):
    """Agrega un recuadro de aviso destacado con borde lateral azul oscuro."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    tbl.columns[0].width = Inches(6.5)

    cell = tbl.cell(0, 0)
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F0F4F8"/>')
    tcPr.append(shd)

    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="1B4965"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r_tit = p.add_run(f"[{titulo}]\n")
    r_tit.bold = True
    r_tit.font.name = "Calibri"
    r_tit.font.size = Pt(10)
    r_tit.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)

    r_txt = p.add_run(texto)
    r_txt.font.name = "Calibri"
    r_txt.font.size = Pt(9.5)
    r_txt.font.color.rgb = RGBColor(0x2B, 0x2D, 0x42)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def construir_memoria():
    print("Iniciando construcción de la memoria oficial del Caso 3...")
    doc = Document()

    # Configuración de márgenes estándar de tesis (2.5 cm / 1.0 inch)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Calibri'
    style_normal.font.size = Pt(11)
    style_normal.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    # =========================================================================
    # PORTADA Y ENCABEZADO
    # =========================================================================
    p_pre = doc.add_paragraph()
    r_pre = p_pre.add_run("TRABAJO FIN DE MÁSTER EN COMPUTACIÓN CUÁNTICA")
    r_pre.font.size = Pt(10)
    r_pre.font.bold = True
    r_pre.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)

    p_title = doc.add_paragraph()
    r_title = p_title.add_run("Caso 3: Generación Procedural de Mapas 2D con Obstáculos, Coherencia Espacial y Elementos de Gameplay")
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x0F, 0x1E, 0x36)
    p_title.paragraph_format.space_after = Pt(4)

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("Comparativa metodológica rigurosa entre Programación por Restricciones (CP-SAT Demostrador vs. CP-SAT Core) y Formulaciones QUBO (Desacoplada vs. Integrada) con Representación 3D Fotorrealista en Blender")
    r_sub.font.size = Pt(12.5)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)
    p_sub.paragraph_format.space_after = Pt(18)

    # =========================================================================
    # SECCIÓN 1: INTRODUCCIÓN Y MOTIVACIÓN
    # =========================================================================
    h1 = doc.add_heading("1. Qué quiero resolver en el Caso 3", level=1)
    h1.paragraph_format.space_before = Pt(12)

    doc.add_paragraph(
        "En los dos casos de estudio precedentes de este Trabajo Fin de Máster abordé problemas de generación procedural con "
        "un grado de acoplamiento espacial intermedio. En el Caso 1 partía de un entorno navegable predefinido, limitando la "
        "optimización combinatoria a la colocación de monedas mediante un modelo de cobertura p-mediana. En el Caso 2 di un paso "
        "más hacia la interacción física diseñando una secuencia de plataformas con saltos balísticos discretos, controlando "
        "alturas y previniendo atajos. No obstante, en ninguno de los dos casos anteriores el optimizador construía la topología "
        "base del terreno; la geometría espacial venía impuesta de antemano."
    )
    doc.add_paragraph(
        "En este tercer y último caso de estudio abordo el desafío definitivo: la síntesis procedural de la propia geometría "
        "del entorno a partir de la nada. El solver debe decidir, para cada celda de una cuadrícula discreta bidimensional, "
        "si se materializa como suelo transitable o como muro infranqueable. La dificultad estriba en que el nivel debe satisfacer "
        "simultáneamente múltiples restricciones de diferente naturaleza matemática: coherencia visual (agrupación de muros en "
        "estructuras legibles y sólidas), navegabilidad dura (existencia de un camino libre e ininterrumpido desde el punto de inicio "
        "START hasta la meta GOAL), balance de densidad espacial (sin salas vacías ni aglomeraciones desproporcionadas) y progresión "
        "narrativa de gameplay (recompensas y amenazas en el recorrido)."
    )

    agregar_callout(
        doc,
        "La pregunta central de investigación en computación cuántica para este caso es: "
        "¿Es preferible integrar todas las variables de ruta temporal dentro del Hamiltoniano cuántico "
        "(aumentando el número de qubits lógicos y la densidad de acoplamientos cuadráticos), o formular un QUBO puro "
        "de geometría basado en interacción espacial tipo Ising y filtrar/validar la navegabilidad mediante algoritmos clásicos? "
        "En esta memoria analizo rigurosamente ambos enfoques frente al estándar clásico exacto.",
        titulo="PREGUNTA DE INVESTIGACIÓN CLAVE"
    )

    # =========================================================================
    # SECCIÓN 2: ESPACIO BASE, ZONAS Y CONTROL DE DENSIDAD
    # =========================================================================
    doc.add_heading("2. Espacio base, partición en zonas y control de densidad", level=1)

    doc.add_paragraph(
        "El espacio de trabajo se define sobre una cuadrícula discreta de M = 6 filas por N = 8 columnas, totalizando 48 celdas. "
        "Fijo la casilla de inicio en la esquina superior izquierda START = (0, 0) y la meta en la esquina inferior derecha GOAL = (5, 7). "
        "La distancia Manhattan mínima entre ambos extremos es exactamente de |5 - 0| + |7 - 0| = 12 pasos, lo que exige una ruta de "
        "al menos 13 celdas consecutivas (paso 0 en START hasta paso 12 en GOAL)."
    )

    doc.add_heading("2.1. El problema de la agregación trivial y la división en cuatro zonas", level=2)
    doc.add_paragraph(
        "En modelos de Ising ferromagnéticos simples, donde el único objetivo es minimizar el perímetro de contacto entre fases "
        "(suelo y pared) bajo una restricción global de muros, cualquier optimizador clásico o cuántico tiende al 'ground state' "
        "geométrico trivial: compactar todos los obstáculos en una masa sólida gigante en una esquina o borde de la cuadrícula. "
        "Desde la óptica del diseño de niveles de videojuegos, esto destruye la experiencia lúdica, convirtiendo el mapa en una sala "
        "vacía con un bloque monolítico arrinconado."
    )
    doc.add_paragraph(
        "Para garantizar un diseño jugable con pasillos y estrangulamientos en todo el recorrido, divido la cuadrícula en cuatro "
        "zonas geométricas disjuntas de 3×4 celdas (12 celdas por zona):\n"
        "• Zona A: filas [0..2], columnas [0..3] (cuadrante superior izquierdo).\n"
        "• Zona B: filas [0..2], columnas [4..7] (cuadrante superior derecho).\n"
        "• Zona C: filas [3..5], columnas [0..3] (cuadrante inferior izquierdo).\n"
        "• Zona D: filas [3..5], columnas [4..7] (cuadrante inferior derecho)."
    )
    doc.add_paragraph(
        "Impongo que cada zona contenga exactamente 5 obstáculos y 7 celdas de suelo. Con ello se asegura un reparto homogéneo "
        "de 20 muros y 28 suelos (41.6% de densidad de obstáculos), forzando una distribución espacial equilibrada."
    )

    # =========================================================================
    # SECCIÓN 3: MODELADO CLÁSICO CP-SAT (DEMOSTRADOR VS CORE)
    # =========================================================================
    doc.add_heading("3. Modelado clásico: CP-SAT Demostrador Completo vs. CP-SAT Core", level=1)

    doc.add_paragraph(
        "Para establecer una línea base formal exacta he empleado el solver de programación por restricciones Google OR-Tools CP-SAT. "
        "Con el propósito de mantener el máximo rigor metodológico, distingo claramente dos formulaciones clásicas:"
    )
    doc.add_paragraph(
        "1. CP-SAT Completo v3 (Demostrador Final de Gameplay):\n"
        "   - Incorpora la geometría completa (48 celdas), la ruta principal de 12 movimientos, y una estructura avanzada de gameplay.\n"
        "   - Rama secundaria ciega de exploración (dead-end de 2 celdas) modelada mediante 116 pares de celdas candidatas evaluadas simultáneamente.\n"
        "   - Elementos de juego: 1 trofeo en ruta temprana (pasos 2..4), 2 enemigos secuenciales en ruta (pasos 5..7 y 9..11), "
        "1 recompensa secreta al final del callejón sin salida, y restricciones de no adyacencia.\n"
        "   - Requiere exactamente 368 variables booleanas en el solver y se resuelve a OPTIMAL en 18.26 segundos con un coste de 22 fronteras.\n\n"
        "2. CP-SAT Core (Geometría + Ruta Principal):\n"
        "   - Resuelve estrictamente el núcleo del problema: 48 celdas de suelo/muro, fijación de START/GOAL, 5 muros por zona, "
        "y ruta principal de longitud 12 con conservación de paso, continuidad ortogonal y compatibilidad con el suelo.\n"
        "   - Comprende 96 variables de decisión (48 para suelo x_c y 48 para pasos de ruta q_{t,c}), exactamente las mismas 96 variables "
        "que componen el QUBO Integrado.\n"
        "   - Se resuelve a OPTIMAL en tan solo 2.19 segundos con un objetivo global de 20 fronteras."
    )

    doc.add_heading("3.1. Función objetivo: Coherencia espacial tipo Ising en el solver clásico", level=2)
    doc.add_paragraph(
        "Para evitar el 'ruido blanco' o patrones caóticos de tablero de ajedrez, minimizamos el perímetro de transición entre "
        "suelo y muro a través de las 82 aristas ortogonales del grafo cuadrangular:\n"
        "min F = sum_{(u,v) in E} |x_u - x_v|\n"
        "En CP-SAT esto se linealiza introduciendo variables auxiliares b_{uv} >= x_u - x_v y b_{uv} >= x_v - x_u, lo que totaliza "
        "178 variables internas en el solver para el modelo Core."
    )

    # Tabla CP-SAT comparativa
    t_cpsat = doc.add_table(rows=7, cols=3)
    t_cpsat.alignment = WD_TABLE_ALIGNMENT.CENTER
    filas_cp = [
        ("Métrica / Parámetro", "CP-SAT Core (Modelo Base)", "CP-SAT v3 (Demostrador Final)"),
        ("Alcance del modelo", "Geometría + Ruta principal", "Geometría + Ruta + Rama + Gameplay"),
        ("Variables de decisión", "96 principales (+ 82 aux.)", "238 principales (+ 130 aux.)"),
        ("Variables totales solver", "178 variables", "368 variables"),
        ("Tiempo de resolución (s)", "2.189 s (CPU monohilo)", "18.257 s (CPU monohilo)"),
        ("Fronteras suelo/pared (F)", "20 transiciones (Óptimo absoluto)", "22 transiciones (Óptimo con gameplay)"),
        ("Componentes conexas de suelo", "1 única componente (100% conexo)", "1 única componente (100% conexo)"),
    ]
    for i, fila in enumerate(filas_cp):
        for j, texto in enumerate(fila):
            c = t_cpsat.cell(i, j)
            c.text = texto
            bg = "1B4965" if i == 0 else ("E9ECEF" if j == 0 else "FFFFFF")
            aplicar_formato_celda(c, bg_color=bg, bold=(i == 0 or j == 0))
            if i == 0:
                for r in c.paragraphs[0].runs:
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Incrustar imagen Matplotlib
    if FIGURA_MATPLOTLIB.exists():
        p_img_m = doc.add_paragraph()
        p_img_m.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_img_m = p_img_m.add_run()
        run_img_m.add_picture(str(FIGURA_MATPLOTLIB), width=Inches(5.2))
        p_cap_m = doc.add_paragraph()
        p_cap_m.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap_m = p_cap_m.add_run("Figura 1: Mapa 2D generado por CP-SAT v3 (Matplotlib) mostrando suelo transitable, muros agrupados, ruta principal, bifurcación ciega, trofeos y enemigos secuenciales.")
        r_cap_m.font.size = Pt(9)
        r_cap_m.font.italic = True
        p_cap_m.paragraph_format.space_after = Pt(14)

    # =========================================================================
    # SECCIÓN 4: VISUALIZACIÓN EN BLENDER
    # =========================================================================
    doc.add_heading("4. Visualización tridimensional fotorrealista en Blender", level=1)
    doc.add_paragraph(
        "Para evaluar la calidad arquitectónica y la riqueza espacial de las soluciones optimizadas, he integrado un pipeline "
        "de renderizado 3D en Blender 5.2 mediante scripts automatizados en Python (bpy). El nivel se exporta en JSON estructurado "
        "y se reconstruye proceduralmente con texturas y geometría de alta fidelidad:"
    )
    doc.add_paragraph(
        "• Cantería de muros real: Bloques prismáticos de 2.2 m de altura con material procedural de piedra caliza oscura, "
        "relieve micro-superficial (Bump Map 3D con Noise Texture) y biselado físico en las aristas para resaltar el volumen arquitectónico.\n"
        "• Suelo de pizarra: Losas cuadradas de 2.0×2.0 m con juntas físicas de separación de 8 cm, variación aleatoria de reflectividad "
        "y rugosidad áspera para evitar superficies planas artificiales.\n"
        "• Monstruos demoníacos 3D: Enemigos modelados con cuerpo orgánico escamado, cuernos curvados, fauces abiertas con colmillos "
        "afilados, alas dorsales y un ojo ciclópeo carmesí con shader de emisión volumétrica.\n"
        "• Cofres de tesoro y altares: Recompensas en ruta representadas por arcas de madera noble con refuerzos dorados, remaches y "
        "tapa entreabierta con gema flotante radiante. En la rama secreta se erige un altar rúnico con orbe de amatista.\n"
        "• Portales rúnicos y rutas de neón: Vórtices de inicio (verde esmeralda) y meta (dorado ámbar) acompañados de tubos volumétricos "
        "que ilustran el camino principal y las bifurcaciones exploratorias."
    )

    # Incrustar render CP-SAT Blender
    if FIGURA_BLENDER_DEMO.exists():
        p_img_b = doc.add_paragraph()
        p_img_b.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_img_b = p_img_b.add_run()
        run_img_b.add_picture(str(FIGURA_BLENDER_DEMO), width=Inches(6.0))
        p_cap_b = doc.add_paragraph()
        p_cap_b.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap_b = p_cap_b.add_run("Figura 2. Ejemplo del nivel completo generado mediante CP-SAT, incluyendo obstáculos, ruta principal, dos enemigos, una recompensa sobre la ruta y una recompensa adicional situada al final de una rama secundaria.")
        r_cap_b.font.size = Pt(9)
        r_cap_b.font.italic = True
        p_cap_b.paragraph_format.space_after = Pt(14)

    # =========================================================================
    # SECCIÓN 5: DERIVACIÓN A PRIORI DE PENALIZACIONES (P > 82)
    # =========================================================================
    doc.add_heading("5. Derivación analítica a priori de multiplicadores de penalización (P > 82)", level=1)

    doc.add_paragraph(
        "Uno de los aspectos metodológicos más críticos en la formulación de Hamiltonianos QUBO es la calibración de los "
        "multiplicadores de penalización P. En muchos trabajos se recurre a ajustes empíricos por ensayo y error o se calibran "
        "los pesos conociendo de antemano el óptimo clásico, lo que resta rigor teórico al modelo cuántico. "
        "En este trabajo resuelvo esta deficiencia derivando una cota matemática universal a priori basada exclusivamente en la topología del grafo."
    )

    doc.add_heading("5.1. Demostración formal de la cota superior del objetivo", level=2)
    doc.add_paragraph(
        "En una cuadrícula cartesiana 2D de dimensiones M = 6 filas y N = 8 columnas, las aristas representan pares de celdas "
        "adyacentes ortogonales. El número total de aristas internas |E| se descompone exactamente en aristas horizontales y verticales:\n"
        "• Aristas horizontales: M * (N - 1) = 6 * (8 - 1) = 6 * 7 = 42 aristas.\n"
        "• Aristas verticales: (M - 1) * N = (6 - 1) * 8 = 5 * 8 = 40 aristas.\n"
        "Número total de aristas: |E| = 42 + 40 = 82 aristas."
    )
    doc.add_paragraph(
        "Dado que la función objetivo mide las fronteras suelo/muro sumando transiciones booleanas a lo largo de las aristas:\n"
        "F = sum_{(u,v) in E} |x_u - x_v| con x_u, x_v in {0, 1}\n"
        "Cada término |x_u - x_v| está acotado en el intervalo [0, 1]. Por consiguiente, el valor del objetivo satisface estrictamente:\n"
        "0 <= F <= |E| = 82"
    )

    agregar_callout(
        doc,
        "Teorema de dominancia de penalizaciones a priori: "
        "Si fijamos un multiplicador de penalización P > 82 (por ejemplo, P = 100), se garantiza analíticamente que la violación "
        "de cualquier restricción dura incrementará la energía en al menos P >= 100, siendo energéticamente superior (penalizada) "
        "a cualquier configuración factible. Como el objetivo de fronteras nunca puede superar F = 82, el ground state del sistema "
        "nunca sacrificará una restricción para reducir fronteras, garantizando la viabilidad a priori sin necesidad de calibración ad-hoc.",
        titulo="GARANTÍA MATEMÁTICA A PRIORI"
    )

    # =========================================================================
    # SECCIÓN 6: FORMULACIÓN QUBO DESACOPLADA (48 VARIABLES)
    # =========================================================================
    doc.add_heading("6. Primera formulación QUBO: Modelo Desacoplado (48 variables)", level=1)
    doc.add_paragraph(
        "Bajo el paradigma QUBO, las decisiones se codifican mediante variables binarias x_i in {0, 1}. En el modelo desacoplado, "
        "el sistema cuántico se enfoca exclusivamente en generar una geometría balanceada y estéticamente coherente, delegando la "
        "verificación de ruta a un filtro clásico. El Hamiltoniano total se expresa como:\n"
        "H_desacoplado = H_fronteras + P * H_zonas + P * H_start_goal"
    )
    doc.add_paragraph(
        "1. Término de coherencia espacial tipo Ising:\n"
        "   Para variables booleanas {0, 1}, la distancia |x_u - x_v| se formula exactamente como el polinomio cuadrático:\n"
        "   |x_u - x_v| = x_u + x_v - 2 * x_u * x_v\n"
        "   No requiere variables auxiliares y suma 1 si las celdas difieren y 0 si coinciden.\n"
        "2. Balance de obstáculos por zona (S = 7 suelos en 12 celdas con P = 100):\n"
        "   P * (sum_{i in Z} x_i - 7)^2 = 100 * [ -13 * sum_{i in Z} x_i + 2 * sum_{i < j in Z} x_i * x_j + 49 ]\n"
        "3. Puntos fijos START y GOAL:\n"
        "   P * [ (1 - x_START) + (1 - x_GOAL) ] = 100 * (1 - x_0) + 100 * (1 - x_47)"
    )
    doc.add_paragraph(
        "Esta formulación utiliza exactamente 48 variables binarias y 278 términos cuadráticos. Es extraordinariamente compacta "
        "y se embebe con gran facilidad en arquitecturas de Quantum Annealing."
    )

    # =========================================================================
    # SECCIÓN 7: FORMULACIÓN QUBO INTEGRADA (96 VARIABLES) Y VALIDACIÓN
    # =========================================================================
    doc.add_heading("7. Segunda formulación QUBO: Modelo Integrado (96 variables) y Validación de Ruta", level=1)
    doc.add_paragraph(
        "La limitación del modelo desacoplado es que la geometría generada no garantiza la existencia de un camino libre "
        "hacia la meta. Para forzar la navegabilidad dentro del propio operador Hamiltoniano, incorporo variables de ruta q_{t,c} in {0, 1}, "
        "donde q_{t,c} = 1 indica que el paso t de la ruta (t in [0..12]) transita por la celda c."
    )

    doc.add_heading("7.1. Poda geométrica de Manhattan para contención del espacio cuántico", level=2)
    doc.add_paragraph(
        "Si creáramos una variable q_{t,c} para cada celda c en cada instante t, necesitaríamos 13 * 48 = 624 variables binarias, "
        "lo que desbordaría la capacidad de los procesadores cuánticos actuales. Para evitarlo, aplico una poda geométrica rigurosa "
        "basada en conos de accesibilidad de Manhattan:\n"
        "Una celda c = (r, c) solo puede ser visitada en el paso t si:\n"
        "dist(START, c) <= t   y   dist(c, GOAL) <= (12 - t)\n"
        "Para una cuadrícula 6×8 con camino mínimo de 12 movimientos (13 celdas), los conos reducen los candidatos temporales a exactamente "
        "48 variables podadas q_{t,c} (excluyendo START y GOAL fijados). Así, el modelo integrado consta de exactamente:\n"
        "48 variables de celda x_c + 48 variables de ruta q_{t,c} = 96 variables binarias totales."
    )

    doc.add_heading("7.2. Restricciones del camino integradas en el Hamiltoniano", level=2)
    doc.add_paragraph(
        "El Hamiltoniano integrado incorpora tres penalizaciones cuadráticas con P = 100:\n"
        "1. Unicidad de posición en cada paso temporal: P * sum_{t=1}^{11} (sum_{c in Cand_t} q_{t,c} - 1)^2.\n"
        "2. Continuidad espacial ortogonal: penalización P * q_{t, a} * q_{t+1, b} para todo par (a, b) tal que dist_Manhattan(a, b) != 1.\n"
        "3. Compatibilidad con el terreno (la ruta solo pisa suelo transitable): P * q_{t, c} * (1 - x_c) = P * q_{t, c} - P * q_{t, c} * x_c."
    )

    doc.add_heading("7.3. Validación rigurosa de variables q vs. BFS", level=2)
    doc.add_paragraph(
        "Una aportación metodológica crucial de esta memoria es la distinción entre navegabilidad de la matriz x mediante BFS "
        "y validación interna de las variables de ruta q del QUBO. Un algoritmo BFS tradicional aplicado a x certifica que existe un "
        "camino topológico libre entre START y GOAL, pero NO garantiza que las variables q obtenidas por el muestreador cuántico "
        "hayan satisfecho todas las penalizaciones sin rupturas. Por ello, implemento la función validar_ruta_qubo() que comprueba:\n"
        "a) Que exista exactamente un q_{t,c} = 1 por cada paso t.\n"
        "b) Que cada paso consecutivo sea adyacente en el grafo ortogonal.\n"
        "c) Que para cada celda visitada por la ruta se cumpla estrictamente x_c = 1.\n"
        "Los resultados demuestran que el QUBO integrado alcanza un 93.6% de cumplimiento simultáneo de ruta q válida y zonas correctas."
    )

    # Incrustar render QUBO Blender
    if FIGURA_BLENDER_QUBO.exists():
        p_img_bq = doc.add_paragraph()
        p_img_bq.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_img_bq = p_img_bq.add_run()
        run_img_bq.add_picture(str(FIGURA_BLENDER_QUBO), width=Inches(6.0))
        p_cap_bq = doc.add_paragraph()
        p_cap_bq.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap_bq = p_cap_bq.add_run("Figura 3. Ejemplo de una solución válida del modelo QUBO integrado obtenida mediante Simulated Annealing. La visualización representa la geometría generada y la ruta q de 12 movimientos entre START y GOAL; los elementos adicionales de gameplay no forman parte del modelo QUBO core.")
        r_cap_bq.font.size = Pt(9)
        r_cap_bq.font.italic = True
        p_cap_bq.paragraph_format.space_after = Pt(10)

        agregar_callout(
            doc,
            "Aviso metodológico sobre la comparación visual: Las Figuras 2 y 3 NO representan una comparativa visual directa del mismo alcance de problema. "
            "La Figura 2 demuestra la capacidad expresiva del generador final clásico (CP-SAT v3) integrando bifurcaciones ciegas y actores lúdicos completos (monstruos y cofres). "
            "Por su parte, la Figura 3 ilustra la solución al problema fundamental cuántico de síntesis geométrica con ruta navegable (modelo Core), "
            "evitando inflar innecesariamente el Hamiltoniano con variables de gameplay que no forman parte del núcleo de conectividad.",
            titulo="DISTINCIÓN VISUAL: DEMOSTRADOR GAMEPLAY VS. MODELO CUÁNTICO CORE"
        )

    # =========================================================================
    # SECCIÓN 8: EVALUACIÓN EXPERIMENTAL, ROBUSTEZ Y TIME TO SOLUTION (TTS)
    # =========================================================================
    doc.add_heading("8. Evaluación experimental: robustez en 20 semillas y Time To Solution (TTS)", level=1)
    doc.add_paragraph(
        "Para evaluar empíricamente ambas formulaciones bajo condiciones estrictamente comparables, se utilizó Simulated Annealing "
        "(dwave-samplers) con 100 lecturas (reads), 1.500 sweeps de enfriamiento y la penalización teórica P = 100.0, "
        "repitiendo el experimento en las mismas 20 semillas aleatorias independientes para ambos modelos QUBO."
    )

    doc.add_heading("8.1. Definición formal de Time To Solution (TTS_99)", level=2)
    doc.add_paragraph(
        "El Time To Solution es la métrica estándar en computación cuántica y optimización heurística para cuantificar el tiempo "
        "esperado de cómputo necesario para obtener al menos una solución óptima válida con una probabilidad de certeza del 99%:\n"
        "TTS_99 = t_read * [ ln(1 - 0.99) / ln(1 - p_éxito) ]\n"
        "donde t_read es el tiempo medio de muestreo por lectura en CPU clásica (tiempo total / número de reads) y p_éxito es la probabilidad "
        "de que una lectura aleatoria satisfaga simultáneamente todas las restricciones duras del problema.\n\n"
        "Es fundamental precisar que el valor obtenido corresponde a una estimación empírica de TTS en CPU clásica mediante Simulated Annealing, "
        "calculada a partir del tiempo de muestreo por lectura y la tasa observada. No representa el tiempo de ciclo físico de un procesador cuántico (QPU)."
    )

    doc.add_heading("8.2. Mínimo de energía vs. Mejor muestra válida", level=2)
    doc.add_paragraph(
        "Un fenómeno de gran interés científico es la divergencia entre la muestra de menor energía bruta y la mejor muestra válida. "
        "En el QUBO desacoplado, la muestra de mínima energía obtiene 31.80 fronteras pero a menudo bloquea el camino (inviable), "
        "mientras que la mejor muestra válida requiere 34.55 fronteras para permitir la ruta de 12 movimientos. "
        "En cambio, en el QUBO integrado, gracias a las 48 variables de ruta q y al acoplamiento de compatibilidad con el suelo, "
        "la muestra de mínima energía coincide con la mejor muestra válida (29.25 fronteras) en la totalidad de las 20 semillas ensayadas."
    )

    # Tabla de Robustez Integrado (Homogeneizada a 20 semillas idénticas)
    t_rob = doc.add_table(rows=6, cols=3)
    t_rob.alignment = WD_TABLE_ALIGNMENT.CENTER
    filas_rob = [
        ("Métrica Estadística (20 semillas)", "QUBO Desacoplado (48 vars)", "QUBO Integrado (96 vars)"),
        ("Tasa media de cumplimiento de zonas", "100.0% (Estricto P=100)", "100.0% (Estricto P=100)"),
        ("Tasa media de éxito / ruta válida", "8.30% ± 2.51% (Filtro BFS)", "93.60% ± 2.35% (Ruta q válida)"),
        ("Fronteras de la mejor solución válida", "34.55 ± 2.13 transiciones", "29.25 ± 2.14 transiciones"),
        ("Estimación empírica TTS_99 en CPU", "63.47 ± 28.29 ms", "4.39 ± 0.60 ms"),
        ("Tiempo medio de muestreo (100 reads)", "0.104 s (en CPU)", "0.209 s (en CPU)"),
    ]
    for i, fila in enumerate(filas_rob):
        for j, texto in enumerate(fila):
            c = t_rob.cell(i, j)
            c.text = texto
            bg = "1B4965" if i == 0 else ("E9ECEF" if j == 0 else "FFFFFF")
            aplicar_formato_celda(c, bg_color=bg, bold=(i == 0 or j == 0))
            if i == 0:
                for r in c.paragraphs[0].runs:
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # =========================================================================
    # SECCIÓN 9: COMPARATIVA METODOLÓGICA MAESTRA (4 VÍAS)
    # =========================================================================
    doc.add_heading("9. Comparativa metodológica integral: 4 Enfoques en el Caso 3", level=1)
    doc.add_paragraph(
        "La siguiente tabla condensa la comparativa exhaustiva entre los cuatro modelos implementados en el Caso 3, "
        "reportando datos consolidados y estadísticamente homogéneos (media ± desviación típica en 20 semillas para ambos modelos QUBO):"
    )

    # Tabla Maestra 4 Vías
    t_comp = doc.add_table(rows=12, cols=5)
    t_comp.alignment = WD_TABLE_ALIGNMENT.CENTER
    filas_comp = [
        ("Métrica Comparativa", "CP-SAT Demostrador", "CP-SAT Core", "QUBO Desacoplado", "QUBO Integrado"),
        ("Problema resuelto", "Geo + Ruta + Gameplay", "Geometría + Ruta", "Geometría pura", "Geometría + Ruta q"),
        ("Variables de decisión", "238 (+ 130 aux.)", "96 (+ 82 aux.)", "48 variables", "96 variables"),
        ("Variables totales solver", "368 variables", "178 variables", "48 variables", "96 variables"),
        ("Términos cuadráticos", "N/A (modelo CP-SAT)", "N/A (modelo CP-SAT)", "278 términos", "541 términos"),
        ("Tiempo de resolución (s)", "18.257 s", "2.189 s", "0.104 s (media SA)", "0.209 s (media SA)"),
        ("Fronteras (mejor válida)", "22 (Óptimo)", "20 (Óptimo)", "34.55 ± 2.13", "29.25 ± 2.14"),
        ("Fronteras (mínimo energía)", "22 (Óptimo)", "20 (Óptimo)", "31.80 ± 1.86", "29.25 ± 2.14"),
        ("Cumplimiento de zonas", "100.0% (Exacto)", "100.0% (Exacto)", "100.0% (P=100)", "100.0% (P=100)"),
        ("Tasa de éxito / navegable", "100.0% (Garantizado)", "100.0% (Garantizado)", "8.30% ± 2.51% (BFS)", "93.60% ± 2.35% (Ruta q)"),
        ("Longitud de ruta START->GOAL", "12 mov. (13 celdas)", "12 mov. (13 celdas)", "12 mov. (13 celdas)", "12 mov. (13 celdas)"),
        ("Estimación empírica TTS_99 en CPU", "N/A (Determinista)", "N/A (Determinista)", "63.47 ± 28.29 ms", "4.39 ± 0.60 ms"),
    ]

    for i, fila in enumerate(filas_comp):
        for j, texto in enumerate(fila):
            c = t_comp.cell(i, j)
            c.text = texto
            bg = "1B4965" if i == 0 else ("E9ECEF" if j == 0 else "FFFFFF")
            aplicar_formato_celda(c, bg_color=bg, bold=(i == 0 or j == 0))
            if i == 0:
                for r in c.paragraphs[0].runs:
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    doc.add_heading("9.1. Discusión científica y trade-offs metodológicos", level=2)
    doc.add_paragraph(
        "Del análisis comparativo riguroso de 4 vías se extraen conclusiones científicas de gran relevancia metodológica:\n"
        "1. La comparación rigurosa 1-a-1: Contrastar el QUBO Integrado (96 variables) contra el CP-SAT Demostrador (368 variables) "
        "era asimétrico debido a las 116 ramas candidatas y la lógica de gameplay. Al crear el CP-SAT Core (exactamente las mismas "
        "96 variables de decisión principales), la comparativa resulta limpia y formal: CP-SAT resuelve el núcleo en 2.19 s alcanzando "
        "el óptimo global de 20 fronteras, mientras que el QUBO integrado resuelve en 0.20 s alcanzando 29 fronteras con una estimación "
        "empírica de TTS_99 en CPU de 4.39 ms.\n\n"
        "2. Carácter determinista vs. muestreo heurístico (precaución sobre el concepto de velocidad): Es crucial no confundir tiempos de "
        "ejecución con garantías matemáticas de resolución. CP-SAT devuelve estado OPTIMAL, certificando la optimalidad para la formulación "
        "considerada (20 fronteras). En cambio, Simulated Annealing es una metaheurística estocástica que obtiene 100 muestras aproximadas "
        "en una superficie de energía rugosa. No se debe hablar de un 'speedup' en sentido estricto, sino de dos paradigmas con garantías diferentes.\n\n"
        "3. El trade-off real: Factibilidad vs. Calidad espacial: El QUBO integrado logra un avance decisivo en factibilidad, elevando la "
        "tasa de éxito del 8.30% al 93.60%. Sin embargo, el muestreo heurístico no recupera con la misma consistencia la calidad visual del "
        "óptimo clásico (promedio de 29.25 ± 2.14 fronteras frente a las 20 del CP-SAT). Esta discrepancia es un resultado científicamente "
        "honesto y valioso: el acoplamiento de restricciones duras en el Hamiltoniano estabiliza la navegabilidad pero dificulta que el sampler "
        "alcance el mínimo absoluto del término de coherencia espacial.\n\n"
        "4. Componentes conexas de suelo como métrica de calidad: La solución del QUBO integrado renderizada en Blender presenta 3 componentes "
        "de suelo (la componente principal que contiene la ruta de 13 celdas / 12 movimientos START->GOAL y dos bolsas secundarias de suelo desconectadas). "
        "Esto no invalida la condición de navegabilidad START->GOAL definida para el experimento, que queda plenamente garantizada por las variables q y el BFS. "
        "En el conjunto de las 20 semillas, aproximadamente el 50% de las soluciones válidas presentan una única componente conexa y el resto 2 o 3. "
        "Forzar la conectividad global de todas las celdas transitables requeriría variables y restricciones auxiliares adicionales —por ejemplo mediante "
        "formulaciones de flujo o estructuras de conectividad—, aumentando significativamente el tamaño y la densidad del QUBO. Por ello se mantiene como métrica de calidad y no como restricción dura."
    )

    # =========================================================================
    # SECCIÓN 10: CONCLUSIONES GENERALES
    # =========================================================================
    doc.add_heading("10. Conclusiones del Caso 3 y del TFM", level=1)
    doc.add_paragraph(
        "El Caso 3 cierra con éxito la trilogía de aplicaciones de optimización cuántica a la generación procedural de contenido (PCG). "
        "Los hitos técnicos alcanzados en este capítulo comprenden:\n"
        "• Demostración de que la coherencia visual de muros en mapas discretos equivale de forma natural a un modelo ferromagnético "
        "de Ising en variables binarias {0, 1} sin sobrecoste de variables auxiliares.\n"
        "• Derivación analítica a priori de la cota superior del objetivo (F <= 82 aristas), justificando formalmente multiplicadores "
        "P = 100 sin sintonización empírica ad-hoc.\n"
        "• Diseño del cono de Manhattan para podar variables temporales, logrando un modelo integrado de ruta en solo 96 variables.\n"
        "• Validación experimental de robustez en 20 semillas con una tasa de éxito del 93.6% y un TTS_99 de 4.39 ms en Simulated Annealing.\n"
        "• Renderizado 3D fotorrealista en Blender 5.2 con materiales procedurales de cantería y criaturas 3D completas, cerrando el puente "
        "entre formulación matemática cuántica y desarrollo visual de videojuegos."
    )

    # =========================================================================
    # ANEXO TÉCNICO: ÁLGEBRA CUADRÁTICA QUBO
    # =========================================================================
    doc.add_heading("Anexo Técnico: Derivaciones Algebraicas Término a Término", level=1)
    doc.add_paragraph(
        "A continuación se presenta el desarrollo formal de la expansión de cada término del Hamiltoniano en variables binarias x, q in {0, 1}:"
    )
    doc.add_paragraph(
        "A1. Coherencia Espacial (Fronteras de Ising):\n"
        "Para cada arista (u, v) in E:\n"
        "|x_u - x_v| = (x_u - x_v)^2 = x_u^2 + x_v^2 - 2 * x_u * x_v\n"
        "Como x_i^2 = x_i para variables binarias idempotentes:\n"
        "|x_u - x_v| = x_u + x_v - 2 * x_u * x_v\n"
        "Matriz QUBO: Q[u, u] += 1, Q[v, v] += 1, Q[u, v] += -2.\n\n"
        "A2. Restricción de Suma de Zona (S = 7 en n = 12 celdas con peso P):\n"
        "P * (sum_{i=1}^{12} x_i - 7)^2 = P * [ (sum x_i)^2 - 14 * sum x_i + 49 ]\n"
        "= P * [ sum x_i^2 + 2 * sum_{i<j} x_i * x_j - 14 * sum x_i + 49 ]\n"
        "= P * [ -13 * sum_{i=1}^{12} x_i + 2 * sum_{i<j} x_i * x_j + 49 ]\n"
        "Matriz QUBO: Q[i, i] += -13 * P, Q[i, j] += 2 * P (para i < j), constante += 49 * P.\n\n"
        "A3. Unicidad de Paso Temporal en la Ruta Integrada (1 celda por paso t):\n"
        "P * (sum_{c in Cand_t} q_{t, c} - 1)^2 = P * [ -1 * sum_{c} q_{t, c} + 2 * sum_{c < c'} q_{t, c} * q_{t, c'} + 1 ]\n"
        "Matriz QUBO: Q[q_{t,c}, q_{t,c}] += -P, Q[q_{t,c}, q_{t,c'}] += 2 * P, constante += P.\n\n"
        "A4. Compatibilidad Ruta-Terreno (No pisar muros):\n"
        "P * q_{t, c} * (1 - x_c) = P * q_{t, c} - P * q_{t, c} * x_c\n"
        "Matriz QUBO: Q[q_{t,c}, q_{t,c}] += P, Q[q_{t,c}, x_c] += -P."
    )

    # Guardar en rutas seguras
    guardado_exitoso = False
    for ruta_guardado in [DOCX_ACTUALIZADO, DOCX_CARPETA, DOCX_COMPLETO, DOCX_PRINCIPAL]:
        try:
            ruta_guardado.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(ruta_guardado))
            print(f"Documento guardado con éxito en: {ruta_guardado}")
            print(f"Tamaño: {ruta_guardado.stat().st_size / 1024:.1f} KB")
            guardado_exitoso = True
        except PermissionError:
            print(f"Aviso: {ruta_guardado} está bloqueado por Microsoft Word. Continuando...")

    if not guardado_exitoso:
        raise IOError("No se pudo guardar la memoria en ninguna de las rutas objetivo.")

    print("=" * 65)
    print("MEMORIA OFICIAL DEL CASO 3 GENERADA EXITOSAMENTE")
    print("=" * 65)


if __name__ == "__main__":
    construir_memoria()
