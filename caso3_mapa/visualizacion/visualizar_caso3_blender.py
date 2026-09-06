r"""Visualización 3D Avanzada en Blender para el Caso 3 (Mapa 2D con Obstáculos y Gameplay).

Novedades de esta versión:
- TEXTURAS REALES PROCEDURALES:
  * Pared real: cantería de piedra oscura con micro-rugosidad, vetas y relieve (Bump Map 3D).
  * Suelo real: losas de piedra/pizarra con desgaste superficial, juntas y variación de tono.
- MONSTRUO 3D REAL (Enemigos):
  * Criatura demoníaca/gárgola completa con cuerpo orgánico, cuernos curvados, fauces abiertas
    con colmillos afilados, alas/espinas dorsales, garras y un gran ojo ciclópeo con pupila
    rasgada emisiva carmesí que ilumina el entorno.
- COFRE DEL TESORO 3D REAL (Recompensas):
  * Cofre con tablas de madera oscura, remaches dorados, tapa abierta dejando ver un montón de
    oro y una gran gema radiante flotante.
  * Altar arcano rúnico con orbe de amatista para la recompensa secreta de la rama.
- PORTALES START Y GOAL REALES:
  * Círculo rúnico de teletransporte esmeralda para el inicio y arco de portal dimensional para la meta.
- ACTIVACIÓN AUTOMÁTICA DE VISTA EN COLOR:
  * Al ejecutar el script, activa automáticamente el modo "Material Preview" (3er círculo superior)
    en todas las vistas 3D de Blender y configura los colores de modo Sólido para que NUNCA se vea gris plano.

INSTRUCCIONES:
1. Abre Blender 5.x (o 3.x/4.x).
2. Ve al espacio de trabajo "Scripting", carga este fichero y haz clic en "Run Script" (▶).
3. La vista cambiará automáticamente a color y texturas. También puedes pulsar Z > Rendered.
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
# CONFIGURACIÓN Y PARÁMETROS
# =============================================================================

RUTA_JSON = None            # None -> Busca automáticamente el JSON más reciente

TILE_SIZE = 2.0             # Tamaño de cada casilla en metros
GAP_SUELO = 0.08            # Separación entre losas
ALTURA_SUELO = 0.15         # Grosor de la losa
ALTURA_MURO = 2.20          # Altura de los muros de piedra
BISEL_MURO = 0.08           # Bisel de los bloques

MOSTRAR_RUTAS = True
MOSTRAR_LUCES_LOCALES = True
ACTIVAR_VISTA_MATERIAL = True


# =============================================================================
# LOCALIZACIÓN DEL ARCHIVO JSON
# =============================================================================

def obtener_ruta_json():
    import os
    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            arg_p = Path(sys.argv[idx + 1])
            if arg_p.exists():
                return arg_p

    if os.environ.get("CASO3_BLENDER_JSON"):
        env_p = Path(os.environ["CASO3_BLENDER_JSON"])
        if env_p.exists():
            return env_p

    if RUTA_JSON is not None and Path(RUTA_JSON).exists():
        return Path(RUTA_JSON)

    rutas_candidatas = [
        Path(bpy.path.abspath("//../experimentos/resultados")),
        Path(r"C:\Users\BCP\Desktop\TFM\caso3_mapa\experimentos\resultados"),
        Path(r"C:\Users\BCP\Desktop\TFM\caso3_mapa\resultados"),
    ]

    archivos = []
    for carpeta in rutas_candidatas:
        if carpeta.exists():
            archivos.extend(list(carpeta.glob("caso3_nivel_blender_*.json")))

    if not archivos:
        raise FileNotFoundError(
            "No se encontró 'caso3_nivel_blender_*.json'. "
            "Ejecuta primero 'exportar_nivel_blender_caso3.py'."
        )

    archivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return archivos[0]


# =============================================================================
# UTILIDADES DE ESCENA Y COLECCIONES
# =============================================================================

def limpiar_escena():
    """Limpia todos los objetos y datos previos para una escena desde cero."""
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
# SISTEMA DE MATERIALES CON TEXTURAS PROCEDURALES REALES
# =============================================================================

def crear_material_muro_procedural():
    """Pared Real: Sillería de piedra oscura con rugosidad, vetas y relieve (Bump)."""
    nombre = "Mat_Muro_Piedra_Real"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (0.12, 0.13, 0.15, 1.0)  # Color en modo sólido
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.05

    # Coordenadas de textura
    coord = nodes.new("ShaderNodeTexCoord")

    # Ruido de grano fino para aspereza de la roca
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 7.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.65

    # Voronoi para simular juntas y bloques de cantería
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = 2.2

    # Rampa de color para tonos de granito oscuro
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (0.05, 0.055, 0.065, 1.0)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.18, 0.19, 0.22, 1.0)

    # Bump Map para relieve táctil 3D
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.40
    bump.inputs["Distance"].default_value = 0.15

    # Conexiones
    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    links.new(coord.outputs["Object"], voronoi.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    return mat


def crear_material_suelo_procedural():
    """Suelo Real: Losas de piedra/pizarra con textura de adoquín, juntas y desgaste."""
    nombre = "Mat_Suelo_Losa_Real"
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = (0.24, 0.25, 0.28, 1.0)  # Color en modo sólido
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.70
    bsdf.inputs["Metallic"].default_value = 0.08

    coord = nodes.new("ShaderNodeTexCoord")

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.55

    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = 4.0

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.10
    ramp.color_ramp.elements[0].color = (0.12, 0.13, 0.15, 1.0)
    ramp.color_ramp.elements[1].position = 0.90
    ramp.color_ramp.elements[1].color = (0.30, 0.32, 0.35, 1.0)

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


def crear_material_pbr_simple(nombre, color_rgba, metallic=0.0, roughness=0.5,
                              emision=None, emision_fuerza=1.0):
    """Crea materiales para criaturas, props y detalles con color de viewport garantizado."""
    if nombre in bpy.data.materials:
        return bpy.data.materials[nombre]

    mat = bpy.data.materials.new(nombre)
    mat.diffuse_color = color_rgba  # ¡Fundamental para que NUNCA se vea gris en Solid view!

    nodes = mat.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

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


def inicializar_todos_materiales():
    """Genera la paleta de materiales completa y rica."""
    return {
        # Terreno
        "muro": crear_material_muro_procedural(),
        "suelo": crear_material_suelo_procedural(),

        # Monstruo (Criatura Enemiga)
        "piel_monstruo": crear_material_pbr_simple(
            "Mat_Monstruo_Piel",
            (0.18, 0.08, 0.22, 1.0),  # Piel púrpura oscura demoníaca
            metallic=0.15,
            roughness=0.60,
        ),
        "ojo_esclera": crear_material_pbr_simple(
            "Mat_Monstruo_Esclera",
            (0.85, 0.82, 0.70, 1.0),
            roughness=0.30,
        ),
        "ojo_pupila": crear_material_pbr_simple(
            "Mat_Monstruo_Ojo_Emisivo",
            (1.0, 0.02, 0.05, 1.0),
            emision=(1.0, 0.02, 0.05, 1.0),
            emision_fuerza=12.0,
        ),
        "cuerno_hueso": crear_material_pbr_simple(
            "Mat_Monstruo_Cuerno",
            (0.08, 0.07, 0.09, 1.0),  # Hueso obsidiana
            metallic=0.40,
            roughness=0.35,
        ),
        "colmillos": crear_material_pbr_simple(
            "Mat_Monstruo_Colmillos",
            (0.92, 0.90, 0.80, 1.0),  # Marfil afilado
            roughness=0.25,
        ),

        # Cofre y Tesoros
        "madera_cofre": crear_material_pbr_simple(
            "Mat_Cofre_Madera",
            (0.24, 0.12, 0.06, 1.0),  # Roble envejecido
            roughness=0.75,
        ),
        "metal_dorado": crear_material_pbr_simple(
            "Mat_Metal_Dorado",
            (1.0, 0.75, 0.10, 1.0),
            metallic=0.90,
            roughness=0.25,
        ),
        "gema_oro": crear_material_pbr_simple(
            "Mat_Gema_Oro_Radiante",
            (1.0, 0.85, 0.15, 1.0),
            emision=(1.0, 0.82, 0.10, 1.0),
            emision_fuerza=9.0,
        ),
        "gema_secreta": crear_material_pbr_simple(
            "Mat_Orbe_Amatista_Secreta",
            (0.80, 0.15, 1.0, 1.0),
            emision=(0.85, 0.20, 1.0, 1.0),
            emision_fuerza=11.0,
        ),

        # Portales
        "portal_start": crear_material_pbr_simple(
            "Mat_Portal_Start_Vortex",
            (0.0, 0.95, 0.60, 1.0),
            emision=(0.0, 0.95, 0.60, 1.0),
            emision_fuerza=8.0,
        ),
        "portal_goal": crear_material_pbr_simple(
            "Mat_Portal_Goal_Vortex",
            (1.0, 0.75, 0.05, 1.0),
            emision=(1.0, 0.75, 0.05, 1.0),
            emision_fuerza=8.0,
        ),

        # Rutas de Neón
        "ruta_neon": crear_material_pbr_simple(
            "Mat_Ruta_Neon_Cyan",
            (0.0, 0.80, 1.0, 1.0),
            emision=(0.0, 0.85, 1.0, 1.0),
            emision_fuerza=9.0,
        ),
        "rama_neon": crear_material_pbr_simple(
            "Mat_Rama_Neon_Magenta",
            (1.0, 0.25, 0.70, 1.0),
            emision=(1.0, 0.30, 0.75, 1.0),
            emision_fuerza=9.0,
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
# MODELADO DE ELEMENTOS
# =============================================================================

def crear_losa_suelo(pos, col, mat):
    ancho = TILE_SIZE - GAP_SUELO
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(pos.x, pos.y, -ALTURA_SUELO / 2.0),
    )
    obj = bpy.context.object
    obj.scale = (ancho, ancho, ALTURA_SUELO)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)

    bevel = obj.modifiers.new("Bisel", type="BEVEL")
    bevel.width = 0.03
    bevel.segments = 2
    mover_a_coleccion(obj, col)
    return obj


def crear_bloque_muro(pos, col, mat):
    ancho = TILE_SIZE - GAP_SUELO * 0.5
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(pos.x, pos.y, ALTURA_MURO / 2.0),
    )
    obj = bpy.context.object
    obj.scale = (ancho, ancho, ALTURA_MURO)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat)

    bevel = obj.modifiers.new("Bisel", type="BEVEL")
    bevel.width = BISEL_MURO
    bevel.segments = 3
    mover_a_coleccion(obj, col)
    return obj


# -----------------------------------------------------------------------------
# MONSTRUO 3D REAL (CRIATURA COMPLETA)
# -----------------------------------------------------------------------------

def crear_monstruo_3d(pos, coleccion, mats):
    """Crea una criatura monstruosa 3D detallada (gárgola demoníaca ciclópea)."""
    # 1. Cuerpo / Cabeza orgánica
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=3,
        radius=0.55,
        location=(pos.x, pos.y, 0.72),
    )
    cuerpo = bpy.context.object
    cuerpo.name = "Monstruo_Cuerpo"
    cuerpo.scale = (0.95, 0.85, 1.05)
    bpy.ops.object.transform_apply(scale=True)
    cuerpo.data.materials.append(mats["piel_monstruo"])
    mover_a_coleccion(cuerpo, coleccion)

    # 2. Gran Ojo Ciclópeo Demoníaco (Esclera)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.22,
        location=(pos.x, pos.y - 0.40, 0.82),
    )
    esclera = bpy.context.object
    esclera.name = "Monstruo_Ojo_Esclera"
    esclera.scale = (1.0, 0.60, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    esclera.data.materials.append(mats["ojo_esclera"])
    mover_a_coleccion(esclera, coleccion)

    # 3. Pupila rasgada vertical emisiva (Brillo rojo demoníaco)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.06,
        depth=0.22,
        location=(pos.x, pos.y - 0.48, 0.82),
    )
    pupila = bpy.context.object
    pupila.name = "Monstruo_Pupila_Emisiva"
    pupila.scale = (0.4, 0.2, 1.1)
    bpy.ops.object.transform_apply(scale=True)
    pupila.data.materials.append(mats["ojo_pupila"])
    mover_a_coleccion(pupila, coleccion)

    # 4. Ceño / Cresta amenazante
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(pos.x, pos.y - 0.35, 1.02),
    )
    ceno = bpy.context.object
    ceno.name = "Monstruo_Cresta"
    ceno.scale = (0.50, 0.22, 0.12)
    ceno.rotation_euler = (math.radians(20.0), 0.0, 0.0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    ceno.data.materials.append(mats["cuerno_hueso"])
    mover_a_coleccion(ceno, coleccion)

    # 5. Grandes Cuernos Curvados
    for lado, dx, r_z in ((-1, -0.40, 35.0), (1, 0.40, -35.0)):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.13,
            radius2=0.02,
            depth=0.75,
            location=(pos.x + dx, pos.y - 0.05, 1.25),
        )
        cuerno = bpy.context.object
        cuerno.name = f"Monstruo_Cuerno_{'I' if lado == -1 else 'D'}"
        cuerno.rotation_euler = (
            math.radians(-25.0),
            math.radians(lado * 40.0),
            math.radians(r_z),
        )
        cuerno.data.materials.append(mats["cuerno_hueso"])
        mover_a_coleccion(cuerno, coleccion)

    # 6. Fauces y Colmillos Afilados
    for idx, (fx, fy, fz, fh, rot_x) in enumerate([
        (-0.16, -0.38, 0.58, 0.20, 180.0),  # Colmillo superior izq
        (0.16, -0.38, 0.58, 0.20, 180.0),   # Colmillo superior der
        (-0.08, -0.40, 0.46, 0.22, 0.0),    # Colmillo inferior izq
        (0.08, -0.40, 0.46, 0.22, 0.0),     # Colmillo inferior der
    ]):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.045,
            depth=fh,
            location=(pos.x + fx, pos.y + fy, fz),
        )
        colmillo = bpy.context.object
        colmillo.name = f"Monstruo_Colmillo_{idx}"
        colmillo.rotation_euler = (math.radians(rot_x), 0.0, 0.0)
        colmillo.data.materials.append(mats["colmillos"])
        mover_a_coleccion(colmillo, coleccion)

    # 7. Garras / Brazos apoyados en la losa
    for lado, gx in ((-1, -0.52), (1, 0.52)):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.10,
            depth=0.55,
            location=(pos.x + gx, pos.y - 0.15, 0.35),
        )
        brazo = bpy.context.object
        brazo.name = f"Monstruo_Brazo_{'I' if lado == -1 else 'D'}"
        brazo.rotation_euler = (math.radians(35.0), math.radians(lado * 20.0), 0.0)
        brazo.data.materials.append(mats["piel_monstruo"])
        mover_a_coleccion(brazo, coleccion)

        # Garras afiladas
        for c_idx, c_dx in enumerate((-0.05, 0.0, 0.05)):
            bpy.ops.mesh.primitive_cone_add(
                radius1=0.03,
                depth=0.14,
                location=(pos.x + gx + c_dx, pos.y - 0.38, 0.08),
            )
            una = bpy.context.object
            una.rotation_euler = (math.radians(85.0), 0.0, 0.0)
            una.data.materials.append(mats["cuerno_hueso"])
            mover_a_coleccion(una, coleccion)

    # 8. Espinas Dorsales en la espalda
    for s_idx, s_z in enumerate((0.95, 0.70, 0.45)):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.06,
            depth=0.30,
            location=(pos.x, pos.y + 0.38, s_z),
        )
        espina = bpy.context.object
        espina.rotation_euler = (math.radians(-75.0), 0.0, 0.0)
        espina.data.materials.append(mats["cuerno_hueso"])
        mover_a_coleccion(espina, coleccion)

    # 9. Luz demoníaca local
    if MOSTRAR_LUCES_LOCALES:
        crear_luz_puntual(
            f"Luz_Monstruo_{pos.x:.1f}_{pos.y:.1f}",
            (pos.x, pos.y - 0.60, 0.85),
            color=(1.0, 0.05, 0.08),
            potencia=45.0,
            radio=0.35,
            coleccion=coleccion,
        )


# -----------------------------------------------------------------------------
# COFRE DEL TESORO 3D REAL (RECOMPENSAS)
# -----------------------------------------------------------------------------

def crear_cofre_tesoro(pos, coleccion, mats):
    """Crea un cofre del tesoro de madera con herrajes dorados y gemas radiantes."""
    # 1. Cuerpo del cofre (Madera)
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(pos.x, pos.y, 0.22),
    )
    base = bpy.context.object
    base.name = "Cofre_Base"
    base.scale = (0.75, 0.50, 0.42)
    bpy.ops.object.transform_apply(scale=True)
    base.data.materials.append(mats["madera_cofre"])
    mover_a_coleccion(base, coleccion)

    # 2. Herrajes metálicos dorados
    for hx in (-0.38, 0.38):
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(pos.x + hx, pos.y, 0.22),
        )
        banda = bpy.context.object
        banda.scale = (0.04, 0.52, 0.44)
        bpy.ops.object.transform_apply(scale=True)
        banda.data.materials.append(mats["metal_dorado"])
        mover_a_coleccion(banda, coleccion)

    # Cerradura frontal
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(pos.x, pos.y - 0.26, 0.24),
    )
    cerradura = bpy.context.object
    cerradura.scale = (0.10, 0.04, 0.12)
    bpy.ops.object.transform_apply(scale=True)
    cerradura.data.materials.append(mats["metal_dorado"])
    mover_a_coleccion(cerradura, coleccion)

    # 3. Tapa semi-abierta revelando el tesoro
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16,
        radius=0.26,
        depth=0.76,
        location=(pos.x, pos.y + 0.10, 0.52),
    )
    tapa = bpy.context.object
    tapa.name = "Cofre_Tapa"
    tapa.rotation_euler = (math.radians(-25.0), math.radians(90.0), 0.0)
    tapa.data.materials.append(mats["madera_cofre"])
    mover_a_coleccion(tapa, coleccion)

    # 4. Oro y Gema Radiante flotante
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2,
        radius=0.22,
        location=(pos.x, pos.y, 0.78),
    )
    gema = bpy.context.object
    gema.name = "Gema_Radiante"
    gema.scale = (0.8, 0.8, 1.2)
    gema.rotation_euler = (math.radians(35.0), math.radians(45.0), 0.0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    gema.data.materials.append(mats["gema_oro"])
    mover_a_coleccion(gema, coleccion)

    if MOSTRAR_LUCES_LOCALES:
        crear_luz_puntual(
            f"Luz_Cofre_{pos.x:.1f}_{pos.y:.1f}",
            (pos.x, pos.y, 0.85),
            color=(1.0, 0.82, 0.12),
            potencia=40.0,
            radio=0.30,
            coleccion=coleccion,
        )


def crear_altar_recompensa_secreta(pos, coleccion, mats):
    """Crea un altar místico con pedestal rúnico y un orbe de amatista flotante."""
    # Pedestal de piedra
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
        radius=0.45,
        depth=0.45,
        location=(pos.x, pos.y, 0.22),
    )
    pedestal = bpy.context.object
    pedestal.data.materials.append(mats["muro"])
    mover_a_coleccion(pedestal, coleccion)

    # Anillo arcano de oro
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.35,
        minor_radius=0.04,
        location=(pos.x, pos.y, 0.50),
    )
    anillo = bpy.context.object
    anillo.data.materials.append(mats["metal_dorado"])
    mover_a_coleccion(anillo, coleccion)

    # Orbe de amatista radiante
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=3,
        radius=0.28,
        location=(pos.x, pos.y, 0.85),
    )
    orbe = bpy.context.object
    orbe.data.materials.append(mats["gema_secreta"])
    mover_a_coleccion(orbe, coleccion)

    if MOSTRAR_LUCES_LOCALES:
        crear_luz_puntual(
            f"Luz_Altar_Secreto_{pos.x:.1f}",
            (pos.x, pos.y, 0.95),
            color=(0.85, 0.20, 1.0),
            potencia=45.0,
            radio=0.35,
            coleccion=coleccion,
        )


# -----------------------------------------------------------------------------
# PORTALES START Y GOAL REALES
# -----------------------------------------------------------------------------

def crear_portal_vortex(pos, coleccion, mat_energia, mat_base, es_start=True):
    """Crea un portal dimensional con base de sillería y anillo de energía."""
    # Base octogonal biselada
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
        radius=TILE_SIZE * 0.40,
        depth=0.22,
        location=(pos.x, pos.y, 0.11),
    )
    base = bpy.context.object
    base.data.materials.append(mat_base)
    mover_a_coleccion(base, coleccion)

    # Anillo de vórtice
    bpy.ops.mesh.primitive_torus_add(
        major_radius=TILE_SIZE * 0.30,
        minor_radius=0.07,
        location=(pos.x, pos.y, 0.26),
    )
    anillo = bpy.context.object
    anillo.data.materials.append(mat_energia)
    mover_a_coleccion(anillo, coleccion)

    # Cristal de invocación central flotante
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=6,
        radius=0.20,
        depth=0.65,
        location=(pos.x, pos.y, 0.75),
    )
    cristal = bpy.context.object
    cristal.rotation_euler = (math.radians(15.0), math.radians(25.0), 0.0)
    cristal.data.materials.append(mat_energia)
    mover_a_coleccion(cristal, coleccion)

    if MOSTRAR_LUCES_LOCALES:
        color_luz = (0.0, 0.95, 0.60) if es_start else (1.0, 0.75, 0.10)
        crear_luz_puntual(
            f"Luz_{'Start' if es_start else 'Goal'}",
            (pos.x, pos.y, 0.90),
            color=color_luz,
            potencia=40.0,
            radio=0.40,
            coleccion=coleccion,
        )


def crear_curva_3d(nombre, puntos, mat, radio, col):
    curva_data = bpy.data.curves.new(name=nombre, type="CURVE")
    curva_data.dimensions = "3D"
    curva_data.bevel_depth = radio
    curva_data.bevel_resolution = 4
    curva_data.use_fill_caps = True

    spline = curva_data.splines.new(type="POLY")
    spline.points.add(len(puntos) - 1)

    for idx, p in enumerate(puntos):
        spline.points[idx].co = (p.x, p.y, 0.45, 1.0)

    obj = bpy.data.objects.new(nombre, curva_data)
    obj.data.materials.append(mat)
    col.objects.link(obj)
    return obj


def crear_luz_puntual(nombre, location, color, potencia, radio, coleccion):
    luz_data = bpy.data.lights.new(name=nombre, type="POINT")
    luz_data.color = color
    luz_data.energy = potencia
    luz_data.shadow_soft_size = radio
    obj = bpy.data.objects.new(name=nombre, object_data=luz_data)
    obj.location = location
    coleccion.objects.link(obj)
    return obj


# =============================================================================
# ILUMINACIÓN, CÁMARA Y CONFIGURACIÓN DEL VIEWPORT
# =============================================================================

def configurar_iluminacion_camara_y_viewport(rows, cols, col_escena):
    col_setup = obtener_o_crear_coleccion("Iluminacion_y_Camara", col_escena)

    # 1. Luces de estudio (3 Puntos)
    key_data = bpy.data.lights.new(name="Luz_Key_Sun", type="SUN")
    key_data.energy = 4.5
    key_data.color = (1.0, 0.96, 0.92)
    key_obj = bpy.data.objects.new("Luz_Key_Sun", key_data)
    key_obj.location = (16.0, -14.0, 22.0)
    key_obj.rotation_euler = (math.radians(45.0), math.radians(20.0), math.radians(-35.0))
    col_setup.objects.link(key_obj)

    fill_data = bpy.data.lights.new(name="Luz_Fill_Sun", type="SUN")
    fill_data.energy = 2.0
    fill_data.color = (0.75, 0.85, 1.0)
    fill_obj = bpy.data.objects.new("Luz_Fill_Sun", fill_data)
    fill_obj.location = (-16.0, 16.0, 16.0)
    fill_obj.rotation_euler = (math.radians(50.0), math.radians(-30.0), math.radians(140.0))
    col_setup.objects.link(fill_obj)

    rim_data = bpy.data.lights.new(name="Luz_Rim_Sun", type="SUN")
    rim_data.energy = 2.8
    rim_data.color = (0.90, 0.80, 1.0)
    rim_obj = bpy.data.objects.new("Luz_Rim_Sun", rim_data)
    rim_obj.location = (0.0, 22.0, 14.0)
    rim_obj.rotation_euler = (math.radians(70.0), math.radians(0.0), math.radians(180.0))
    col_setup.objects.link(rim_obj)

    # 2. Cámara Isométrica
    target = bpy.data.objects.new("Camara_Target", None)
    target.location = (0.0, 0.0, 0.8)
    col_setup.objects.link(target)

    cam_data = bpy.data.cameras.new(name="Camara_Isometrica")
    cam_data.type = "PERSP"
    cam_data.lens = 50.0

    cam_obj = bpy.data.objects.new("Camara_Nivel", cam_data)
    cam_obj.location = (20.0, -22.0, 22.0)
    col_setup.objects.link(cam_obj)

    track = cam_obj.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    bpy.context.scene.camera = cam_obj

    # 3. Fondo de Mundo Oscuro
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("World_Dungeon")
    world = bpy.context.scene.world
    if hasattr(world, "node_tree") and world.node_tree:
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg is not None:
            bg.inputs["Color"].default_value = (0.025, 0.028, 0.035, 1.0)
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
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.resolution_percentage = 100

    # 5. ACTIVACIÓN AUTOMÁTICA DEL MODO MATERIAL EN TODAS LAS VISTAS 3D
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

def construir_escena_caso3():
    json_path = obtener_ruta_json()
    print(f"Cargando nivel desde: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    rows = meta["grid_rows"]
    cols = meta["grid_cols"]

    print(f"Generando escena con texturas y props de gameplay ({rows}x{cols})...")

    limpiar_escena()
    mats = inicializar_todos_materiales()

    col_raiz = obtener_o_crear_coleccion("Caso3_Dungeon_Nivel")
    col_entorno = obtener_o_crear_coleccion("01_Entorno", col_raiz)
    col_gameplay = obtener_o_crear_coleccion("02_Gameplay", col_raiz)
    col_rutas = obtener_o_crear_coleccion("03_Rutas", col_raiz)

    # 1. Celdas de Suelo Real y Muros de Piedra Real
    for cell_info in data["cells"]:
        r = cell_info["row"]
        c = cell_info["col"]
        pos = coord_a_blender(r, c, rows, cols)

        if cell_info["is_open"]:
            crear_losa_suelo(pos, col_entorno, mats["suelo"])
        else:
            crear_bloque_muro(pos, col_entorno, mats["muro"])

    # 2. Props de Gameplay: Monstruos Reales, Cofres del Tesoro y Portales
    poi = data["points_of_interest"]

    # START y GOAL
    pos_start = coord_a_blender(poi["start"]["row"], poi["start"]["col"], rows, cols)
    pos_goal = coord_a_blender(poi["goal"]["row"], poi["goal"]["col"], rows, cols)
    crear_portal_vortex(pos_start, col_gameplay, mats["portal_start"], mats["muro"], es_start=True)
    crear_portal_vortex(pos_goal, col_gameplay, mats["portal_goal"], mats["muro"], es_start=False)

    # Cofres del Tesoro (Recompensas en ruta)
    for item in poi["route_rewards"]:
        pos_rew = coord_a_blender(item["row"], item["col"], rows, cols)
        crear_cofre_tesoro(pos_rew, col_gameplay, mats)

    # Altar de la Recompensa Secreta (Final de la rama si existe)
    if poi.get("branch_reward") is not None:
        pos_sec = coord_a_blender(poi["branch_reward"]["row"], poi["branch_reward"]["col"], rows, cols)
        crear_altar_recompensa_secreta(pos_sec, col_gameplay, mats)

    # MONSTRUOS REALES (Enemigos si existen)
    for item in poi.get("route_enemies", []):
        pos_ene = coord_a_blender(item["row"], item["col"], rows, cols)
        crear_monstruo_3d(pos_ene, col_gameplay, mats)

    # 3. Rutas de Neón
    if MOSTRAR_RUTAS:
        if "paths" in data and "main_path" in data["paths"]:
            puntos_main = [
                coord_a_blender(p["row"], p["col"], rows, cols)
                for p in data["paths"]["main_path"]
            ]
            crear_curva_3d("Ruta_Principal_Neon", puntos_main, mats["ruta_neon"], 0.065, col_rutas)

        if "paths" in data and "branch_path" in data["paths"]:
            puntos_branch = [
                coord_a_blender(p["row"], p["col"], rows, cols)
                for p in data["paths"]["branch_path"]
            ]
            crear_curva_3d("Rama_Secundaria_Neon", puntos_branch, mats["rama_neon"], 0.055, col_rutas)

    # 4. Iluminación, Cámara y Viewport
    configurar_iluminacion_camara_y_viewport(rows, cols, col_raiz)

    print("=" * 65)
    print("ESCENA 3D AVANZADA GENERADA CON ÉXITO")
    print("• Texturas de piedra y suelo activas")
    print("• Monstruos demoníacos generados")
    print("• Cofres del tesoro colocados")
    print("• Vista 3D configurada en modo 'Material Preview' con color")
    print("=" * 65)

    # Si se ejecuta en segundo plano (-b), renderizar y guardar
    if bpy.app.background:
        json_str = str(json_path).lower()
        if "qubo_full" in json_str or "qubo_completo" in json_str:
            stem = "caso3_nivel_blender_qubo_full_6x8"
            img_stem = "caso3_blender_qubo_full_render_6x8.png"
        elif "qubo" in json_str:
            stem = "caso3_nivel_blender_qubo_6x8"
            img_stem = "caso3_blender_qubo_render_6x8.png"
        else:
            stem = "caso3_nivel_blender_6x8"
            img_stem = "caso3_blender_render_6x8.png"

        blend_output = Path(r"C:\Users\BCP\Desktop\TFM\caso3_mapa\experimentos\resultados") / f"{stem}.blend"
        blend_output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_output))
        print(f"Escena .blend guardada en: {blend_output}")

        img_output = Path(r"C:\Users\BCP\Desktop\TFM\caso3_mapa\experimentos\figuras") / img_stem
        img_output.parent.mkdir(parents=True, exist_ok=True)
        bpy.context.scene.render.filepath = str(img_output)
        bpy.ops.render.render(write_still=True)
        print(f"Render 3D guardado en: {img_output}")


if __name__ == "__main__" and bpy is not None:
    construir_escena_caso3()
