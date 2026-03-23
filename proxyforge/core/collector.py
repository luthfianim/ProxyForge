"""
core/collector.py
Scan scene → kumpulkan semua objek yang berhubungan dengan satu armature.

Hasil: dict dengan key = tipe relationship, value = list of objects.
"""

import bpy


def _obj_uses_armature_deform(obj: bpy.types.Object, rig: bpy.types.Object) -> bool:
    """True jika obj punya Armature modifier yang menunjuk ke rig."""
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object == rig:
            return True
    return False


def _obj_is_parented_to_rig(obj: bpy.types.Object, rig: bpy.types.Object) -> bool:
    """True jika parent obj adalah rig (parent_type OBJECT atau BONE)."""
    return obj.parent == rig


def _obj_has_constraint_to_rig(obj: bpy.types.Object, rig: bpy.types.Object) -> bool:
    """True jika obj punya constraint yang target-nya adalah rig."""
    for con in obj.constraints:
        if hasattr(con, 'target') and con.target == rig:
            return True
    # Juga cek pose bones (untuk kebutuhan masa depan)
    return False


def _obj_has_driver_to_rig(obj: bpy.types.Object, rig: bpy.types.Object) -> bool:
    """True jika obj punya driver yang path-nya mengandung nama rig."""
    if obj.animation_data is None:
        return False
    for drv in obj.animation_data.drivers:
        for var in drv.driver.variables:
            for tgt in var.targets:
                if tgt.id == rig:
                    return True
    return False


def _is_mesh_object(obj: bpy.types.Object) -> bool:
    return obj.type == 'MESH'


def collect_related_objects(
    rig: bpy.types.Object,
    include_armature_deformed: bool = True,
    include_non_deformed: bool = True,
    include_constrained: bool = True,
    include_driven: bool = False,
    protected_names: set = None,
    skip_names: set = None,
) -> dict:
    """
    Scan semua objek di scene dan kategorikan berdasarkan relasi ke rig.

    Returns:
        {
            'armature_deformed': [...],
            'non_deformed':      [...],
            'constrained':       [...],
            'driven':            [...],
        }
    """

    if protected_names is None:
        protected_names = set()
    if skip_names is None:
        skip_names = set()

    result = {
        'armature_deformed': [],
        'non_deformed':      [],
        'constrained':       [],
        'driven':            [],
    }

    seen = set()  # Hindari dobel jika objek memenuhi lebih dari satu kriteria

    for obj in bpy.context.scene.objects:
        # Skip rig itu sendiri
        if obj == rig:
            continue
        # Skip non-mesh (mesh only untuk sekarang)
        if not _is_mesh_object(obj):
            continue
        # Skip yang ada di skip list
        if obj.name in skip_names:
            continue

        name = obj.name

        if include_armature_deformed and name not in seen:
            if _obj_uses_armature_deform(obj, rig):
                result['armature_deformed'].append(obj)
                seen.add(name)
                continue

        if include_non_deformed and name not in seen:
            if _obj_is_parented_to_rig(obj, rig) and not _obj_uses_armature_deform(obj, rig):
                result['non_deformed'].append(obj)
                seen.add(name)
                continue

        if include_constrained and name not in seen:
            if _obj_has_constraint_to_rig(obj, rig):
                result['constrained'].append(obj)
                seen.add(name)
                continue

        if include_driven and name not in seen:
            if _obj_has_driver_to_rig(obj, rig):
                result['driven'].append(obj)
                seen.add(name)

    return result
