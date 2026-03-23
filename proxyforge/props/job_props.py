"""
props/job_props.py
Semua PropertyGroup untuk ProxyForge — disimpan di bpy.types.Scene
"""

import bpy


# ─────────────────────────────────────────────
#  Protected / Skip Datablock entry
# ─────────────────────────────────────────────

class PF_ProtectedEntry(bpy.types.PropertyGroup):
    """Satu entri datablock yang di-protect atau di-skip."""

    block_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('OBJECT',     "Object",     "Protect a single object"),
            ('COLLECTION', "Collection", "Protect all objects in a collection"),
            ('BONE',       "Bone",       "Protect objects under this bone (Split only)"),
        ],
        default='OBJECT',
    )
    # Pointer ke object (diisi kalau block_type == OBJECT)
    target_object: bpy.props.PointerProperty(
        name="Object",
        type=bpy.types.Object,
    )
    # Pointer ke collection
    target_collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
    )
    # Nama bone (string, bukan pointer — lebih stabil lintas session)
    target_bone: bpy.props.StringProperty(
        name="Bone",
        default="",
    )
    # Vertex group name (opsional, Split only)
    vertex_group: bpy.props.StringProperty(
        name="Vertex Group",
        default="",
    )
    # True = skip (exclude), False = protect (duplicate apa adanya)
    is_skip: bpy.props.BoolProperty(
        name="Skip",
        default=False,
    )


# ─────────────────────────────────────────────
#  Per-relationship settings
# ─────────────────────────────────────────────

class PF_RelationshipSettings(bpy.types.PropertyGroup):
    """Settings decimation khusus per variant relationship."""

    use_custom_decimate: bpy.props.BoolProperty(
        name="Custom Decimate",
        description="Override general decimate settings for this relationship",
        default=False,
    )
    ratio: bpy.props.FloatProperty(
        name="Ratio",
        description="Decimate ratio (1.0 = no change, 0.1 = 10% polys left)",
        default=0.15,
        min=0.001,
        max=1.0,
        subtype='FACTOR',
    )
    method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('COLLAPSE',  "Collapse",       "Collapse vertices (general purpose)"),
            ('UNSUBDIV',  "Un-Subdivide",   "Remove subdivision levels (clean topology)"),
        ],
        default='COLLAPSE',
    )


# ─────────────────────────────────────────────
#  Main Proxy Job
# ─────────────────────────────────────────────

class PF_JobProperties(bpy.types.PropertyGroup):
    """
    Satu Proxy Job = satu rig + semua settings-nya.
    Disimpan sebagai CollectionProperty di scene.
    """

    # ── Identitas ──────────────────────────────
    name: bpy.props.StringProperty(
        name="Job Name",
        default="Proxy Job",
    )

    # ── Source ─────────────────────────────────
    source_rig: bpy.props.PointerProperty(
        name="Source Rig",
        description="Armature yang akan dibuatkan proxy-nya",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )

    # ── Algoritma ──────────────────────────────
    algorithm: bpy.props.EnumProperty(
        name="Algorithm",
        description="Cara ProxyForge memproses mesh",
        items=[
            ('DECIMATE', "Decimate",
             "Kurangi jumlah polygon — cocok untuk semua mesh"),
            ('SPLIT',    "Split",
             "Pecah mesh per-bone — cocok untuk rig modular"),
        ],
        default='DECIMATE',
    )

    # ── Tampilan collection ─────────────────────
    collection_color: bpy.props.EnumProperty(
        name="Color Tag",
        description="Warna collection di Outliner",
        items=[
            ('NONE',      "None",   "", 'OUTLINER_COLLECTION', 0),
            ('COLOR_01',  "Red",    "", 'COLLECTION_COLOR_01', 1),
            ('COLOR_02',  "Orange", "", 'COLLECTION_COLOR_02', 2),
            ('COLOR_03',  "Yellow", "", 'COLLECTION_COLOR_03', 3),
            ('COLOR_04',  "Green",  "", 'COLLECTION_COLOR_04', 4),
            ('COLOR_05',  "Blue",   "", 'COLLECTION_COLOR_05', 5),
            ('COLOR_06',  "Violet", "", 'COLLECTION_COLOR_06', 6),
            ('COLOR_07',  "Pink",   "", 'COLLECTION_COLOR_07', 7),
            ('COLOR_08',  "Brown",  "", 'COLLECTION_COLOR_08', 8),
        ],
        default='NONE',
    )

    # ── Relationship toggles ────────────────────
    include_armature_deformed: bpy.props.BoolProperty(
        name="Armature Deformed",
        description="Sertakan mesh yang di-deform langsung oleh armature",
        default=True,
    )
    include_non_deformed: bpy.props.BoolProperty(
        name="Non-Deformed",
        description="Sertakan mesh yang tidak di-deform (parented saja)",
        default=True,
    )
    include_constrained: bpy.props.BoolProperty(
        name="Constrained",
        description="Sertakan mesh yang punya constraint ke rig ini",
        default=True,
    )
    include_driven: bpy.props.BoolProperty(
        name="Driven",
        description="Sertakan mesh dengan driver yang mereferensi rig ini",
        default=False,
    )

    # ── Decimate settings ──────────────────────
    decimate_ratio: bpy.props.FloatProperty(
        name="Ratio",
        description="Sisa polygon setelah decimation (0.1 = 10% dari aslinya)",
        default=0.1,
        min=0.001,
        max=1.0,
        subtype='FACTOR',
    )
    decimate_method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('COLLAPSE', "Collapse",     "Collapse vertex — general purpose"),
            ('UNSUBDIV', "Un-Subdivide", "Hapus level subdivisi"),
        ],
        default='COLLAPSE',
    )
    join_siblings: bpy.props.BoolProperty(
        name="Join Siblings",
        description="Gabungkan objek sibling sebelum decimation (lebih sedikit objects di collection)",
        default=False,
    )

    # Per-relationship custom decimate
    custom_armature_deformed: bpy.props.PointerProperty(type=PF_RelationshipSettings)
    custom_non_deformed:      bpy.props.PointerProperty(type=PF_RelationshipSettings)
    custom_constrained:       bpy.props.PointerProperty(type=PF_RelationshipSettings)
    custom_driven:            bpy.props.PointerProperty(type=PF_RelationshipSettings)

    # ── Post-generation options ─────────────────
    link_rig_to_proxy: bpy.props.BoolProperty(
        name="Link Rig to Proxy Collection",
        description="Instance source rig ke dalam proxy collection setelah generate",
        default=False,
    )
    disable_in_renders: bpy.props.BoolProperty(
        name="Disable in Renders",
        description="Sembunyikan proxy collection dari render setelah generate",
        default=True,
    )

    # ── Split algorithm extras ──────────────────
    split_show_overlays: bpy.props.BoolProperty(
        name="Show Overlays",
        description="Aktifkan overlay viewport setelah generate (Split only)",
        default=True,
    )
    split_show_outline: bpy.props.BoolProperty(
        name="Show Outline",
        description="Tampilkan outline pada proxy objects (Split only)",
        default=False,
    )
    dup_non_mesh: bpy.props.BoolProperty(
        name="Duplicate Non-Mesh",
        description="Duplikat objek non-mesh (curves, empties, lights) ke sub-collection",
        default=False,
    )
    convert_surface_deform: bpy.props.BoolProperty(
        name="Convert Surface Deform",
        description="Coba konversi Surface Deform modifier ke Armature Deform",
        default=False,
    )

    # ── Protected / Skip datablocks ─────────────
    protected_blocks: bpy.props.CollectionProperty(
        type=PF_ProtectedEntry,
        name="Protected Datablocks",
    )
    active_protected_index: bpy.props.IntProperty(default=0)

    # ── State tracking ─────────────────────────
    is_generated: bpy.props.BoolProperty(
        name="Is Generated",
        default=False,
    )
    used_algorithm: bpy.props.StringProperty(
        name="Used Algorithm",
        default="",
    )
    # Nama collection yang dibuat (untuk tracking & delete)
    proxy_collection_name: bpy.props.StringProperty(
        name="Proxy Collection Name",
        default="",
    )
    # Visibility state saat ini
    visibility_state: bpy.props.EnumProperty(
        name="Visibility State",
        items=[
            ('SOURCE', "Source", "Source rig visible"),
            ('PROXY',  "Proxy",  "Proxy collection visible"),
            ('MIXED',  "Mixed",  "Both visible"),
        ],
        default='SOURCE',
    )
    # Batch mark
    is_batch_marked: bpy.props.BoolProperty(
        name="Include in Batch",
        description="Ikutkan job ini dalam operasi Batch Generate / Delete",
        default=True,
    )


# ─────────────────────────────────────────────
#  Scene-level container
# ─────────────────────────────────────────────

class PF_SceneProperties(bpy.types.PropertyGroup):
    """Root PropertyGroup yang ditempel ke bpy.types.Scene."""

    jobs: bpy.props.CollectionProperty(
        type=PF_JobProperties,
        name="Proxy Jobs",
    )
    active_job_index: bpy.props.IntProperty(
        name="Active Job",
        default=0,
    )


# ─────────────────────────────────────────────
#  Register
# ─────────────────────────────────────────────

CLASSES = [
    PF_ProtectedEntry,
    PF_RelationshipSettings,
    PF_JobProperties,
    PF_SceneProperties,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.proxyforge = bpy.props.PointerProperty(type=PF_SceneProperties)


def unregister():
    del bpy.types.Scene.proxyforge
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
