import bpy
from bpy.types import PropertyGroup, Scene, Panel, Operator, Object, PropertyGroup
from bpy.props import BoolProperty, PointerProperty, FloatProperty, EnumProperty
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

collider_types = [
    ('box', 'Box', ''),
    ('sphere', 'Sphere', ''),
    ('capsule', 'Capsule', ''),
    ('hull', 'Hull', ''),
    ('mesh', 'Mesh', ''),
    ('compound', 'Compound', '')
]

# collider_properties_name = 'gltf2_omi_collider_properties'
# collider_properties_defaults = dict(collider_type=collider_types[0], collider_istrigger=0)

class OMIColliderProperties(PropertyGroup):
    is_collider: BoolProperty(name='Is Collider')
    collider_type: EnumProperty(items=collider_types, name='Collider Type')
    collider_is_trigger: BoolProperty(name='Is Trigger')

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

def _is_mesh_object_active(context):
    objs = context.selected_objects
    return True if len(objs) > 0 and context.active_object.type == 'MESH' else False
    
class GLTF_PT_OMIColliderObjectPropertiesPanel(Panel):

    bl_label = 'glTF OMI_collider Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1001 # order the addon properties to last

    @classmethod
    def poll(cls, context):
        return True if _is_mesh_object_active(context) else None

    def draw(self, context):
        active_obj = context.active_object
        collider_props = active_obj.OMIColliderProperties
        
        layout = self.layout

        layout.prop(collider_props, 'is_collider')
        
        if collider_props is not None and collider_props.is_collider:
            layout.prop(collider_props, 'collider_type')
            layout.prop(collider_props, 'collider_is_trigger')

# class GLTF_OT_OMIColliderAddProperties(Operator):

#     bl_idname = 'gltf2_omi_collider_extension.add_properties'
#     bl_label = 'Add OMI_Collider Properties'
#     bl_description = 'Add the properties describing the collider to the object.'
#     bl_options = {'REGISTER', 'UNDO'}

#     @classmethod
#     def poll(cls, context):
#         return True if _is_mesh_object_active(context) else None

#     def execute(self, context):
#         active_obj = context.active_object
#         collider_props = active_obj.get(collider_properties_name, None)

#         if collider_props is None:
#             active_obj[collider_properties_name] = collider_properties_defaults.copy()
        
#         return {'FINISHED'}
    
#     def invoke(self, context, event):
#         return self.execute(context)

class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
        self.properties = bpy.context.scene.OMIColliderExportExtensionProperties

    def gather_node_hook(self, gltf2_object, blender_object, export_settings):
        if self.properties.enabled:
            if gltf2_object.extensions is None: gltf2_object.extensions = {}

            gltf2_object.extensions[glTF_extension_name] = self.Extension(
                name=glTF_extension_name,
                extension={'float': self.properties.float_property},
                required=extension_is_required
            )

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

addon_classes = [
    OMIColliderExportExtensionProperties,
    OMIColliderImportExtensionProperties,
    OMIColliderProperties,
    GLTF_OT_OMIColliderAddProperties,
    GLTF_PT_OMIColliderObjectPropertiesPanel
]

extension_panel_classes = [
    GLTF_PT_OMIColliderExportExtensionPanel,
    GLTF_PT_OMIColliderImportExtensionPanel    
]

def unregister_panel():
    for cls in extension_panel_classes: unregister_class(cls)

def register_panel():
    for cls in extension_panel_classes: register_class(cls)
    return unregister_panel
    
def register():
    for cls in addon_classes: register_class(cls)
    
    Scene.OMIColliderExportExtensionProperties = PointerProperty(type=OMIColliderExportExtensionProperties)
    Scene.OMIColliderImportExtensionProperties = PointerProperty(type=OMIColliderImportExtensionProperties)

    Object.OMIColliderProperties = PointerProperty(type=OMIColliderProperties)

def unregister():
    for cls in reversed(addon_classes): unregister_class(cls)

    del Scene.OMIColliderExportExtensionProperties
    del Scene.OMIColliderImportExtensionProperties

    del Object.OMIColliderProperties
