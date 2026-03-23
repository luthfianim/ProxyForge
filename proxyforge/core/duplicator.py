"""
core/duplicator.py — v0.1.5

Root cause bug polygon tidak berkurang:
  bmesh.ops.decimate TIDAK EKSIS di Blender Python API.
  Semua versi sebelumnya silently skip decimation tanpa error.

Fix: pakai Decimate modifier biasa, apply SEBELUM Armature modifier ditambah,
dengan set active object secara langsung (tidak butuh temp_override).

Urutan final yang benar:
  1. Set REST POSE
  2. Bake evaluated mesh → mesh data bersih
  3. Buat Object dari mesh, link ke collection (object sudah ada di scene)
  4. Set object sebagai active → apply Decimate modifier ← FIX UTAMA
  5. KDTree weight transfer
  6. Add Armature modifier
  7. Restore pose
"""

import bpy
import mathutils


# ─────────────────────────────────────────────────────────
#  REST POSE helpers
# ─────────────────────────────────────────────────────────

def _set_rig_rest_pose(rig):
    old = rig.data.pose_position
    rig.data.pose_position = 'REST'
    return old

def _restore_rig_pose(rig, old_val):
    rig.data.pose_position = old_val


# ─────────────────────────────────────────────────────────
#  Decimate via modifier — SATU-SATUNYA cara yang pasti bekerja
# ─────────────────────────────────────────────────────────

def _apply_decimate(
    obj: bpy.types.Object,
    ratio: float,
    method: str,
    context: bpy.types.Context,
):
    """
    Add Decimate modifier ke obj lalu langsung apply.

    Syarat agar modifier_apply berhasil:
    - obj sudah di-link ke collection yang ada di scene  ← sudah terpenuhi
    - obj harus jadi active object di view layer         ← kita set di sini
    - TIDAK boleh ada modifier lain di stack             ← dipanggil sebelum arm mod

    TIDAK pakai temp_override (sering crash di Blender 5.0).
    Cukup set active object langsung.
    """
    if ratio >= 1.0:
        return

    import math

    # Simpan state
    prev_active = context.view_layer.objects.active

    # Set obj jadi active (obj sudah ada di collection yang di-link ke scene)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    # Tambah modifier
    mod = obj.modifiers.new(name="PF_Decimate", type='DECIMATE')

    if method == 'UNSUBDIV':
        mod.decimate_type = 'UNSUBDIV'
        mod.iterations = max(1, round(abs(math.log(max(ratio, 0.001)) / math.log(4))))
    else:
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = max(0.001, min(1.0, ratio))

    # Apply
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"[ProxyForge] Decimate OK '{obj.name}' "
              f"→ {len(obj.data.polygons)} faces (ratio={ratio})")
    except Exception as e:
        print(f"[ProxyForge] Decimate modifier_apply gagal '{obj.name}': {e}")
        if mod.name in [m.name for m in obj.modifiers]:
            obj.modifiers.remove(mod)

    # Restore
    obj.select_set(False)
    context.view_layer.objects.active = prev_active


# ─────────────────────────────────────────────────────────
#  Copy Vertex Groups via KDTree
# ─────────────────────────────────────────────────────────

def _copy_vertex_groups_kdtree(src: bpy.types.Object, dst: bpy.types.Object):
    """
    Transfer vertex weights via nearest-vertex lookup.
    Pure Python — tidak butuh ops atau modifier.
    Bekerja meskipun vertex count berbeda (karena decimation).
    """
    if not src.vertex_groups:
        return

    src_mesh = src.data
    dst_mesh = dst.data

    # Buat vertex groups kosong di dst
    for vg in src.vertex_groups:
        if dst.vertex_groups.get(vg.name) is None:
            dst.vertex_groups.new(name=vg.name)

    # Build KDTree dari vertex positions src
    kd = mathutils.kdtree.KDTree(len(src_mesh.vertices))
    for i, v in enumerate(src_mesh.vertices):
        kd.insert(v.co, i)
    kd.balance()

    # Pre-cache weights per vertex index
    src_weights = {}
    for v in src_mesh.vertices:
        weights = []
        for ge in v.groups:
            vg_name = src.vertex_groups[ge.group].name
            if ge.weight > 0.0:
                weights.append((vg_name, ge.weight))
        src_weights[v.index] = weights

    # Transfer ke setiap vertex dst
    for dst_v in dst_mesh.vertices:
        _co, src_idx, _dist = kd.find(dst_v.co)
        for vg_name, weight in src_weights.get(src_idx, []):
            dst_vg = dst.vertex_groups.get(vg_name)
            if dst_vg:
                dst_vg.add([dst_v.index], weight, 'REPLACE')


# ─────────────────────────────────────────────────────────
#  Add Armature modifier
# ─────────────────────────────────────────────────────────

def _add_armature_modifier(proxy_obj: bpy.types.Object, rig: bpy.types.Object):
    mod = proxy_obj.modifiers.new(name="PF_Armature", type='ARMATURE')
    mod.object = rig
    mod.use_vertex_groups = True
    return mod


# ─────────────────────────────────────────────────────────
#  Core: duplicate satu object
# ─────────────────────────────────────────────────────────

def duplicate_as_proxy(
    obj: bpy.types.Object,
    rig: bpy.types.Object,
    target_collection: bpy.types.Collection,
    context: bpy.types.Context,
    is_armature_deformed: bool = True,
    decimate_ratio: float = 0.1,
    decimate_method: str = 'COLLAPSE',
):
    try:
        if is_armature_deformed:

            # 1. REST POSE → bake
            old_pose = _set_rig_rest_pose(rig)
            context.view_layer.update()
            depsgraph = context.evaluated_depsgraph_get()

            evaluated_obj = obj.evaluated_get(depsgraph)
            baked_mesh = bpy.data.meshes.new_from_object(
                evaluated_obj,
                preserve_all_data_layers=False,
                depsgraph=depsgraph,
            )
            baked_mesh.name = f"PF_{obj.name}"

            # 2. Buat object dan link ke collection
            #    Object harus ada di scene SEBELUM modifier_apply dipanggil
            proxy_obj = bpy.data.objects.new(f"PF_{obj.name}", baked_mesh)
            proxy_obj.matrix_world = obj.matrix_world.copy()
            target_collection.objects.link(proxy_obj)

            # 3. Restore pose sebelum decimation
            #    (agar view layer update dengan benar)
            _restore_rig_pose(rig, old_pose)
            context.view_layer.update()

            # 4. DECIMATE — obj sudah di scene, modifier_apply aman dipanggil
            _apply_decimate(proxy_obj, decimate_ratio, decimate_method, context)

            # 5. Copy vertex groups dari src (rest pose mesh) ke proxy (decimated)
            try:
                _copy_vertex_groups_kdtree(obj, proxy_obj)
            except Exception as e:
                print(f"[ProxyForge] Weight transfer gagal '{obj.name}': {e}")

            # 6. Armature modifier — TERAKHIR
            _add_armature_modifier(proxy_obj, rig)

        else:
            # Non-deformed: bake + decimate + parent ke rig
            context.view_layer.update()
            depsgraph = context.evaluated_depsgraph_get()

            evaluated_obj = obj.evaluated_get(depsgraph)
            baked_mesh = bpy.data.meshes.new_from_object(
                evaluated_obj,
                preserve_all_data_layers=False,
                depsgraph=depsgraph,
            )
            baked_mesh.name = f"PF_{obj.name}"

            proxy_obj = bpy.data.objects.new(f"PF_{obj.name}", baked_mesh)
            proxy_obj.matrix_world = obj.matrix_world.copy()
            target_collection.objects.link(proxy_obj)

            context.view_layer.update()
            _apply_decimate(proxy_obj, decimate_ratio, decimate_method, context)

            proxy_obj.parent = rig
            proxy_obj.parent_type = 'OBJECT'
            proxy_obj.matrix_parent_inverse = rig.matrix_world.inverted()

        return proxy_obj

    except Exception as e:
        print(f"[ProxyForge] ERROR duplicate_as_proxy '{obj.name}': {e}")
        import traceback
        traceback.print_exc()
        return None


# ─────────────────────────────────────────────────────────
#  Batch
# ─────────────────────────────────────────────────────────

def duplicate_objects_as_proxies(
    related: dict,
    rig: bpy.types.Object,
    target_collection: bpy.types.Collection,
    context: bpy.types.Context,
    decimate_ratio: float = 0.1,
    decimate_method: str = 'COLLAPSE',
) -> list:

    proxies = []

    for obj in related.get('armature_deformed', []):
        proxy = duplicate_as_proxy(
            obj, rig, target_collection, context,
            is_armature_deformed=True,
            decimate_ratio=decimate_ratio,
            decimate_method=decimate_method,
        )
        if proxy:
            proxies.append(proxy)
        else:
            print(f"[ProxyForge] Skip '{obj.name}'")

    for key in ('non_deformed', 'constrained', 'driven'):
        for obj in related.get(key, []):
            proxy = duplicate_as_proxy(
                obj, rig, target_collection, context,
                is_armature_deformed=False,
                decimate_ratio=decimate_ratio,
                decimate_method=decimate_method,
            )
            if proxy:
                proxies.append(proxy)

    return proxies
