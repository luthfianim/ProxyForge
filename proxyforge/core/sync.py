"""
core/sync.py
Buat & kelola collection hierarchy untuk proxy job.
Naming convention: "PF_<job_name>"
"""

import bpy


COLOR_TAG_MAP = {
    'NONE':     'NONE',
    'COLOR_01': 'COLOR_01',
    'COLOR_02': 'COLOR_02',
    'COLOR_03': 'COLOR_03',
    'COLOR_04': 'COLOR_04',
    'COLOR_05': 'COLOR_05',
    'COLOR_06': 'COLOR_06',
    'COLOR_07': 'COLOR_07',
    'COLOR_08': 'COLOR_08',
}


def make_proxy_collection_name(job_name: str) -> str:
    """Buat nama collection dari job name."""
    # Bersihkan karakter khusus
    safe = job_name.strip().replace(' ', '_')
    return f"PF_{safe}"


def get_or_create_collection(name: str, parent: bpy.types.Collection = None) -> bpy.types.Collection:
    """
    Ambil collection yang sudah ada, atau buat baru.
    Jika parent diberikan, pastikan collection masuk ke parent.
    """
    existing = bpy.data.collections.get(name)
    if existing:
        return existing

    col = bpy.data.collections.new(name)

    # Link ke parent atau ke scene collection
    if parent:
        parent.children.link(col)
    else:
        bpy.context.scene.collection.children.link(col)

    return col


def setup_proxy_collection(
    job_name: str,
    color_tag: str = 'NONE',
) -> bpy.types.Collection:
    """
    Buat collection utama untuk proxy job.
    Di-link ke Scene Collection root.

    Returns: Collection yang sudah siap diisi proxy objects.
    """
    col_name = make_proxy_collection_name(job_name)
    col = get_or_create_collection(col_name)

    # Set color tag
    if color_tag in COLOR_TAG_MAP:
        col.color_tag = COLOR_TAG_MAP[color_tag]

    return col


def delete_proxy_collection(collection_name: str):
    """
    Hapus collection dan semua isinya (objects + mesh data).
    Aman dipanggil bahkan jika collection tidak ada.
    """
    col = bpy.data.collections.get(collection_name)
    if col is None:
        return

    # Hapus semua objects dalam collection
    for obj in list(col.objects):
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj, do_unlink=True)
        # Hapus mesh data orphan
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    # Unlink dari semua parent collection
    for parent_col in bpy.data.collections:
        if col.name in parent_col.children:
            parent_col.children.unlink(col)
    # Juga cek scene collection
    scene_col = bpy.context.scene.collection
    if col.name in [c.name for c in scene_col.children]:
        scene_col.children.unlink(col)

    # Hapus collection itu sendiri
    bpy.data.collections.remove(col)


def set_collection_visibility(
    collection_name: str,
    viewport_visible: bool,
    render_visible: bool = None,
):
    """Toggle visibility collection di viewport dan/atau render."""
    col = bpy.data.collections.get(collection_name)
    if col is None:
        return

    # ViewLayer visibility
    vl_col = _find_view_layer_collection(bpy.context.view_layer.layer_collection, collection_name)
    if vl_col:
        vl_col.hide_viewport = not viewport_visible

    # Render visibility
    if render_visible is not None:
        col.hide_render = not render_visible


def _find_view_layer_collection(layer_col, name: str):
    """Cari LayerCollection secara rekursif berdasarkan nama."""
    if layer_col.collection.name == name:
        return layer_col
    for child in layer_col.children:
        found = _find_view_layer_collection(child, name)
        if found:
            return found
    return None
