import bpy
from bpy.types import PropertyGroup, Scene, Panel
from bpy.props import BoolProperty, PointerProperty, FloatProperty
from bpy.utils import register_class, unregister_class

bl_info = {
    'name': 'OMI_collider glTF Extension',
    'category': 'Generic',
    "version": (1, 0, 0),
    'blender': (2, 80, 0),
    'location': 'File > Import-Export > glTF 2.0',
    'description': 'glTF extension to support the addition of colliders to glTF scenes.',
    'tracker_url': 'https://github.com/cyberneticocult/gltf-blender-io-omi-collision-extension/issues',
    'isDraft': False,
    'developer': 'cyberneticocult',
    'url': 'https://github.com/cyberneticocult'
}

glTF_extension_name = 'OMI_collider'

extension_is_required = False

class OMIColliderExportExtensionProperties(PropertyGroup):
    enabled: BoolProperty(
        name=bl_info['name'],
        description='Include this extension in the exported glTF file.',
        default=True
    )

    float_property: FloatProperty(
        name='Test FloatProperty',
        description='Testing a float property...',
        default=2.0
    )

class OMIColliderImportExtensionProperties(PropertyGroup):
    enabled: BoolProperty(
        name=bl_info['name'],
        description='Run this extension while importing glTF file.',
        default=True
    )
    
    float_property: FloatProperty(
        name='Test FloatProperty',
        description='Testing a float property...',
        default=1.0
    )

class GLTF_PT_OMIColliderExportExtensionPanel(Panel):

    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Enabled"
    bl_parent_id = "GLTF_PT_export_user_extensions"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == 'EXPORT_SCENE_OT_gltf'

    def draw_header(self, context):
        props = bpy.context.scene.OMIColliderExportExtensionProperties
        self.layout.prop(props, 'enabled')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = bpy.context.scene.OMIColliderExportExtensionProperties
        layout.active = props.enabled

        box = layout.box()
        box.label(text=glTF_extension_name)

        props = bpy.context.scene.OMIColliderExportExtensionProperties
        layout.prop(props, 'float_property', text='test float value')

class GLTF_PT_OMIColliderImportExtensionPanel(Panel):

    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Enabled"
    bl_parent_id = "GLTF_PT_import_user_extensions"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        props = bpy.context.scene.OMIColliderImportExtensionProperties
        self.layout.prop(props, 'enabled')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = bpy.context.scene.OMIColliderImportExtensionProperties
        layout.active = props.enabled

        box = layout.box()
        box.label(text=glTF_extension_name)

        layout.prop(props, 'float_property', text="test float value")
        
class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
        self.properties = bpy.context.scene.OMIColliderExportExtensionProperties

    def gather_node_hook(self, gltf2_object, blender_object, export_settings):
        if self.properties.enabled: pass

class glTF2ImportUserExtension:

    def __init__(self):
        self.properties = bpy.context.scene.OMIColliderImportExtensionProperties
        self.extensions = [Extension(name="TEST_extension1", extension={}, required=True), Extension(name="TEST_extension2", extension={}, required=False)]

    def gather_import_node_before_hook(self, vnode, gltf_node, import_settings):
        if self.properties.enabled:
            pass

    def gather_import_node_after_hook(self, vnode, gltf_node, blender_object, import_settings):
        if self.properties.enabled:
            pass
        
def register_panel():
    try: register_class(GLTF_PT_OMIColliderExportExtensionPanel)
    except Exception: pass

    try: register_class(GLTF_PT_OMIColliderImportExtensionPanel)
    except Exception: pass
    
    return unregister_panel

def unregister_panel():
    try: unregister_class(GLTF_PT_OMIColliderExportExtensionPanel)
    except Exception: pass

    try: unregister_class(GLTF_PT_OMIColliderImportExtensionPanel)
    except Exception: pass    

def register():
    register_class(OMIColliderExportExtensionProperties)
    Scene.OMIColliderExportExtensionProperties = PointerProperty(type=OMIColliderExportExtensionProperties)

    register_class(OMIColliderImportExtensionProperties)
    Scene.OMIColliderImportExtensionProperties = PointerProperty(type=OMIColliderImportExtensionProperties)

def unregister():
    unregister_panel()
    
    unregister_class(OMIColliderExportExtensionProperties)
    del Scene.OMIColliderExportExtensionProperties

    unregister_class(OMIColliderImportExtensionProperties)
    del Scene.OMIColliderImportExtensionProperties
