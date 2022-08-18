import bpy
from bpy.types import PropertyGroup, Scene, Panel, Operator, Object, PropertyGroup
from bpy.props import BoolProperty, PointerProperty, FloatProperty, EnumProperty, StringProperty
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

class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
        self.properties = bpy.context.scene.OMIColliderExportExtensionProperties

    def _get_axis_min_and_max(self, mesh):
        x_min, x_max = None, None
        y_min, y_max = None, None
        z_min, z_max = None, None
        
        for vertex in mesh.vertices:
            x, y, z = vertex.co

            if x_min is None: x_min = x
            if x_max is None: x_max = x

            if y_min is None: y_min = y
            if y_max is None: y_max = y

            if z_min is None: z_min = z
            if z_max is None: z_max = z
            
            if x < x_min: x_min = x
            elif x > x_max: x_max = x

            if y < y_min: y_min = y
            elif y > y_max: y_max = y

            if z < z_min: z_min = z
            elif z > z_max: z_max = z

        return (
            (x_min, x_max),
            (y_min, y_max),
            (z_min, z_max)
        )
        
    def _get_half_extents_for_mesh(self, mesh):
        axes = self._get_axis_min_and_max(mesh)
        x_axis, y_axis, z_axis = axes

        x_min, x_max = x_axis
        y_min, y_max = y_axis
        z_min, z_max = z_axis
            
        x_extent = abs(x_min - x_max) * 0.5
        y_extent = abs(y_min - y_max) * 0.5
        z_extent = abs(z_min - z_max) * 0.5
        
        return (x_extent, y_extent, z_extent)

    def _get_radius_for_mesh(self, mesh):
        extents = self._get_half_extents_for_mesh(mesh)
        x_extent, y_extent, z_extent = extents

        radius = x_extent if x_extent > y_extent else y_extent
        
        return radius

    def _get_height_for_mesh(self, mesh):
        axes = self._get_axis_min_and_max(mesh)
        x_axis, y_axis, z_axis = axes

        z_min, z_max = z_axis

        height = abs(z_min - z_max)
        
        return height
        
    def _collect_extension_data(self, gltf2_object, blender_object, export_settings):
        extension_data = {}
        
        collider_props = blender_object.OMIColliderProperties
        collider_type = collider_props.collider_type

        extension_data['type'] = collider_type
        if collider_props.collider_is_trigger: extension_data['isTrigger'] = True

        mesh = blender_object.data
        
        if collider_type == 'box':
            extension_data['extents'] = self._get_half_extents_for_mesh(mesh)
        elif collider_type == 'sphere':
            extension_data['radius'] = self._get_radius_for_mesh(mesh)
        elif collider_type == 'capsule':
            extension_data['radius'] = self._get_radius_for_mesh(mesh)
            extension_data['height'] = self._get_height_for_mesh(mesh)
        
        return extension_data
        
    def gather_node_hook(self, gltf2_object, blender_object, export_settings):
        if self.properties.enabled:
            collider_props = blender_object.OMIColliderProperties
            
            if collider_props.is_collider:
                if gltf2_object.extensions is None: gltf2_object.extensions = {}

                extension_data = self._collect_extension_data(gltf2_object, blender_object, export_settings)
                
                gltf2_object.extensions[glTF_extension_name] = self.Extension(
                    name=glTF_extension_name,
                    extension=extension_data,
                    required=extension_is_required
                )

class glTF2ImportUserExtension:

    def __init__(self):
        self.properties = bpy.context.scene.OMIColliderImportExtensionProperties
        self.extensions = [
            Extension(name="TEST_extension1", extension={}, required=True),
            Extension(name="TEST_extension2", extension={}, required=False)
        ]

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
