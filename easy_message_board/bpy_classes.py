import bpy

from bpy.props import *
from bpy.types import Operator, Panel

class EMB_PT_main_panel(Panel):
    bl_label = 'Easy Message Board'
    bl_category = "Tool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        pass

master_classes = [
    EMB_PT_main_panel
]