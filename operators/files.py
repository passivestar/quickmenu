import bpy
from .. common.common import *

class ReimportTexturesOperator(bpy.types.Operator):
  """Reimport Textures"""
  bl_idname, bl_label, bl_options = 'qm.reimport_textures', 'Reimport Textures', {'REGISTER', 'UNDO'}

  def execute(self, context):
    for item in bpy.data.images: item.reload()
    return {'FINISHED'}

class UnpackAllDataToFilesOperator(bpy.types.Operator):
  """Unpack All Data To Files"""
  bl_idname, bl_label, bl_options = 'qm.unpack_all_data_to_files', 'Unpack All Data To Files', {'REGISTER', 'UNDO'}

  def execute(self, context):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.ops.file.unpack_all(method='WRITE_LOCAL')
    return {'FINISHED'}

def register():
    bpy.utils.register_class(ReimportTexturesOperator)
    bpy.utils.register_class(UnpackAllDataToFilesOperator)

def unregister():
    bpy.utils.unregister_class(ReimportTexturesOperator)
    bpy.utils.unregister_class(UnpackAllDataToFilesOperator)