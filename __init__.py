bl_info = {
    "name" : "MAL Tools",
    "description" : "Simple addon for EMB",
    "author" : "hisanimations",
    "version" : (1, 0, 0),
    "blender" : (3, 5, 0),
    "location" : "View3d > TF2-Trifecta",
    "support" : "COMMUNITY",
    "category" : "Porting",
    "doc_url": "https://github.com/hisprofile/TF2-Trifecta/blob/main/README.md"
}

from .easy_message_board import register as register_emb
from .easy_message_board import unregister as unregister_emb

def register():
    #emb.register()
    register_emb()

def unregister():
    pass
    unregister_emb()