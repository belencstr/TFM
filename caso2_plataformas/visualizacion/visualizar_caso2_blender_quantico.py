"""Visualización Blender de una solución QUBO/SA del Caso 2.

El JSON debe haber sido generado previamente con:
    python cuantico/experimentos/exportar_nivel_blender_qubo_reducido.py

IMPORTANTE:
La solución procede de una formulación QUBO resuelta con Simulated Annealing,
por lo que no debe describirse como ejecución sobre hardware cuántico.

Uso:
1. Ejecuta primero el exportador.
2. Copia la ruta del JSON generado.
3. Pégala en RUTA_JSON.
4. Abre Blender > Scripting.
5. Abre este fichero y pulsa Run Script.
"""

import bpy
import json
from mathutils import Vector


# -------------------------------------------------------------------------
# CAMBIA SOLO ESTA RUTA POR EL JSON GENERADO
# -------------------------------------------------------------------------
RUTA_JSON = (
    r"C:\Users\BCP\Desktop\TFM\caso2_plataformas"
    r"\cuantico\resultados"
    r"\caso2_nivel_blender_qubo_reducido_18x5_20260903_180117.json"
)


# -------------------------------------------------------------------------
# ESCALA VISUAL
# -------------------------------------------------------------------------
TILE_SIZE = 2.0
PROFUNDIDAD_PLATAFORMA = 3.5
GROSOR_PLATAFORMA = 0.45

ALTURA_MARCADOR = 1.6
RADIO_MARCADOR = 0.55

MOSTRAR_RUTA = True


def limpiar_escena():
    bpy.ops.object.select_all(
        action="SELECT"
    )
    bpy.ops.object.delete(
        use_global=False
    )

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def crear_material(
    nombre,
    color_rgba,
    metallic=0.0,
    roughness=0.5,
):
    material = bpy.data.materials.new(
        nombre
    )
    material.diffuse_color = color_rgba
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get(
        "Principled BSDF"
    )

    if bsdf is not None:
        bsdf.inputs[
            "Base Color"
        ].default_value = color_rgba
        bsdf.inputs[
            "Metallic"
        ].default_value = metallic
        bsdf.inputs[
            "Roughness"
        ].default_value = roughness

    return material


def crear_plataforma(
    x,
    y,
    ancho_tiles,
    material,
    nombre,
):
    ancho = ancho_tiles * TILE_SIZE

    centro_x = (
        x * TILE_SIZE
        + ancho / 2.0
    )
    centro_z = y * TILE_SIZE

    bpy.ops.mesh.primitive_cube_add(
        location=(
            centro_x,
            0.0,
            centro_z,
        )
    )

    obj = bpy.context.object
    obj.name = nombre

    obj.dimensions = (
        ancho,
        PROFUNDIDAD_PLATAFORMA,
        GROSOR_PLATAFORMA,
    )

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )

    obj.data.materials.append(
        material
    )

    bevel = obj.modifiers.new(
        name="Bevel",
        type="BEVEL",
    )
    bevel.width = 0.10
    bevel.segments = 3

    return obj


def crear_marcador(
    pos,
    texto,
    material,
):
    x = pos["x"] * TILE_SIZE
    z = pos["y"] * TILE_SIZE

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=RADIO_MARCADOR,
        depth=ALTURA_MARCADOR,
        location=(
            x + TILE_SIZE / 2.0,
            0.0,
            z + ALTURA_MARCADOR / 2.0,
        ),
    )

    obj = bpy.context.object
    obj.name = texto
    obj.data.materials.append(
        material
    )

    return obj


def centro_nodo(
    pos,
    ancho_tiles,
    start,
    goal,
):
    x = pos["x"]
    y = pos["y"]

    es_extremo = (
        (
            x == start["x"]
            and y == start["y"]
        )
        or
        (
            x == goal["x"]
            and y == goal["y"]
        )
    )

    if es_extremo:
        centro_x = (
            x * TILE_SIZE
            + TILE_SIZE / 2.0
        )
    else:
        centro_x = (
            x * TILE_SIZE
            + (
                ancho_tiles
                * TILE_SIZE
            ) / 2.0
        )

    centro_z = (
        y * TILE_SIZE
        + 0.55
    )

    return Vector(
        (
            centro_x,
            0.0,
            centro_z,
        )
    )


def crear_curva_ruta(
    ruta,
    ancho_tiles,
    start,
    goal,
    material,
):
    curva = bpy.data.curves.new(
        "Ruta_QUBO_SA",
        type="CURVE",
    )
    curva.dimensions = "3D"
    curva.bevel_depth = 0.08
    curva.bevel_resolution = 4

    spline = curva.splines.new(
        "POLY"
    )
    spline.points.add(
        len(ruta) - 1
    )

    for i, pos in enumerate(ruta):
        coord = centro_nodo(
            pos,
            ancho_tiles,
            start,
            goal,
        )

        spline.points[i].co = (
            coord.x,
            coord.y,
            coord.z,
            1.0,
        )

    obj = bpy.data.objects.new(
        "Ruta_QUBO_SA",
        curva,
    )
    bpy.context.collection.objects.link(
        obj
    )
    obj.data.materials.append(
        material
    )

    return obj


def crear_suelo_referencia(
    ancho,
    material,
):
    bpy.ops.mesh.primitive_cube_add(
        location=(
            ancho * TILE_SIZE / 2.0,
            0.0,
            -1.5,
        )
    )

    obj = bpy.context.object
    obj.name = "Base_Visual"

    obj.dimensions = (
        ancho * TILE_SIZE + 4.0,
        PROFUNDIDAD_PLATAFORMA + 2.0,
        0.25,
    )

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )

    obj.data.materials.append(
        material
    )


def apuntar(
    objeto,
    punto,
):
    direccion = (
        Vector(punto)
        - objeto.location
    )

    objeto.rotation_euler = (
        direccion
        .to_track_quat("-Z", "Y")
        .to_euler()
    )


def crear_camara(
    ancho,
    alto,
):
    bpy.ops.object.camera_add()

    camara = bpy.context.object
    camara.name = (
        "Camara_Caso2_QUBO_SA"
    )

    centro_x = (
        ancho * TILE_SIZE / 2.0
    )
    centro_z = (
        alto * TILE_SIZE / 2.0
    )

    # Para 18x5 acercamos la cámara respecto a la escena clásica 40x10.
    distancia_y = max(
        38.0,
        ancho * 2.3,
    )

    camara.location = (
        centro_x,
        -distancia_y,
        centro_z + 4.0,
    )

    apuntar(
        camara,
        (
            centro_x,
            0.0,
            centro_z,
        ),
    )

    camara.data.lens = 52
    bpy.context.scene.camera = camara

    return camara


def crear_luces(
    ancho,
    alto,
):
    centro_x = (
        ancho * TILE_SIZE / 2.0
    )
    centro_z = (
        alto * TILE_SIZE / 2.0
    )

    bpy.ops.object.light_add(
        type="AREA",
        location=(
            centro_x,
            -8.0,
            centro_z + 16.0,
        ),
    )

    principal = bpy.context.object
    principal.name = (
        "Luz_Principal_QUBO"
    )
    principal.data.energy = 1600
    principal.data.shape = "RECTANGLE"
    principal.data.size = 28.0
    principal.data.size_y = 15.0

    apuntar(
        principal,
        (
            centro_x,
            0.0,
            centro_z,
        ),
    )

    bpy.ops.object.light_add(
        type="AREA",
        location=(
            centro_x,
            10.0,
            centro_z + 7.0,
        ),
    )

    relleno = bpy.context.object
    relleno.name = (
        "Luz_Relleno_QUBO"
    )
    relleno.data.energy = 800
    relleno.data.size = 22.0

    apuntar(
        relleno,
        (
            centro_x,
            0.0,
            centro_z,
        ),
    )


def crear_texto_titulo(
    ancho,
    alto,
    material,
):
    bpy.ops.object.text_add(
        location=(
            ancho * TILE_SIZE / 2.0,
            0.0,
            alto * TILE_SIZE + 2.5,
        ),
        rotation=(
            1.5708,
            0.0,
            0.0,
        ),
    )

    texto = bpy.context.object
    texto.name = "Titulo_QUBO_SA"
    texto.data.body = (
        "QUBO reducido + "
        "Simulated Annealing"
    )
    texto.data.align_x = "CENTER"
    texto.data.size = 1.2
    texto.data.extrude = 0.025
    texto.data.materials.append(
        material
    )


def configurar_render():
    escena = bpy.context.scene

    # Compatible con Blender 4.x.
    try:
        escena.render.engine = (
            "BLENDER_EEVEE_NEXT"
        )
    except Exception:
        escena.render.engine = (
            "BLENDER_EEVEE"
        )

    escena.render.resolution_x = 1600
    escena.render.resolution_y = 700
    escena.render.resolution_percentage = 100

    escena.world.color = (
        0.025,
        0.03,
        0.045,
    )


def main():
    with open(
        RUTA_JSON,
        "r",
        encoding="utf-8",
    ) as f:
        datos = json.load(f)

    limpiar_escena()

    ancho_mapa = (
        datos["escenario"]["ancho"]
    )
    alto_mapa = (
        datos["escenario"]["alto"]
    )
    ancho_plataforma = (
        datos["ancho_plataforma"]
    )

    start = datos["start"]
    goal = datos["goal"]
    plataformas = datos["plataformas"]
    ruta = datos["ruta"]

    # Cambio de paleta respecto al CP-SAT para que las capturas
    # se distingan visualmente, pero se conserva la misma geometría.
    material_plataforma = crear_material(
        "Material_Plataformas_QUBO",
        (0.38, 0.16, 0.68, 1.0),
        metallic=0.08,
        roughness=0.35,
    )

    material_start = crear_material(
        "Material_START",
        (0.08, 0.65, 0.25, 1.0),
        roughness=0.35,
    )

    material_goal = crear_material(
        "Material_GOAL",
        (0.85, 0.20, 0.12, 1.0),
        roughness=0.35,
    )

    material_ruta = crear_material(
        "Material_Ruta_QUBO",
        (0.15, 0.85, 1.0, 1.0),
        roughness=0.22,
    )

    material_base = crear_material(
        "Material_Base",
        (0.035, 0.045, 0.065, 1.0),
        roughness=0.75,
    )

    material_texto = crear_material(
        "Material_Texto_QUBO",
        (0.82, 0.72, 1.0, 1.0),
        roughness=0.35,
    )

    for i, p in enumerate(
        plataformas,
        start=1,
    ):
        crear_plataforma(
            p["x"],
            p["y"],
            ancho_plataforma,
            material_plataforma,
            f"Plataforma_QUBO_{i:02d}",
        )

    crear_marcador(
        start,
        "START",
        material_start,
    )

    crear_marcador(
        goal,
        "GOAL",
        material_goal,
    )

    if MOSTRAR_RUTA:
        crear_curva_ruta(
            ruta,
            ancho_plataforma,
            start,
            goal,
            material_ruta,
        )

    crear_suelo_referencia(
        ancho_mapa,
        material_base,
    )

    crear_texto_titulo(
        ancho_mapa,
        alto_mapa,
        material_texto,
    )

    crear_camara(
        ancho_mapa,
        alto_mapa,
    )

    crear_luces(
        ancho_mapa,
        alto_mapa,
    )

    configurar_render()

    print("=" * 76)
    print("CASO 2 — ESCENA QUBO/SA GENERADA EN BLENDER")
    print("=" * 76)
    print(
        f"Versión: {datos.get('version')}"
    )
    print(
        f"Plataformas: {len(plataformas)}"
    )
    print(
        f"Ruta: {len(ruta) - 1} saltos"
    )

    metricas = datos.get(
        "metricas",
        {},
    )

    if metricas:
        print(
            "Energía QUBO: "
            f"{metricas.get('energia_qubo')}"
        )
        print(
            "Validación completa: "
            f"{metricas.get('validacion_completa')}"
        )

    print(
        "La escena está lista para "
        "visualizar o renderizar."
    )


if __name__ == "__main__":
    main()
