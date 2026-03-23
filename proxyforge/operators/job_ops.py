"""
operators/job_ops.py
CRUD operations untuk Proxy Job list:
  - Add, Remove, Duplicate, Move Up/Down
  - Batch: Generate all, Delete all, Toggle all
"""

import bpy
from ..core import sync, collector


# ──────────────────────────────────────────────
#  Add Job
# ──────────────────────────────────────────────

class PF_OT_add_job(bpy.types.Operator):
    """Tambah Proxy Job baru"""
    bl_idname = "pf.add_job"
    bl_label = "Add Proxy Job"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        pf = context.scene.proxyforge
        job = pf.jobs.add()
        # Nama unik
        existing_names = {j.name for j in pf.jobs}
        base = "Proxy Job"
        n = 1
        candidate = base
        while candidate in existing_names:
            n += 1
            candidate = f"{base} {n:02d}"
        job.name = candidate

        # Set active ke job baru
        pf.active_job_index = len(pf.jobs) - 1

        self.report({'INFO'}, f"Job '{job.name}' ditambahkan")
        return {'FINISHED'}


# ──────────────────────────────────────────────
#  Remove Job
# ──────────────────────────────────────────────

class PF_OT_remove_job(bpy.types.Operator):
    """Hapus Proxy Job aktif (dan proxy collection-nya jika sudah digenerate)"""
    bl_idname = "pf.remove_job"
    bl_label = "Remove Proxy Job"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.proxyforge.jobs)

    def execute(self, context):
        pf = context.scene.proxyforge
        idx = pf.active_job_index
        job = pf.jobs[idx]

        # Hapus proxy collection jika ada
        if job.is_generated and job.proxy_collection_name:
            sync.delete_proxy_collection(job.proxy_collection_name)

        job_name = job.name
        pf.jobs.remove(idx)

        # Clamp index
        pf.active_job_index = min(idx, max(0, len(pf.jobs) - 1))

        self.report({'INFO'}, f"Job '{job_name}' dihapus")
        return {'FINISHED'}


# ──────────────────────────────────────────────
#  Duplicate Job
# ──────────────────────────────────────────────

class PF_OT_duplicate_job(bpy.types.Operator):
    """Duplikat settings job aktif ke job baru"""
    bl_idname = "pf.duplicate_job"
    bl_label = "Duplicate Job"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.proxyforge.jobs)

    def execute(self, context):
        pf = context.scene.proxyforge
        src = pf.jobs[pf.active_job_index]

        new_job = pf.jobs.add()

        # Copy properti dasar
        new_job.name = src.name + " (Copy)"
        new_job.source_rig = src.source_rig
        new_job.algorithm = src.algorithm
        new_job.collection_color = src.collection_color
        new_job.include_armature_deformed = src.include_armature_deformed
        new_job.include_non_deformed = src.include_non_deformed
        new_job.include_constrained = src.include_constrained
        new_job.include_driven = src.include_driven
        new_job.decimate_ratio = src.decimate_ratio
        new_job.decimate_method = src.decimate_method
        new_job.join_siblings = src.join_siblings
        new_job.link_rig_to_proxy = src.link_rig_to_proxy
        new_job.disable_in_renders = src.disable_in_renders
        # State baru = belum generate
        new_job.is_generated = False
        new_job.proxy_collection_name = ""
        new_job.visibility_state = 'SOURCE'

        pf.active_job_index = len(pf.jobs) - 1
        self.report({'INFO'}, f"Job '{new_job.name}' dibuat dari duplikat")
        return {'FINISHED'}


# ──────────────────────────────────────────────
#  Move Job
# ──────────────────────────────────────────────

class PF_OT_move_job(bpy.types.Operator):
    """Pindah job aktif ke atas atau ke bawah"""
    bl_idname = "pf.move_job"
    bl_label = "Move Job"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        items=[('UP', "Up", ""), ('DOWN', "Down", "")],
        default='UP',
    )

    @classmethod
    def poll(cls, context):
        return len(context.scene.proxyforge.jobs) > 1

    def execute(self, context):
        pf = context.scene.proxyforge
        idx = pf.active_job_index
        total = len(pf.jobs)

        if self.direction == 'UP' and idx > 0:
            pf.jobs.move(idx, idx - 1)
            pf.active_job_index = idx - 1
        elif self.direction == 'DOWN' and idx < total - 1:
            pf.jobs.move(idx, idx + 1)
            pf.active_job_index = idx + 1

        return {'FINISHED'}


# ──────────────────────────────────────────────
#  Batch Generate
# ──────────────────────────────────────────────

class PF_OT_batch_generate(bpy.types.Operator):
    """Generate proxy untuk semua job yang ditandai batch"""
    bl_idname = "pf.batch_generate"
    bl_label = "Batch Generate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(j.is_batch_marked and j.source_rig
                   for j in context.scene.proxyforge.jobs)

    def execute(self, context):
        pf = context.scene.proxyforge
        original_idx = pf.active_job_index
        count = 0

        for i, job in enumerate(pf.jobs):
            if not job.is_batch_marked or not job.source_rig:
                continue
            pf.active_job_index = i
            result = bpy.ops.pf.generate_proxy()
            if result == {'FINISHED'}:
                count += 1

        pf.active_job_index = original_idx
        self.report({'INFO'}, f"Batch generate selesai: {count} job diproses")
        return {'FINISHED'}


# ──────────────────────────────────────────────
#  Batch Delete
# ──────────────────────────────────────────────

class PF_OT_batch_delete(bpy.types.Operator):
    """Hapus semua proxy collections dari job yang ditandai batch"""
    bl_idname = "pf.batch_delete"
    bl_label = "Batch Delete Collections"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(j.is_batch_marked and j.is_generated
                   for j in context.scene.proxyforge.jobs)

    def execute(self, context):
        pf = context.scene.proxyforge
        original_idx = pf.active_job_index
        count = 0

        for i, job in enumerate(pf.jobs):
            if not job.is_batch_marked or not job.is_generated:
                continue
            pf.active_job_index = i
            result = bpy.ops.pf.delete_proxy()
            if result == {'FINISHED'}:
                count += 1

        pf.active_job_index = original_idx
        self.report({'INFO'}, f"Batch delete selesai: {count} collection dihapus")
        return {'FINISHED'}


CLASSES = [
    PF_OT_add_job,
    PF_OT_remove_job,
    PF_OT_duplicate_job,
    PF_OT_move_job,
    PF_OT_batch_generate,
    PF_OT_batch_delete,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
