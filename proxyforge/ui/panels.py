"""
ui/panels.py
Semua panel dan UIList untuk N-Panel ProxyForge.
Lokasi: 3D Viewport → N-Panel → tab "ProxyForge"
"""

import bpy


# ──────────────────────────────────────────────
#  UIList — daftar Proxy Jobs
# ──────────────────────────────────────────────

class PF_UL_jobs(bpy.types.UIList):
    """Tampilkan daftar Proxy Jobs di panel."""
    bl_idname = "PF_UL_jobs"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        job = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # Warna collection
            row.prop(job, "collection_color", text="", icon_only=True, emboss=False)

            # Nama job (bisa di-double-click untuk rename)
            row.prop(job, "name", text="", emboss=False,
                     icon='ARMATURE_DATA' if job.source_rig else 'ERROR')

            # Indikator algoritma (setelah generate)
            if job.is_generated:
                alg_icon = 'MOD_DECIM' if job.used_algorithm == 'DECIMATE' else 'BONE_DATA'
                row.label(icon=alg_icon, text="")

            # Toggle visibility (source ↔ proxy)
            if job.is_generated:
                vis_icons = {
                    'PROXY':  'HIDE_OFF',
                    'SOURCE': 'HIDE_ON',
                    'MIXED':  'OVERLAY',
                }
                row.operator(
                    "pf.toggle_visibility",
                    text="",
                    icon=vis_icons.get(job.visibility_state, 'HIDE_OFF'),
                )

            # Batch mark checkbox
            row.prop(
                job, "is_batch_marked",
                text="",
                icon='CHECKBOX_HLT' if job.is_batch_marked else 'CHECKBOX_DEHLT',
                emboss=False,
            )


# ──────────────────────────────────────────────
#  Panel: Proxy Jobs
# ──────────────────────────────────────────────

class PF_PT_jobs(bpy.types.Panel):
    bl_label = "Proxy Jobs"
    bl_idname = "PF_PT_jobs"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ProxyForge"

    def draw(self, context):
        layout = self.layout
        pf = context.scene.proxyforge

        row = layout.row()
        # UIList
        row.template_list(
            "PF_UL_jobs", "",
            pf, "jobs",
            pf, "active_job_index",
            rows=4,
        )

        # Kolom tombol kanan
        col = row.column(align=True)
        col.operator("pf.add_job",    icon='ADD',    text="")
        col.operator("pf.remove_job", icon='REMOVE', text="")
        col.separator()
        col.operator("pf.move_job", icon='TRIA_UP',   text="").direction = 'UP'
        col.operator("pf.move_job", icon='TRIA_DOWN', text="").direction = 'DOWN'
        col.separator()
        # Specials (batch) menu
        col.menu("PF_MT_job_specials", icon='DOWNARROW_HLT', text="")


# ──────────────────────────────────────────────
#  Panel: Settings (untuk job aktif)
# ──────────────────────────────────────────────

class PF_PT_settings(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "PF_PT_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ProxyForge"

    @classmethod
    def poll(cls, context):
        pf = context.scene.proxyforge
        return bool(pf.jobs) and pf.active_job_index < len(pf.jobs)

    def draw(self, context):
        layout = self.layout
        pf = context.scene.proxyforge
        job = pf.jobs[pf.active_job_index]

        # ── Source Rig ──────────────────────────
        box = layout.box()
        box.label(text="Source Rig", icon='ARMATURE_DATA')
        box.prop(job, "source_rig", text="")

        # ── Algoritma ───────────────────────────
        box = layout.box()
        box.label(text="Algorithm", icon='MOD_DECIM')
        box.prop(job, "algorithm", expand=True)

        # ── Relationships ───────────────────────
        box = layout.box()
        box.label(text="Relationships", icon='LINKED')
        col = box.column(align=True)
        col.prop(job, "include_armature_deformed", text="Armature Deformed",
                 icon='MOD_ARMATURE')
        col.prop(job, "include_non_deformed",      text="Non-Deformed",
                 icon='OBJECT_DATA')
        col.prop(job, "include_constrained",       text="Constrained",
                 icon='CONSTRAINT')
        col.prop(job, "include_driven",            text="Driven",
                 icon='DRIVER')

        # ── Decimate ────────────────────────────
        if job.algorithm == 'DECIMATE':
            box = layout.box()
            box.label(text="Decimation", icon='MOD_DECIM')
            row = box.row()
            row.prop(job, "decimate_method", expand=True)
            box.prop(job, "decimate_ratio", slider=True)
            box.prop(job, "join_siblings")

        # ── Post-generation ─────────────────────
        box = layout.box()
        box.label(text="After Generate", icon='CHECKMARK')
        box.prop(job, "link_rig_to_proxy")
        box.prop(job, "disable_in_renders")


# ──────────────────────────────────────────────
#  Panel: Generate
# ──────────────────────────────────────────────

class PF_PT_generate(bpy.types.Panel):
    bl_label = "Generate"
    bl_idname = "PF_PT_generate"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ProxyForge"

    @classmethod
    def poll(cls, context):
        pf = context.scene.proxyforge
        return bool(pf.jobs) and pf.active_job_index < len(pf.jobs)

    def draw(self, context):
        layout = self.layout
        pf = context.scene.proxyforge
        job = pf.jobs[pf.active_job_index]

        col = layout.column(align=True)

        # Tombol Generate / Regenerate
        is_gen = job.is_generated
        label = "Regenerate Proxy" if is_gen else "Generate Proxy"
        icon  = 'FILE_REFRESH'     if is_gen else 'PLAY'

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("pf.generate_proxy", text=label, icon=icon)

        if is_gen:
            # Status info
            col.separator()
            info_box = col.box()
            info_row = info_box.row()
            info_row.label(text=f"Collection: {job.proxy_collection_name}", icon='COLLECTION_COLOR_04')
            info_row = info_box.row()
            info_row.label(text=f"Algorithm:  {job.used_algorithm}", icon='INFO')
            info_row = info_box.row()
            info_row.label(text=f"Visibility: {job.visibility_state}", icon='HIDE_OFF')

            col.separator()
            row2 = col.row(align=True)
            row2.operator("pf.toggle_visibility", text="Toggle Source/Proxy", icon='OVERLAY')
            row2 = col.row(align=True)
            row2.operator("pf.delete_proxy", text="Delete Proxy", icon='TRASH')


# ──────────────────────────────────────────────
#  Panel: Available Rigs (info panel)
# ──────────────────────────────────────────────

class PF_PT_available_rigs(bpy.types.Panel):
    bl_label = "Available Rigs"
    bl_idname = "PF_PT_available_rigs"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ProxyForge"

    def draw(self, context):
        layout = self.layout
        rigs = [obj for obj in context.scene.objects if obj.type == 'ARMATURE']

        if not rigs:
            layout.label(text="Tidak ada armature di scene", icon='INFO')
            return

        for rig in rigs:
            row = layout.row(align=True)
            row.label(text=rig.name, icon='ARMATURE_DATA')
            # Tombol select rig di viewport
            op = row.operator("pf.select_armature", text="", icon='RESTRICT_SELECT_OFF')
            op.armature_name = rig.name


# ──────────────────────────────────────────────
#  Menu: Specials (batch actions)
# ──────────────────────────────────────────────

class PF_MT_job_specials(bpy.types.Menu):
    bl_label = "Job Specials"
    bl_idname = "PF_MT_job_specials"

    def draw(self, context):
        layout = self.layout
        layout.operator("pf.duplicate_job",   icon='DUPLICATE')
        layout.separator()
        layout.operator("pf.batch_generate",  icon='PLAY')
        layout.operator("pf.batch_delete",    icon='TRASH')
        layout.separator()
        layout.operator("pf.remove_job",      icon='REMOVE')


# ──────────────────────────────────────────────
#  Select Armature operator (helper)
# ──────────────────────────────────────────────

class PF_OT_select_armature(bpy.types.Operator):
    """Pilih armature ini di viewport"""
    bl_idname = "pf.select_armature"
    bl_label = "Select Armature"

    armature_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.armature_name)
        if obj:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        return {'FINISHED'}


CLASSES = [
    PF_UL_jobs,
    PF_PT_available_rigs,
    PF_PT_jobs,
    PF_PT_settings,
    PF_PT_generate,
    PF_MT_job_specials,
    PF_OT_select_armature,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
