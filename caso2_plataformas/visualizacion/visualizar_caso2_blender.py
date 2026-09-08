r"""Visualización 3D Avanzada en Blender — Caso 2: Generación Procedural de Plataformas (CP-SAT v4 y QUBO).

Transforma el problema combinatorio de plataformas en un nivel 2.5D estilizado y profesional:
- PLATAFORMAS 2.5D MULTICAPA:
  * Capa superior de tránsito de piedra labrada con bisel y sutil veta de musgo.
  * Cuerpo inferior de estrato rocoso escarpado con ménsulas/contrafuertes de soporte.
- CHECKPOINTS DE GAMEPLAY:
  * Start: Campamento de aventurero con fogata de ascuas ardientes, poste indicador y farol cálido.
  * Goal: Santuario de meta con arquería rúnica dorada, cristal radiante flotante y halo de victoria.
- ARCOS PARABÓLICOS DE SALTO (FÍSICA REAL):
  * Trayectorias parabólicas suaves entre plataformas según la física de salto y gravedad.
  * Línea tubular de neón brillante (cian a dorado) con marcadores de aterrizaje en cada plataforma.
- ENTORNO Y ATMÓSFERA:
  * Foso inferior de peligro: Mar de lava/abismo brillante que justifica la necesidad de saltar.
  * Fondo de siluetas de caverna/cordillera en perspectiva parallax.
  * Cámara 2.5D cinematográfica con perspectiva isométrica que muestra el perfil y la superficie superior.

EJECUCIÓN INTERACTIVA:
1. Abre Blender 5.x (o 4.x/3.x) -> Scripting.
2. Abre este fichero y haz clic en "Run Script" (▶).
3. La escena se genera a todo color en modo "Material Preview".

EJECUCIÓN HEADLESS:
  blender -b -P caso2_plataformas/visualizacion/visualizar_caso2_blender.py
"""

from pathlib import Path
import json
import math
import sys

try:
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None


# Asegurar que la carpeta del script esté en sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


# =============================================================================
# CONFIGURACIÓN Y PARÁMETROS
# =============================================================================

RUTA_JSON = None              # None -> Auto-descubre el JSON v4 o QUBO más reciente

TILE_SIZE = 2.0               # Metros por casilla
PROFUNDIDAD_TOP = 3.6         # Fondo de la superficie superior
GROSOR_TOP = 0.35             # Grosor de la losa superior
PROFUNDIDAD_ROCA = 3.2        # Fondo de la roca inferior
GROSOR_ROCA = 0.90            # Altura de la base rocosa

MOSTRAR_ARCOS_SALTO = True
MOSTRAR_ABISMO_LAVA = True
MOSTRAR_FONDO_PARALLAX = True
ACTIVAR_VISTA_MATERIAL = True


# =============================================================================
# LOCALIZACIÓN DEL ARCHIVO JSON
# =============================================================================

def obtener_ruta_json():
    import os
    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            p = Path(sys.argv[idx + 1])
            if p.exists():
                return p

    if os.environ.get("CASO2_BLENDER_JSON"):
        p = Path(os.environ["CASO2_BLENDER_JSON"])
        if p.exists():
            return p

    if RUTA_JSON is not None and Path(RUTA_JSON).exists():
        return Path(RUTA_JSON)

    rutas_candidatas = [
        Path(r"C:\Users\BCP\Desktop\TFM\caso2_plataformas\resultados"),
        Path(r"C:\Users\BCP\Desktop\TFM\caso2_plataformas\cuantico\resultados"),
        Path(r"C:\Users\BCP\Desktop\TFM\caso2_plataformas\visualizacion"),
    ]

    archivos = []
    for carpeta in rutas_candidatas:
        if carpeta.exists():
            archivos.extend(list(carpeta.glob("caso2_nivel_blender_*.json")))

    if not archivos:
        raise FileNotFoundError(
            "No se encontró 'caso2_nivel_blender_*.json'. "
            "Ejecuta primero 'exportar_nivel_blender_v4.py'."
        )

    # Preferir v4 si existe, sino el más reciente
    v4_files = [a for a in archivos if "v4" in a.name.lower()]
    if v4_files:
        v4_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return v4_files[0]

    archivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return archivos[0]


# =============================================================================
# UTILIDADES DE ESCENA
# =============================================================================

def limpiar_escena():
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for db in list(datablocks):
            if db.users == 0:
                datablocks.remove(db)


def obtener_o_crear_coleccion(nombre, padre=None):
    if nombre in bpy.data.collections:
        return bpy.data.collections[nombre]
    col = bpy.data.collections.new(nombre)
    if padre is None:
        bpy.context.scene.collection.children.link(col)
    else:
        padre.children.link(col)
    return col


def mover_a_coleccion(obj, coleccion_destino):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    if obj.name not in coleccion_destino.objects:
        coleccion_destino.objects.link(obj)


# =============================================================================
# MATERIALES PBR PROCEDURALES
# =============================================================================

def crear_material_top_plataforma():
    """Losa superior con relieve de cantería y borde con matiz de musgo."""
    nombre = "Mat_Plataforma_Top"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (0.22, 0.38, 0.28, 1.0)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.70
    bsdf.inputs["Metallic"].default_value = 0.05

    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 6.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.16, 0.26, 0.18, 1.0)  # Tono musgo
    ramp.color_ramp.elements[1].position = 0.80
    ramp.color_ramp.elements[1].color = (0.35, 0.42, 0.38, 1.0)  # Piedra pizarra

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.30
    bump.inputs["Distance"].default_value = 0.10

    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def crear_material_roca_plataforma():
    """Estrato rocoso escarpado oscuro para el cuerpo inferior de las plataformas."""
    nombre = "Mat_Plataforma_Roca"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (0.14, 0.15, 0.18, 1.0)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.08

    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 8.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (0.07, 0.08, 0.10, 1.0)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.22, 0.23, 0.26, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    bump.inputs["Distance"].default_value = 0.15

    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def crear_material_pbr_simple(nombre, color_rgba, metallic=0.0, roughness=0.5,
                              emision=None, emision_fuerza=1.0):
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = color_rgba

    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color_rgba
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if emision is not None:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = emision
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = emision_fuerza
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = emision
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = emision_fuerza
    return mat


def crear_material_lava_procedural():
    """Lava volcánica procedural: costra de basalto oscuro con grietas de magma ardiente."""
    nombre = "Mat_Abismo_Lava_Procedural"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (0.2, 0.05, 0.02, 1.0)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Metallic"].default_value = 0.1

    coord = nodes.new("ShaderNodeTexCoord")
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = 1.8
    voronoi.feature = "DISTANCE_TO_EDGE"

    ramp = nodes.new("ShaderNodeValToRGB")
    # Zonas de grietas (0.0 a 0.15): magma ardiente. Zonas amplias: roca de basalto negro.
    ramp.color_ramp.elements[0].position = 0.04
    ramp.color_ramp.elements[0].color = (1.0, 0.35, 0.03, 1.0)
    ramp.color_ramp.elements[1].position = 0.22
    ramp.color_ramp.elements[1].color = (0.04, 0.03, 0.04, 1.0)

    links.new(coord.outputs["Object"], voronoi.inputs["Vector"])
    links.new(voronoi.outputs["Distance"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    if "Emission Color" in bsdf.inputs:
        links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 4.0
    elif "Emission" in bsdf.inputs:
        links.new(ramp.outputs["Color"], bsdf.inputs["Emission"])
        bsdf.inputs["Emission Strength"].default_value = 4.0

    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def inicializar_materiales_caso2():
    return {
        "top": crear_material_top_plataforma(),
        "roca": crear_material_roca_plataforma(),
        "bracket": crear_material_pbr_simple("Mat_Bracket_Bronce", (0.28, 0.22, 0.14, 1.0), metallic=0.8, roughness=0.35),
        "madera_poste": crear_material_pbr_simple("Mat_Poste_Madera", (0.25, 0.14, 0.08, 1.0), roughness=0.8),
        "ascuas": crear_material_pbr_simple(
            "Mat_Ascuas_Emisivo",
            (1.0, 0.35, 0.02, 1.0),
            emision=(1.0, 0.40, 0.05, 1.0),
            emision_fuerza=14.0,
        ),
        "cristal_goal": crear_material_pbr_simple(
            "Mat_Cristal_Goal_Oro",
            (1.0, 0.85, 0.15, 1.0),
            metallic=0.2,
            roughness=0.15,
            emision=(1.0, 0.85, 0.15, 1.0),
            emision_fuerza=9.0,
        ),
        "portal_arco": crear_material_pbr_simple("Mat_Arco_Goal", (0.45, 0.40, 0.30, 1.0), metallic=0.4, roughness=0.3),
        "salto_neon": crear_material_pbr_simple(
            "Mat_Arco_Salto_Neon",
            (0.05, 0.90, 1.0, 1.0),
            emision=(0.05, 0.92, 1.0, 1.0),
            emision_fuerza=9.0,
        ),
        "impacto_target": crear_material_pbr_simple(
            "Mat_Impacto_Target",
            (1.0, 0.70, 0.10, 1.0),
            emision=(1.0, 0.70, 0.10, 1.0),
            emision_fuerza=6.0,
        ),
        "lava": crear_material_lava_procedural(),
        "fondo_silueta": crear_material_pbr_simple("Mat_Fondo_Silueta", (0.025, 0.03, 0.045, 1.0), roughness=0.9),
    }


# =============================================================================
# MODELADO PROCEDURAL DE PLATAFORMAS 2.5D
# =============================================================================

def crear_plataforma_25d(x, y, ancho_tiles, col_plataformas, mats, nombre):
    """Crea una plataforma 2.5D multicapa con losa superior, cuerpo rocoso y ménsulas."""
    ancho = ancho_tiles * TILE_SIZE
    centro_x = x * TILE_SIZE + ancho / 2.0
    centro_z = y * TILE_SIZE

    # 1. Superficie superior de tránsito
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(centro_x, 0.0, centro_z),
    )
    top = bpy.context.object
    top.name = f"{nombre}_Top"
    top.scale = (ancho, PROFUNDIDAD_TOP, GROSOR_TOP)
    bpy.ops.object.transform_apply(scale=True)
    top.data.materials.append(mats["top"])

    bev_top = top.modifiers.new("Bisel", type="BEVEL")
    bev_top.width = 0.06
    bev_top.segments = 2
    mover_a_coleccion(top, col_plataformas)

    # 2. Base / Estrato rocoso inferior
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(centro_x, 0.0, centro_z - (GROSOR_TOP + GROSOR_ROCA) / 2.0),
    )
    roca = bpy.context.object
    roca.name = f"{nombre}_Roca"
    roca.scale = (ancho - 0.25, PROFUNDIDAD_ROCA, GROSOR_ROCA)
    bpy.ops.object.transform_apply(scale=True)
    roca.data.materials.append(mats["roca"])

    bev_roca = roca.modifiers.new("Bisel", type="BEVEL")
    bev_roca.width = 0.12
    bev_roca.segments = 3
    mover_a_coleccion(roca, col_plataformas)

    # 3. Ménsulas / Contrafuertes en los extremos (apoyo estructural)
    for lado, dx in ((-1, -ancho / 2.0 + 0.35), (1, ancho / 2.0 - 0.35)):
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(centro_x + dx, 0.0, centro_z - GROSOR_TOP - 0.30),
        )
        mensula = bpy.context.object
        mensula.name = f"{nombre}_Mensula_{'I' if lado == -1 else 'D'}"
        mensula.scale = (0.28, PROFUNDIDAD_ROCA + 0.1, 0.45)
        mensula.rotation_euler = (0.0, math.radians(lado * 25.0), 0.0)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        mensula.data.materials.append(mats["bracket"])
        mover_a_coleccion(mensula, col_plataformas)

    return top


# =============================================================================
# CHECKPOINTS START Y GOAL
# =============================================================================

def crear_checkpoint_start(pos, ancho_tiles, col_gameplay, mats):
    """Campamento de inicio con fogata de ascuas ardientes, poste y farol."""
    ancho_m = ancho_tiles * TILE_SIZE
    cx = pos["x"] * TILE_SIZE + ancho_m / 2.0
    cz = pos["y"] * TILE_SIZE + GROSOR_TOP / 2.0

    # Hoguera de piedras en el centro de la plataforma de inicio
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.45,
        minor_radius=0.10,
        location=(cx + 0.35, 0.0, cz + 0.08),
    )
    hoguera = bpy.context.object
    hoguera.name = "Start_Hoguera_Piedras"
    hoguera.data.materials.append(mats["roca"])
    mover_a_coleccion(hoguera, col_gameplay)

    # Ascuas incandescentes
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2,
        radius=0.22,
        location=(cx + 0.35, 0.0, cz + 0.14),
    )
    ascuas = bpy.context.object
    ascuas.name = "Start_Ascuas_Fuego"
    ascuas.data.materials.append(mats["ascuas"])
    mover_a_coleccion(ascuas, col_gameplay)

    # Poste indicador de madera a la izquierda
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.08,
        depth=1.60,
        location=(cx - 0.65, 0.0, cz + 0.80),
    )
    poste = bpy.context.object
    poste.name = "Start_Poste_Madera"
    poste.data.materials.append(mats["madera_poste"])
    mover_a_coleccion(poste, col_gameplay)

    # Tablilla con dirección a la meta
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(cx - 0.50, 0.0, cz + 1.40),
    )
    flecha = bpy.context.object
    flecha.name = "Start_Flecha_Indicador"
    flecha.scale = (0.45, 0.06, 0.20)
    flecha.rotation_euler = (0.0, 0.0, math.radians(-10.0))
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    flecha.data.materials.append(mats["madera_poste"])
    mover_a_coleccion(flecha, col_gameplay)

    # Luz cálida del campamento
    luz_data = bpy.data.lights.new(name="Luz_Start_Fogata", type="POINT")
    luz_data.color = (1.0, 0.50, 0.10)
    luz_data.energy = 60.0
    luz_data.shadow_soft_size = 0.4
    luz_obj = bpy.data.objects.new("Luz_Start_Fogata", luz_data)
    luz_obj.location = (cx + 0.35, 0.0, cz + 0.60)
    col_gameplay.objects.link(luz_obj)


def crear_checkpoint_goal(pos, ancho_tiles, col_gameplay, mats):
    """Santuario de victoria: Portal de arquería rúnica dorada con cristal celestial flotante."""
    ancho_m = ancho_tiles * TILE_SIZE
    cx = pos["x"] * TILE_SIZE + ancho_m / 2.0
    cz = pos["y"] * TILE_SIZE + GROSOR_TOP / 2.0

    # Pedestal de cantería
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
        radius=0.75,
        depth=0.25,
        location=(cx, 0.0, cz + 0.12),
    )
    pedestal = bpy.context.object
    pedestal.name = "Goal_Pedestal"
    pedestal.data.materials.append(mats["portal_arco"])
    mover_a_coleccion(pedestal, col_gameplay)

    # Columnas del arco
    for lado, dx in ((-1, -0.65), (1, 0.65)):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=12,
            radius=0.12,
            depth=2.20,
            location=(cx + dx, 0.0, cz + 1.20),
        )
        columna = bpy.context.object
        columna.name = f"Goal_Columna_{'I' if lado == -1 else 'D'}"
        columna.data.materials.append(mats["portal_arco"])
        mover_a_coleccion(columna, col_gameplay)

    # Dintel superior del arco
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(cx, 0.0, cz + 2.30),
    )
    dintel = bpy.context.object
    dintel.name = "Goal_Dintel"
    dintel.scale = (1.60, 0.35, 0.28)
    bpy.ops.object.transform_apply(scale=True)
    dintel.data.materials.append(mats["portal_arco"])
    mover_a_coleccion(dintel, col_gameplay)

    # Cristal dorado flotante (octaedro rotando)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=4,
        radius=0.35,
        depth=0.70,
        location=(cx, 0.0, cz + 1.30),
    )
    cristal = bpy.context.object
    cristal.name = "Goal_Cristal_Celestial"
    cristal.rotation_euler = (math.radians(45.0), math.radians(25.0), math.radians(35.0))
    cristal.data.materials.append(mats["cristal_goal"])
    mover_a_coleccion(cristal, col_gameplay)

    # Luz dorada de la victoria
    luz_data = bpy.data.lights.new(name="Luz_Goal_Victory", type="POINT")
    luz_data.color = (1.0, 0.85, 0.20)
    luz_data.energy = 75.0
    luz_data.shadow_soft_size = 0.5
    luz_obj = bpy.data.objects.new("Luz_Goal_Victory", luz_data)
    luz_obj.location = (cx, 0.0, cz + 1.50)
    col_gameplay.objects.link(luz_obj)


# =============================================================================
# ARCOS PARABÓLICOS DE SALTO (FÍSICA REAL DEL PLATAFORMAS)
# =============================================================================

def crear_arcos_salto_parabolicos(ruta, ancho_tiles, start, goal, col_rutas, mats):
    """Genera trayectorias parabólicas de salto entre plataformas consecutivas."""
    curva_data = bpy.data.curves.new(name="Arcos_Salto_Parabolicos", type="CURVE")
    curva_data.dimensions = "3D"
    curva_data.bevel_depth = 0.09
    curva_data.bevel_resolution = 4
    curva_data.use_fill_caps = True

    ancho_m = ancho_tiles * TILE_SIZE

    for idx in range(len(ruta) - 1):
        origen = ruta[idx]
        destino = ruta[idx + 1]

        # Punto de despegue (extremo derecho de la plataforma de origen)
        if origen["x"] == start["x"] and origen["y"] == start["y"]:
            x0 = origen["x"] * TILE_SIZE + TILE_SIZE * 0.8
        else:
            x0 = origen["x"] * TILE_SIZE + ancho_m - 0.2
        z0 = origen["y"] * TILE_SIZE + GROSOR_TOP / 2.0 + 0.15

        # Punto de aterrizaje (borde izquierdo / centro de la plataforma de destino)
        if destino["x"] == goal["x"] and destino["y"] == goal["y"]:
            x1 = destino["x"] * TILE_SIZE + TILE_SIZE * 0.3
        else:
            x1 = destino["x"] * TILE_SIZE + 0.4
        z1 = destino["y"] * TILE_SIZE + GROSOR_TOP / 2.0 + 0.15

        delta_x = x1 - x0
        delta_z = z1 - z0

        apex_h = max(1.4, 0.9 + 0.7 * max(0.0, delta_z))

        spline = curva_data.splines.new(type="POLY")
        num_pasos = 22
        spline.points.add(num_pasos)

        for s in range(num_pasos + 1):
            t = s / float(num_pasos)
            px = x0 + delta_x * t
            pz = z0 + delta_z * t + 4.0 * apex_h * t * (1.0 - t)
            spline.points[s].co = (px, 0.0, pz, 1.0)

        # Marcador circular de aterrizaje en la plataforma de destino
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.40,
            minor_radius=0.04,
            location=(x1, 0.0, z1 - 0.10),
        )
        target = bpy.context.object
        target.name = f"Target_Salto_{idx+1}"
        target.data.materials.append(mats["impacto_target"])
        mover_a_coleccion(target, col_rutas)

    obj_curva = bpy.data.objects.new("Trayectorias_Salto", curva_data)
    obj_curva.data.materials.append(mats["salto_neon"])
    col_rutas.objects.link(obj_curva)


# =============================================================================
# ENTORNO: ABISMO DE LAVA Y PARALLAX DE FONDO
# =============================================================================

def crear_abismo_peligro(ancho_mapa, col_entorno, mats):
    """Crea una sima de lava incandescente en el fondo que justifica el riesgo de saltar."""
    ancho_total = (ancho_mapa + 24) * TILE_SIZE
    profundidad_y = 35.0

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(ancho_mapa * TILE_SIZE / 2.0, 5.0, -11.0),
    )
    lava = bpy.context.object
    lava.name = "Abismo_Lava_Peligro"
    lava.scale = (ancho_total, profundidad_y, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    lava.data.materials.append(mats["lava"])
    mover_a_coleccion(lava, col_entorno)

    # Luz de resplandor ascendente de lava suave y cálida
    luz_data = bpy.data.lights.new(name="Luz_Resplandor_Lava", type="AREA")
    luz_data.color = (1.0, 0.35, 0.06)
    luz_data.energy = 600.0
    luz_data.size = ancho_total * 0.7
    luz_data.size_y = 14.0
    luz_obj = bpy.data.objects.new("Luz_Resplandor_Lava", luz_data)
    luz_obj.location = (ancho_mapa * TILE_SIZE / 2.0, 0.0, -9.5)
    luz_obj.rotation_euler = (math.radians(-180.0), 0.0, 0.0)
    col_entorno.objects.link(luz_obj)


def crear_fondo_parallax(ancho_mapa, alto_mapa, col_entorno, mats):
    """Crea siluetas lejanas de columnas de caverna para profundidad 2.5D."""
    dist_fondo = 40.0

    num_columnas = int(ancho_mapa / 4) + 3
    for i in range(num_columnas):
        cx = (i - 1) * 4.0 * TILE_SIZE
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=8,
            radius=2.4,
            depth=alto_mapa * TILE_SIZE * 3.5,
            location=(cx, dist_fondo, (alto_mapa * TILE_SIZE) / 2.0),
        )
        columna = bpy.context.object
        columna.name = f"Columna_Fondo_{i}"
        columna.data.materials.append(mats["fondo_silueta"])
        mover_a_coleccion(columna, col_entorno)


# =============================================================================
# CÁMARA E ILUMINACIÓN CINEMATOGRÁFICA 2.5D
# =============================================================================

def configurar_camara_e_iluminacion(ancho_mapa, alto_mapa, col_raiz):
    col_setup = obtener_o_crear_coleccion("00_Setup_Camara_Luces", col_raiz)

    centro_x = (ancho_mapa + 2.0) * TILE_SIZE / 2.0
    centro_z = alto_mapa * TILE_SIZE / 2.0 + 0.5

    # 1. Luces de Estudio
    key_data = bpy.data.lights.new(name="Luz_Key_Plataformas", type="AREA")
    key_data.energy = 2800.0
    key_data.color = (1.0, 0.96, 0.90)
    key_data.shape = "RECTANGLE"
    key_data.size = (ancho_mapa + 10) * TILE_SIZE
    key_data.size_y = 22.0
    key_obj = bpy.data.objects.new("Luz_Key_Plataformas", key_data)
    key_obj.location = (centro_x, -30.0, centro_z + 24.0)
    key_obj.rotation_euler = (math.radians(48.0), 0.0, 0.0)
    col_setup.objects.link(key_obj)

    fill_data = bpy.data.lights.new(name="Luz_Fill_Cielo", type="SUN")
    fill_data.energy = 2.2
    fill_data.color = (0.65, 0.80, 1.0)
    fill_obj = bpy.data.objects.new("Luz_Fill_Cielo", fill_data)
    fill_obj.location = (centro_x, 20.0, centro_z + 25.0)
    fill_obj.rotation_euler = (math.radians(45.0), math.radians(-15.0), math.radians(170.0))
    col_setup.objects.link(fill_obj)

    # 2. Cámara 2.5D Isométrica con Perspectiva y amplio margen horizontal
    target = bpy.data.objects.new("Camara_Target", None)
    target.location = (centro_x, 0.0, centro_z)
    col_setup.objects.link(target)

    cam_data = bpy.data.cameras.new(name="Camara_25D_Plataformas")
    cam_data.type = "PERSP"
    cam_data.lens = 32.0

    # Distancia generosa para asegurar que Start (x=0) y Goal (x=ancho) tengan márgenes impecables
    ancho_mundo = (ancho_mapa + 4.0) * TILE_SIZE
    dist_y = ancho_mundo * 0.88

    # Altura rasante 2.5D: solo 2.2m por encima del centro para vista directa a los props
    cam_obj = bpy.data.objects.new("Camara_Nivel", cam_data)
    cam_obj.location = (centro_x, -dist_y, centro_z + 2.2)
    col_setup.objects.link(cam_obj)

    track = cam_obj.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    bpy.context.scene.camera = cam_obj

    # 3. Fondo atmosférico de caverna
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("World_Cavern")
    world = bpy.context.scene.world
    if hasattr(world, "node_tree") and world.node_tree:
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg is not None:
            bg.inputs["Color"].default_value = (0.015, 0.018, 0.025, 1.0)
            bg.inputs["Strength"].default_value = 0.55

    # 4. Motor de Render
    for engine in ("CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            bpy.context.scene.render.engine = engine
            break
        except Exception:
            pass

    if bpy.context.scene.render.engine == "CYCLES":
        bpy.context.scene.cycles.samples = 64
        bpy.context.scene.cycles.adaptive_threshold = 0.05

    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 900
    bpy.context.scene.render.resolution_percentage = 100

    # 5. Modo Material en Viewport
    if ACTIVAR_VISTA_MATERIAL and hasattr(bpy.context, "window_manager"):
        for window in bpy.context.window_manager.windows:
            if hasattr(window, "screen") and window.screen:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                space.shading.type = 'MATERIAL'
                                space.shading.color_type = 'MATERIAL'
                                if hasattr(space.shading, 'show_shadows'):
                                    space.shading.show_shadows = True


# =============================================================================
# CONSTRUCCIÓN PRINCIPAL
# =============================================================================

def construir_escena_caso2():
    json_path = obtener_ruta_json()
    print(f"Cargando nivel de Caso 2 desde: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ancho_mapa = data["escenario"]["ancho"]
    alto_mapa = data["escenario"]["alto"]
    ancho_plataforma = data["ancho_plataforma"]

    start = data["start"]
    goal = data["goal"]
    plataformas = data["plataformas"]
    ruta = data["ruta"]

    print(f"Generando nivel 2.5D ({ancho_mapa}x{alto_mapa}) con {len(plataformas)} plataformas...")

    limpiar_escena()
    mats = inicializar_materiales_caso2()

    col_raiz = obtener_o_crear_coleccion("Caso2_Plataformas_25D")
    col_plataformas = obtener_o_crear_coleccion("01_Plataformas_Multicapa", col_raiz)
    col_gameplay = obtener_o_crear_coleccion("02_Checkpoints", col_raiz)
    col_rutas = obtener_o_crear_coleccion("03_Arcos_Salto", col_raiz)
    col_entorno = obtener_o_crear_coleccion("04_Entorno_Abismo", col_raiz)

    # 1. Plataformas multicapa intermedias
    for i, p in enumerate(plataformas, start=1):
        crear_plataforma_25d(
            p["x"],
            p["y"],
            ancho_plataforma,
            col_plataformas,
            mats,
            f"Plataforma_{i:02d}",
        )

    # Plataformas de inicio (START) y fin (GOAL)
    crear_plataforma_25d(
        start["x"],
        start["y"],
        ancho_plataforma,
        col_plataformas,
        mats,
        "Plataforma_START",
    )
    crear_plataforma_25d(
        goal["x"],
        goal["y"],
        ancho_plataforma,
        col_plataformas,
        mats,
        "Plataforma_GOAL",
    )

    # 2. Checkpoints Start y Goal situados sobre sus plataformas
    crear_checkpoint_start(start, ancho_plataforma, col_gameplay, mats)
    crear_checkpoint_goal(goal, ancho_plataforma, col_gameplay, mats)

    # 3. Arcos parabólicos de salto
    if MOSTRAR_ARCOS_SALTO:
        crear_arcos_salto_parabolicos(
            ruta,
            ancho_plataforma,
            start,
            goal,
            col_rutas,
            mats,
        )

    # 4. Abismo de lava y fondo parallax
    if MOSTRAR_ABISMO_LAVA:
        crear_abismo_peligro(ancho_mapa, col_entorno, mats)

    if MOSTRAR_FONDO_PARALLAX:
        crear_fondo_parallax(ancho_mapa, alto_mapa, col_entorno, mats)

    # 5. Cámara e Iluminación 2.5D
    configurar_camara_e_iluminacion(ancho_mapa, alto_mapa, col_raiz)

    print("=" * 68)
    print("NIVEL 2.5D CASO 2 GENERADO CON ÉXITO")
    print(f"• Plataformas multicapa generadas: {len(plataformas)}")
    print(f"• Arcos parabólicos de salto: {len(ruta) - 1}")
    print("• Campamento de inicio y santuario de meta colocados")
    print("• Sima de lava y fondo parallax configurados")
    print("=" * 68)

    # Si se ejecuta en segundo plano (-b), guardar .blend y renderizar imagen
    if bpy.app.background:
        json_name = Path(json_path).stem.lower()
        if "qubo" in json_name:
            stem = "caso2_nivel_blender_qubo_18x5"
            img_stem = "caso2_blender_qubo_render_18x5.png"
        else:
            stem = "caso2_nivel_blender_v4_40x10"
            img_stem = "caso2_blender_v4_render_40x10.png"

        res_dir = Path(r"C:\Users\BCP\Desktop\TFM\caso2_plataformas\resultados")
        fig_dir = Path(r"C:\Users\BCP\Desktop\TFM\caso2_plataformas\figuras")
        res_dir.mkdir(parents=True, exist_ok=True)
        fig_dir.mkdir(parents=True, exist_ok=True)

        blend_output = res_dir / f"{stem}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_output))
        print(f"Escena .blend guardada en: {blend_output}")

        img_output = fig_dir / img_stem
        bpy.context.scene.render.filepath = str(img_output)
        bpy.ops.render.render(write_still=True)
        print(f"Render 3D guardado en: {img_output}")


if __name__ == "__main__" and bpy is not None:
    construir_escena_caso2()