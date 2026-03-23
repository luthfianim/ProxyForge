"""
ProxyForge — Fast proxy rig generator
Blender 4.2+ Extension (bpy 5.0.x compatible)

Entry point utama: register semua modul dalam urutan yang benar.
"""

# Pastikan sub-package bisa di-import
if "bpy" in dir():
    # Reload saat development (Blender developer reload)
    import importlib
    from . import props, operators, core, ui
    importlib.reload(props)
    importlib.reload(operators)
    importlib.reload(core)
    importlib.reload(ui)

import bpy

from .props      import job_props
from .operators  import job_ops, generate_ops
from .ui         import panels


def register():
    """Register semua classes dalam urutan yang tepat:
    Props dulu → Operators → UI (panels terakhir karena butuh props dan ops)
    """
    job_props.register()
    job_ops.register()
    generate_ops.register()
    panels.register()
    print("[ProxyForge] Add-on registered — siap digunakan!")


def unregister():
    """Unregister dalam urutan terbalik."""
    panels.unregister()
    generate_ops.unregister()
    job_ops.unregister()
    job_props.unregister()
    print("[ProxyForge] Add-on unregistered")
