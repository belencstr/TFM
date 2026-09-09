r"""Visualización 3D Avanzada en Blender — Caso 1: Colocación de Monedas (k-center).

Transforma la salida combinatoria de k-center en un diorama 3D fotorrealista para el TFM:
- DIORAMA COMPLETO: Zócalo de cantería subterránea que sostiene el nivel.
- TEXTURAS PROCEDURALES: Losas de suelo con bisel y relieve, muros de piedra antigua con sillares.
- MONEDAS DE ORO 3D: Monedas esculpidas con relieve perimetral, emblema central de estrella,
  material de oro reflectante PBR (Metallic 0.95), levitación dinámica y resplandor luminoso.
- VISUALIZACIÓN ALGORÍTMICA DE COBERTURA: Halos rúnicos circulares en el suelo que ilustran
  el radio de influencia de cada centro k-center.
- CHECKPOINTS: Pedestal rúnico de inicio (Start) y portal dimensional de fin (Goal).
- ANTORCHAS DE PARED: Apliques de hierro forjado con fuego y luces cálidas en esquinas.
- ILUMINACIÓN CINEMATOGRÁFICA: Configuración 3-point de estudio con cámara isométrica 3/4.

EJECUCIÓN INTERACTIVA:
1. Abre Blender 5.x (o 4.x/3.x) -> pestaña Scripting.
2. Abre este archivo y pulsa "Run Script" (▶).
3. Se activa automáticamente el modo Material Preview a todo color.

EJECUCIÓN DESDE CONSOLA / AUTOMÁTICA:
  blender -b -P caso1_colocacion_monedas/visualizacion/visualizar_caso1_blender.py
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


# =============================================================================
# CONFIGURACIÓN Y DIMENSIONES
# =============================================================================

RUTA_JSON = None             # None -> auto-descubre el JSON de Caso 1 más reciente

TILE_SIZE = 2.0              # Metros por casilla
ALTURA_SUELO = 0.20          # Grosor losa
GAP_SUELO = 0.08             # Separación entre losas
ALTURA_MURO = 2.30           # Altura de los muros
BISEL_MURO = 0.10            # Bisel de los bloques

MOSTRAR_HALOS_COBERTURA = True
MOSTRAR_ANTORCHAS = True
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

    if os.environ.get("CASO1_BLENDER_JSON"):
        p = Path(os.environ["CASO1_BLENDER_JSON"])
        if p.exists():
            return p

    if RUTA_JSON is not None and Path(RUTA_JSON).exists():
        return Path(RUTA_JSON)

    script_dir = Path(__file__).resolve().parent
    base_caso1 = script_dir.parent
    rutas_candidatas = [
        base_caso1 / "resultados",
        script_dir,
    ]

    archivos = []
    for carpeta in rutas_candidatas:
        if carpeta.exists():
            archivos.extend(list(carpeta.glob("caso1_nivel_blender_*.json")))

    if not archivos:
        raise FileNotFoundError(
            "No se encontró 'caso1_nivel_blender_*.json'. "
            "Ejecuta primero 'exportar_nivel_blender_caso1.py'."
        )

    # Preferir el de mapa B si existe, o el más reciente
    mapa_b = [a for a in archivos if "mapa_b" in a.name.lower()]
    if mapa_b:
        mapa_b.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return mapa_b[0]

    archivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return archivos[0]


# =============================================================================
# GESTIÓN DE ESCENA
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

def crear_material_muro():
    nombre = "Mat_Muro_Granito"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (0.16, 0.17, 0.19, 1.0)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.05

    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 7.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.2
    ramp.color_ramp.elements[0].color = (0.08, 0.09, 0.11, 1.0)
    ramp.color_ramp.elements[1].position = 0.8
    ramp.color_ramp.elements[1].color = (0.22, 0.24, 0.27, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.12

    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def crear_material_suelo():
    nombre = "Mat_Suelo_Canteria"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (0.28, 0.30, 0.33, 1.0)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.65
    bsdf.inputs["Metallic"].default_value = 0.08

    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 6.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (0.16, 0.17, 0.20, 1.0)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.34, 0.36, 0.40, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.08

    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def crear_material_oro_pbr():
    """Oro pulido con brillo reflectante de alta calidad."""
    nombre = "Mat_Oro_Coleccionable"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (1.0, 0.78, 0.12, 1.0)

    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (1.0, 0.78, 0.12, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.96
        bsdf.inputs["Roughness"].default_value = 0.18
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.82, 0.20, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.2
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


def inicializar_materiales_caso1():
    return {
        "muro": crear_material_muro(),
        "suelo": crear_material_suelo(),
        "oro": crear_material_oro_pbr(),
        "plinth": crear_material_pbr_simple("Mat_Diorama_Plinth", (0.05, 0.05, 0.06, 1.0), roughness=0.8),
        "halo": crear_material_pbr_simple(
            "Mat_Halo_Cobertura",
            (1.0, 0.80, 0.15, 0.5),
            emision=(1.0, 0.80, 0.15, 1.0),
            emision_fuerza=4.0,
            roughness=0.2,
        ),
        "portal_start": crear_material_pbr_simple(
            "Mat_Start_Esmeralda",
            (0.0, 0.95, 0.55, 1.0),
            emision=(0.0, 0.95, 0.55, 1.0),
            emision_fuerza=7.0,
        ),
        "portal_goal": crear_material_pbr_simple(
            "Mat_Goal_Zafiro",
            (0.1, 0.65, 1.0, 1.0),
            emision=(0.1, 0.65, 1.0, 1.0),
            emision_fuerza=7.0,
        ),
        "hierro_antorcha": crear_material_pbr_simple("Mat_Hierro_Antorcha", (0.08, 0.08, 0.09, 1.0), metallic=0.8, roughness=0.4),
        "fuego_antorcha": crear_material_pbr_simple(
            "Mat_Fuego_Antorcha",
            (1.0, 0.45, 0.05, 1.0),
            emision=(1.0, 0.50, 0.08, 1.0),
            emision_fuerza=12.0,
        ),
    }


# =============================================================================
# COORDENADAS
# =============================================================================

def coord_a_blender(row, col, rows, cols, z=0.0):
    x = (col - (cols - 1) / 2.0) * TILE_SIZE
    y = ((rows - 1) / 2.0 - row) * TILE_SIZE
    return Vector((x, y, z))


# =============================================================================
# MODELADO PROCEDURAL DEL DIORAMA
# =============================================================================

def crear_plinth_diorama(rows, cols, col_entorno, mat_plinth):
    """Zócalo de piedra subterránea sólida bajo el diorama para eliminar el vacío plano."""
    ancho_x = cols * TILE_SIZE + 0.8
    ancho_y = rows * TILE_SIZE + 0.8
    profundidad_z = 1.4

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, 0.0, -profundidad_z / 2.0 - ALTURA_SUELO),
    )
    base = bpy.context.object
    base.name = "Diorama_Plinth"
    base.scale = (ancho_x, ancho_y, profundidad_z)
    bpy.ops.object.transform_apply(scale=True)
    base.data.materials.append(mat_plinth)

    bevel = base.modifiers.new("Bisel", type="BEVEL")
    bevel.width = 0.20
    bevel.segments = 3
    mover_a_coleccion(base, col_entorno)


def crear_losa_suelo(pos, col_entorno, mat_suelo):
    ancho = TILE_SIZE - GAP_SUELO
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(pos.x, pos.y, -ALTURA_SUELO / 2.0),
    )
    losa = bpy.context.object
    losa.scale = (ancho, ancho, ALTURA_SUELO)
    bpy.ops.object.transform_apply(scale=True)
    losa.data.materials.append(mat_suelo)

    bevel = losa.modifiers.new("Bisel", type="BEVEL")
    bevel.width = 0.04
    bevel.segments = 2
    mover_a_coleccion(losa, col_entorno)


def crear_bloque_muro(pos, col_entorno, mat_muro, es_borde=False):
    ancho = TILE_SIZE - GAP_SUELO * 0.4
    altura = ALTURA_MURO + (0.35 if es_borde else 0.0)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(pos.x, pos.y, altura / 2.0),
    )
    muro = bpy.context.object
    muro.scale = (ancho, ancho, altura)
    bpy.ops.object.transform_apply(scale=True)
    muro.data.materials.append(mat_muro)

    bevel = muro.modifiers.new("Bisel", type="BEVEL")
    bevel.width = BISEL_MURO
    bevel.segments = 3
    mover_a_coleccion(muro, col_entorno)


# =============================================================================
# MODELADO DE MONEDAS Y VISUALIZACIÓN ALGORÍTMICA
# =============================================================================

def crear_moneda_oro_3d(pos, col_monedas, mats, radio_cobertura_local=7.0):
    """Crea una moneda coleccionable dorada estilizada con relieve y aura de cobertura."""
    altura_flotacion = 1.05

    # 1. Cuerpo de la moneda (Cilindro biselado más grande para visibilidad en mapa 17x17)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=0.68,
        depth=0.15,
        location=(pos.x, pos.y, altura_flotacion),
    )
    moneda = bpy.context.object
    moneda.name = "Moneda_Oro_Cuerpo"
    moneda.rotation_euler = (math.radians(30.0), math.radians(25.0), math.radians(20.0))
    moneda.data.materials.append(mats["oro"])
    mover_a_coleccion(moneda, col_monedas)

    # 2. Relieve exterior (Torus en el reborde grueso)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.62,
        minor_radius=0.065,
        location=(pos.x, pos.y, altura_flotacion),
    )
    borde = bpy.context.object
    borde.rotation_euler = moneda.rotation_euler
    borde.data.materials.append(mats["oro"])
    mover_a_coleccion(borde, col_monedas)

    # 3. Emblema central de estrella / diamante en relieve
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=4,
        radius=0.35,
        depth=0.22,
        location=(pos.x, pos.y, altura_flotacion),
    )
    emblema = bpy.context.object
    emblema.rotation_euler = moneda.rotation_euler
    emblema.data.materials.append(mats["oro"])
    mover_a_coleccion(emblema, col_monedas)

    # 4. Halo / Anillo de Cobertura Algorítmica en el suelo (k-center)
    if MOSTRAR_HALOS_COBERTURA:
        # Anillo interior brillante
        bpy.ops.mesh.primitive_torus_add(
            major_radius=TILE_SIZE * 0.55,
            minor_radius=0.05,
            location=(pos.x, pos.y, 0.03),
        )
        halo_base = bpy.context.object
        halo_base.name = "Halo_Base_Moneda"
        halo_base.data.materials.append(mats["halo"])
        mover_a_coleccion(halo_base, col_monedas)

        # Anillo exterior de radio de cobertura (onda rúnica)
        bpy.ops.mesh.primitive_torus_add(
            major_radius=TILE_SIZE * 1.10,
            minor_radius=0.035,
            location=(pos.x, pos.y, 0.03),
        )
        halo_ext = bpy.context.object
        halo_ext.name = "Halo_Ext_Moneda"
        halo_ext.data.materials.append(mats["halo"])
        mover_a_coleccion(halo_ext, col_monedas)

    # 5. Luz cálida puntual dorada emitida por la moneda
    luz_data = bpy.data.lights.new(name="Luz_Moneda", type="POINT")
    luz_data.color = (1.0, 0.85, 0.25)
    luz_data.energy = 55.0
    luz_data.shadow_soft_size = 0.45
    luz_obj = bpy.data.objects.new("Luz_Moneda", luz_data)
    luz_obj.location = (pos.x, pos.y, altura_flotacion + 0.35)
    col_monedas.objects.link(luz_obj)


def crear_portal_spawn_exit(pos, col_gameplay, mat_portal, mat_base, es_start=True):
    """Crea un pedestal rúnico para Start y Exit."""
    # Pedestal octogonal
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
        radius=TILE_SIZE * 0.42,
        depth=0.18,
        location=(pos.x, pos.y, 0.09),
    )
    pedestal = bpy.context.object
    pedestal.data.materials.append(mat_base)
    mover_a_coleccion(pedestal, col_gameplay)

    # Anillo rúnico emisivo
    bpy.ops.mesh.primitive_torus_add(
        major_radius=TILE_SIZE * 0.32,
        minor_radius=0.045,
        location=(pos.x, pos.y, 0.20),
    )
    anillo = bpy.context.object
    anillo.data.materials.append(mat_portal)
    mover_a_coleccion(anillo, col_gameplay)

    # Cristal flotante
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=6,
        radius=0.18,
        depth=0.60,
        location=(pos.x, pos.y, 0.65),
    )
    cristal = bpy.context.object
    cristal.rotation_euler = (math.radians(15.0), math.radians(20.0), 0.0)
    cristal.data.materials.append(mat_portal)
    mover_a_coleccion(cristal, col_gameplay)

    # Luz puntual de invocación
    luz_data = bpy.data.lights.new(name="Luz_Portal", type="POINT")
    luz_data.color = (0.0, 0.95, 0.55) if es_start else (0.1, 0.70, 1.0)
    luz_data.energy = 40.0
    luz_data.shadow_soft_size = 0.4
    luz_obj = bpy.data.objects.new("Luz_Portal", luz_data)
    luz_obj.location = (pos.x, pos.y, 0.9)
    col_gameplay.objects.link(luz_obj)


def crear_antorcha_pared(pos_muro, direccion_offset, col_entorno, mats):
    """Crea un aplique de antorcha medieval en un muro con fuego y luz cálida."""
    pos_antorcha = pos_muro + direccion_offset * (TILE_SIZE * 0.42) + Vector((0.0, 0.0, 1.4))

    # Soporte de hierro
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
        radius=0.04,
        depth=0.35,
        location=(pos_antorcha.x, pos_antorcha.y, pos_antorcha.z - 0.12),
    )
    soporte = bpy.context.object
    soporte.rotation_euler = (math.radians(25.0), 0.0, 0.0)
    soporte.data.materials.append(mats["hierro_antorcha"])
    mover_a_coleccion(soporte, col_entorno)

    # Fuego / Ascua ardiente
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2,
        radius=0.10,
        location=(pos_antorcha.x, pos_antorcha.y, pos_antorcha.z + 0.08),
    )
    fuego = bpy.context.object
    fuego.data.materials.append(mats["fuego_antorcha"])
    mover_a_coleccion(fuego, col_entorno)

    # Luz cálida parpadeante
    luz_data = bpy.data.lights.new(name="Luz_Antorcha", type="POINT")
    luz_data.color = (1.0, 0.55, 0.12)
    luz_data.energy = 38.0
    luz_data.shadow_soft_size = 0.25
    luz_obj = bpy.data.objects.new("Luz_Antorcha", luz_data)
    luz_obj.location = (pos_antorcha.x, pos_antorcha.y, pos_antorcha.z + 0.15)
    col_entorno.objects.link(luz_obj)


# =============================================================================
# ILUMINACIÓN Y CÁMARA CINEMATOGRÁFICA
# =============================================================================

def configurar_camara_e_iluminacion(rows, cols, col_raiz):
    col_setup = obtener_o_crear_coleccion("00_Setup_Camara_Luces", col_raiz)

    # 1. Luces de Estudio 3-Point
    # Key Light (Sol Cálido)
    key_data = bpy.data.lights.new(name="Sol_Key", type="SUN")
    key_data.energy = 4.0
    key_data.color = (1.0, 0.95, 0.90)
    key_obj = bpy.data.objects.new("Sol_Key", key_data)
    key_obj.location = (25.0, -20.0, 30.0)
    key_obj.rotation_euler = (math.radians(45.0), math.radians(20.0), math.radians(-35.0))
    col_setup.objects.link(key_obj)

    # Fill Light (Luz de Relleno Azulada Eterna)
    fill_data = bpy.data.lights.new(name="Sol_Fill", type="SUN")
    fill_data.energy = 1.8
    fill_data.color = (0.70, 0.82, 1.0)
    fill_obj = bpy.data.objects.new("Sol_Fill", fill_data)
    fill_obj.location = (-25.0, 25.0, 25.0)
    fill_obj.rotation_euler = (math.radians(50.0), math.radians(-25.0), math.radians(145.0))
    col_setup.objects.link(fill_obj)

    # Rim Light (Contraluz)
    rim_data = bpy.data.lights.new(name="Sol_Rim", type="SUN")
    rim_data.energy = 2.4
    rim_data.color = (0.92, 0.85, 1.0)
    rim_obj = bpy.data.objects.new("Sol_Rim", rim_data)
    rim_obj.location = (0.0, 30.0, 20.0)
    rim_obj.rotation_euler = (math.radians(65.0), math.radians(0.0), math.radians(180.0))
    col_setup.objects.link(rim_obj)

    # 2. Cámara Isométrica
    max_dim = max(rows, cols)
    dist = max_dim * TILE_SIZE * 1.55

    target = bpy.data.objects.new("Camara_Target", None)
    target.location = (0.0, 0.0, 0.5)
    col_setup.objects.link(target)

    cam_data = bpy.data.cameras.new(name="Camara_Isometrica")
    cam_data.type = "PERSP"
    cam_data.lens = 52.0

    cam_obj = bpy.data.objects.new("Camara_Nivel", cam_data)
    cam_obj.location = (dist * 0.70, -dist * 0.80, dist * 0.75)
    col_setup.objects.link(cam_obj)

    track = cam_obj.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    bpy.context.scene.camera = cam_obj

    # 3. Fondo de Mundo de Estudio
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("World_Studio")
    world = bpy.context.scene.world
    if hasattr(world, "node_tree") and world.node_tree:
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg is not None:
            bg.inputs["Color"].default_value = (0.022, 0.024, 0.030, 1.0)
            bg.inputs["Strength"].default_value = 0.5

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
    bpy.context.scene.render.resolution_y = 1080
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

def construir_escena_caso1():
    json_path = obtener_ruta_json()
    print(f"Cargando nivel de Caso 1 desde: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = data["dimensiones"]["filas"]
    cols = data["dimensiones"]["columnas"]
    nombre_mapa = data.get("mapa_nombre", "Mapa de Monedas")
    k = data.get("k", 5)

    print(f"Construyendo diorama 3D para {nombre_mapa} ({rows}x{cols}) con {k} monedas...")

    limpiar_escena()
    mats = inicializar_materiales_caso1()

    col_raiz = obtener_o_crear_coleccion("Caso1_Colocacion_Monedas")
    col_entorno = obtener_o_crear_coleccion("01_Entorno_Diorama", col_raiz)
    col_monedas = obtener_o_crear_coleccion("02_Monedas_Oro_3D", col_raiz)
    col_gameplay = obtener_o_crear_coleccion("03_Checkpoints", col_raiz)

    # 1. Zócalo base subterráneo
    crear_plinth_diorama(rows, cols, col_entorno, mats["plinth"])

    # 2. Celdas del mapa
    antorchas_colocadas = 0
    for cell in data["celdas"]:
        r = cell["row"]
        c = cell["col"]
        pos = coord_a_blender(r, c, rows, cols)
        es_borde = (r == 0 or r == rows - 1 or c == 0 or c == cols - 1)

        if cell["is_wall"]:
            crear_bloque_muro(pos, col_entorno, mats["muro"], es_borde=es_borde)

            # Colocar algunas antorchas en muros interiores estratégicos
            if MOSTRAR_ANTORCHAS and not es_borde and antorchas_colocadas < 6:
                if (r + c) % 5 == 0:
                    offset = Vector((0.0, -1.0, 0.0))
                    crear_antorcha_pared(pos, offset, col_entorno, mats)
                    antorchas_colocadas += 1
        else:
            crear_losa_suelo(pos, col_entorno, mats["suelo"])

    # 3. Checkpoints Start & End
    if data.get("start") is not None:
        pos_s = coord_a_blender(data["start"]["row"], data["start"]["col"], rows, cols)
        crear_portal_spawn_exit(pos_s, col_gameplay, mats["portal_start"], mats["muro"], es_start=True)

    if data.get("end") is not None:
        pos_e = coord_a_blender(data["end"]["row"], data["end"]["col"], rows, cols)
        crear_portal_spawn_exit(pos_e, col_gameplay, mats["portal_goal"], mats["muro"], es_start=False)

    # 4. Monedas de Oro 3D y Halos de Cobertura
    radio_cobertura = data["metricas"].get("radio_cobertura", 7.0)
    for moneda in data["monedas"]:
        pos_m = coord_a_blender(moneda["row"], moneda["col"], rows, cols)
        crear_moneda_oro_3d(pos_m, col_monedas, mats, radio_cobertura_local=radio_cobertura)

    # 5. Configurar Iluminación y Cámara
    configurar_camara_e_iluminacion(rows, cols, col_raiz)

    print("=" * 68)
    print("DIORAMA 3D CASO 1 GENERADO CON ÉXITO")
    print(f"• Mapa: {nombre_mapa}")
    print(f"• Monedas de oro 3D esculpidas: {len(data['monedas'])}")
    print(f"• Halos de cobertura k-center activos (Radio = {radio_cobertura})")
    print("• Zócalo de diorama y antorchas iluminadas")
    print("=" * 68)

    # Si se ejecuta en modo headless (-b), guardar escena y renderizar imagen
    if bpy.app.background:
        id_mapa = data.get("mapa_id", "b").lower()
        script_dir = Path(__file__).resolve().parent
        base_caso1 = script_dir.parent
        res_dir = base_caso1 / "resultados"
        fig_dir = base_caso1 / "figuras"
        res_dir.mkdir(parents=True, exist_ok=True)
        fig_dir.mkdir(parents=True, exist_ok=True)

        blend_output = res_dir / f"caso1_nivel_blender_mapa_{id_mapa}_k{k}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_output))
        print(f"Escena .blend guardada en: {blend_output}")

        img_output = fig_dir / f"caso1_blender_render_mapa_{id_mapa}_k{k}.png"
        bpy.context.scene.render.filepath = str(img_output)
        bpy.ops.render.render(write_still=True)
        print(f"Render 3D guardado en: {img_output}")


if __name__ == "__main__" and bpy is not None:
    construir_escena_caso1()
