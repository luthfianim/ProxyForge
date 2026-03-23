"""
operators/generate_ops.py — v0.1.2
Decimation settings sekarang dipass langsung ke duplicator,
tidak ada apply_decimate_batch terpisah.
"""

import bpy
from ..core import collector, duplicator, sync


def _set_source_visibility(objects: list, viewport_visible: bool):
    for obj in objects:
        obj.hide_set(not viewport_visible)


class PF_OT_generate_proxy(bpy.types.Operator):
    """Generate atau Regenerate proxy collection untuk job aktif"""
    bl_idname = "pf.generate_proxy"
    bl_label = "Generate Proxy"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        pf = context.scene.proxyforge
        if not pf.jobs:
            return False
        idx = pf.active_job_index
        if idx >= len(pf.jobs):
            return False
        return pf.jobs[idx].source_rig is not None

    def execute(self, context):
        pf = context.scene.proxyforge
        job = pf.jobs[pf.active_job_index]
        rig = job.source_rig

        # ── 1. Hapus proxy lama ────────────────────────────────────
        if job.is_generated and job.proxy_collection_name:
            sync.delete_proxy_collection(job.proxy_collection_name)
            job.is_generated = False
            job.proxy_collection_name = ""

        # ── 2. Collect ─────────────────────────────────────────────
        related = collector.collect_related_objects(
            rig=rig,
            include_armature_deformed=job.include_armature_deformed,
            include_non_deformed=job.include_non_deformed,
            include_constrained=job.include_constrained,
            include_driven=job.include_driven,
        )

        all_objects = (
            related['armature_deformed'] +
            related['non_deformed'] +
            related['constrained'] +
            related['driven']
        )

        if not all_objects:
            self.report({'WARNING'},
                f"Tidak ada objek ditemukan terkait rig '{rig.name}'. "
                "Pastikan mesh punya Armature modifier yang menunjuk ke rig ini."
            )
            return {'CANCELLED'}

        total = len(all_objects)
        arm_count = len(related['armature_deformed'])
        self.report({'INFO'},
            f"Ditemukan {total} objek ({arm_count} armature-deformed) → generating..."
        )

        # ── 3. Buat proxy collection ───────────────────────────────
        col = sync.setup_proxy_collection(
            job_name=job.name,
            color_tag=job.collection_color,
        )
        job.proxy_collection_name = col.name

        # ── 4. Duplicate + Decimate + Armature modifier sekaligus ──
        #    Urutan di dalam duplicator:
        #    REST POSE → bake mesh → decimate mesh → buat obj → copy VGs → arm mod
        proxies = duplicator.duplicate_objects_as_proxies(
            related=related,
            rig=rig,
            target_collection=col,
            context=context,
            decimate_ratio=job.decimate_ratio,
            decimate_method=job.decimate_method,
        )

        if not proxies:
            self.report({'ERROR'},
                "Gagal membuat proxy. Cek System Console (Window → Toggle System Console)."
            )
            return {'CANCELLED'}

        # ── 5. Post-generation ─────────────────────────────────────
        if job.link_rig_to_proxy:
            if rig.name not in [o.name for o in col.objects]:
                col.objects.link(rig)

        if job.disable_in_renders:
            col.hide_render = True

        _set_source_visibility(all_objects, viewport_visible=False)
        sync.set_collection_visibility(col.name, viewport_visible=True)

        # ── 6. Update state ────────────────────────────────────────
        job.is_generated = True
        job.used_algorithm = job.algorithm
        job.visibility_state = 'PROXY'

        self.report(
            {'INFO'},
            f"✓ '{col.name}' selesai — {len(proxies)} proxy objects, "
            f"ratio {job.decimate_ratio}, ikut rig '{rig.name}'"
        )
        return {'FINISHED'}


class PF_OT_delete_proxy(bpy.types.Operator):
    """Hapus proxy collection untuk job aktif"""
    bl_idname = "pf.delete_proxy"
    bl_label = "Delete Proxy Collection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        pf = context.scene.proxyforge
        if not pf.jobs:
            return False
        idx = pf.active_job_index
        if idx >= len(pf.jobs):
            return False
        return pf.jobs[idx].is_generated

    def execute(self, context):
        pf = context.scene.proxyforge
        job = pf.jobs[pf.active_job_index]
        col_name = job.proxy_collection_name

        if col_name:
            sync.delete_proxy_collection(col_name)

        if job.source_rig:
            related = collector.collect_related_objects(rig=job.source_rig)
            all_objs = (
                related['armature_deformed'] +
                related['non_deformed'] +
                related['constrained'] +
                related['driven']
            )
            _set_source_visibility(all_objs, viewport_visible=True)

        job.is_generated = False
        job.proxy_collection_name = ""
        job.used_algorithm = ""
        job.visibility_state = 'SOURCE'

        self.report({'INFO'}, f"Proxy '{col_name}' dihapus")
        return {'FINISHED'}


class PF_OT_toggle_visibility(bpy.types.Operator):
    """Toggle tampilan Source ↔ Proxy ↔ Mixed"""
    bl_idname = "pf.toggle_visibility"
    bl_label = "Toggle Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        pf = context.scene.proxyforge
        if not pf.jobs:
            return False
        idx = pf.active_job_index
        if idx >= len(pf.jobs):
            return False
        return pf.jobs[idx].is_generated

    def execute(self, context):
        pf = context.scene.proxyforge
        job = pf.jobs[pf.active_job_index]

        related = collector.collect_related_objects(rig=job.source_rig)
        all_source = (
            related['armature_deformed'] +
            related['non_deformed'] +
            related['constrained'] +
            related['driven']
        )

        current = job.visibility_state
        if current == 'SOURCE':
            _set_source_visibility(all_source, False)
            sync.set_collection_visibility(job.proxy_collection_name, True)
            job.visibility_state = 'PROXY'
        elif current == 'PROXY':
            _set_source_visibility(all_source, True)
            sync.set_collection_visibility(job.proxy_collection_name, True)
            job.visibility_state = 'MIXED'
        else:
            _set_source_visibility(all_source, True)
            sync.set_collection_visibility(job.proxy_collection_name, False)
            job.visibility_state = 'SOURCE'

        return {'FINISHED'}


CLASSES = [
    PF_OT_generate_proxy,
    PF_OT_delete_proxy,
    PF_OT_toggle_visibility,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
