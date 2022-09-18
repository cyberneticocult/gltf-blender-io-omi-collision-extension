import types
import json

import bpy
from bpy.types import PropertyGroup, Scene, Panel, Operator, Object, PropertyGroup
from bpy.props import BoolProperty, PointerProperty, FloatProperty, EnumProperty, StringProperty
from bpy.utils import register_class, unregister_class

from io_scene_gltf2.io.com.gltf2_io import Node

import bmesh

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
    is_display_mesh: BoolProperty(name='Is Display Mesh')
    collider_type: EnumProperty(items=collider_types, name='Collider Type')
    collider_is_trigger: BoolProperty(name='Is Trigger')

class OMIColliderExportExtensionProperties(PropertyGroup):
    enabled: BoolProperty(
        name=bl_info['name'],
        description='Include this extension in the exported glTF file.',
        default=True
    )

class OMIColliderImportExtensionProperties(PropertyGroup):
    enabled: BoolProperty(
        name=bl_info['name'],
        description='Run this extension while importing glTF file.',
        default=True
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

def _is_mesh_object_active(context):
    objs = context.selected_objects
    return True if len(objs) > 0 and context.active_object.type == 'MESH' else False

def _is_valid_hull_mesh(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)

    is_convex = all([e.is_convex for e in bm.edges])
    is_contiguous = all([e.is_contiguous for e in bm.edges])
    is_manifold = all([e.is_manifold for e in bm.edges])
    
    bm.free()
        
    return is_convex and is_contiguous and is_manifold
    
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
            layout.prop(collider_props, 'is_display_mesh')
            layout.prop(collider_props, 'collider_type')
            layout.prop(collider_props, 'collider_is_trigger')

            layout.operator(
                'gltf2_omi_collider_extension.check_if_hull_is_valid',
                text='Check if Hull is Valid')
                
            layout.operator(
                'gltf2_omi_collider_extension.select_invalid_hull_edges',
                text='Select Invalid Hull Edges')

class GLTF_OT_OMIColliderSelectInvalidHullEdgesOperator(Operator):

    bl_idname = 'gltf2_omi_collider_extension.select_invalid_hull_edges'
    bl_label = 'Select Invalid Hull Edges'
    bl_description = 'Select edges that do not pass convextiy, manifold and contiguous tests.'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not _is_mesh_object_active(context): return False
        
        collider_props = context.active_object.OMIColliderProperties
        
        if collider_props is None: return False
        if not collider_props.is_collider: return False
        if collider_props.collider_type != 'hull': return False
        
        return True

    def execute(self, context):
        mesh = context.active_object.data

        bm = bmesh.new()
        bm.from_mesh(mesh)

        non_convex_edges = [e.index for e in bm.edges if e.is_convex is False]
        non_contiguous_edges = [e.index for e in bm.edges if e.is_contiguous is False]
        non_manifold_edges = [e.index for e in bm.edges if e.is_manifold is False]
        
        bm.free()

        invalid_edges = list(set(non_convex_edges + non_contiguous_edges + non_manifold_edges))

        def _deslect_all():
            for vertex in mesh.vertices: vertex.select = False
            for edge in mesh.edges: edge.select = False
            for polygon in mesh.polygons: polygon.select = False

        def _select_invalid_edges():
            for idx in invalid_edges: mesh.edges[idx].select = True

        _deslect_all()
        _select_invalid_edges()
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return self.execute(context)

class GLTF_OT_OMIColliderCheckIfHullIsValidOperator(Operator):

    bl_idname = 'gltf2_omi_collider_extension.check_if_hull_is_valid'
    bl_label = 'Check If Hull Is Valid'
    bl_description = 'Test if hull passes convextiy, manifold and contiguous tests.'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if not _is_mesh_object_active(context): return False

        collider_props = context.active_object.OMIColliderProperties
        
        if collider_props is None: return False
        if not collider_props.is_collider: return False
        if collider_props.collider_type != 'hull': return False
        
        return True

    def execute(self, context):
        mesh = context.active_object.data

        if not _is_valid_hull_mesh(mesh):
            self.report({'WARNING'}, 'Hull is invalid and will not export as collider.')
        else:
            self.report({'INFO'}, 'Hull is valid.')

        return {'CANCELLED'}
    
    def invoke(self, context, event):
        return self.execute(context)

class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.extension = Extension
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

    def _is_valid_hull(self, mesh): return _is_valid_hull_mesh(mesh)

    def _modify_node_json_result(self, node_result):
        mesh_id = node_result.get('mesh', None)
        
        if 'mesh' in node_result: del node_result['mesh']

        extension_omi_collider = node_result.get('extensions', {}).get(glTF_extension_name, None)
        
        if extension_omi_collider is not None and type(extension_omi_collider) is dict:
            collider_type = extension_omi_collider.get('type', None)
            
            if collider_type == 'hull' or collider_type == 'mesh':
                extension_omi_collider['mesh'] = mesh_id

        return node_result

    def _node_to_dict_wrapper(self, func, gltf2_object):

        def wrapper(*args, **kwargs):
            result = func()
            return self._modify_node_json_result(result)

        return wrapper
    
    def _collect_extension_data(self, gltf2_object, blender_object, export_settings):
        extension_data = {}
        
        collider_props = blender_object.OMIColliderProperties
        collider_type = collider_props.collider_type

        extension_data['type'] = collider_type
        if collider_props.collider_is_trigger: extension_data['isTrigger'] = True

        mesh = blender_object.data

        setattr(gltf2_object, '_collider_mesh', gltf2_object.mesh)
            
        if collider_type == 'box':
            gltf2_object.mesh = None
            extension_data['extents'] = self._get_half_extents_for_mesh(mesh)
        elif collider_type == 'sphere':
            gltf2_object.mesh = None
            extension_data['radius'] = self._get_radius_for_mesh(mesh)
        elif collider_type == 'capsule':
            gltf2_object.mesh = None
            extension_data['radius'] = self._get_radius_for_mesh(mesh)
            extension_data['height'] = self._get_height_for_mesh(mesh)
        elif collider_type == 'hull':
            if self._is_valid_hull(mesh) is not True:
                raise Exception('Mesh is not a convex hull : {}'.format(blender_object.name))
        elif collider_type == 'mesh':
            pass

        setattr(gltf2_object, 'to_dict', self._node_to_dict_wrapper(gltf2_object.to_dict, gltf2_object))
        
        return extension_data
        
    def gather_node_hook(self, gltf2_object, blender_object, export_settings):
        if self.properties.enabled:
            collider_props = blender_object.OMIColliderProperties
            
            if collider_props.is_collider:
                if gltf2_object.extensions is None: gltf2_object.extensions = {}

                extension_data = self._collect_extension_data(gltf2_object, blender_object, export_settings)
                
                gltf2_object.extensions[glTF_extension_name] = self.extension(
                    name=glTF_extension_name,
                    extension=extension_data,
                    required=extension_is_required
                )

                if collider_props.is_display_mesh: setattr(gltf2_object, 'is_display_mesh', True)

    def _add_display_mesh_node(self, glTF, node):
        node_index = glTF.nodes.index(node)

        parent_node = None        
        try: parent_node = next(n for n in glTF.nodes if node_index in n.children)
        except: pass
        
        camera = None
        children = [node_index]
        extensions = {}
        extras = None
        matrix = []
        mesh = node._collider_mesh
        name = '{}_DisplayMesh'.format(node.name)
        rotation = node.rotation
        scale = node.scale
        skin = None
        translation = node.translation
        weights = None

        node.rotation = None
        node.scale = None
        node.translation = None
        
        display_mesh_node = Node(
            camera, children, extensions, extras, matrix, mesh, name, rotation, scale,
            skin, translation, weights)

        glTF.nodes.append(display_mesh_node)
        display_mesh_node_index = glTF.nodes.index(display_mesh_node)

        def _replace_node_in_parent():
            if parent_node is not None:
                parent_node.children.remove(node_index)
                parent_node.children.append(display_mesh_node_index)

        def _replace_node_in_scenes():
            for scene in glTF.scenes:
                if node_index in scene.nodes:
                    scene.nodes.remove(node_index)
                    scene.nodes.append(display_mesh_node_index)

        _replace_node_in_parent()
        _replace_node_in_scenes()
        
    def gather_gltf_extensions_hook(self, glTF, export_settings):
        for node in glTF.nodes:
            if hasattr(node, 'is_display_mesh'): self._add_display_mesh_node(glTF, node)
                

class glTF2ImportUserExtension:

    def __init__(self):
        self.properties = bpy.context.scene.OMIColliderImportExtensionProperties
        self.extensions = [
            # Extension(name="TEST_extension1", extension={}, required=True),
            # Extension(name="TEST_extension2", extension={}, required=False)
        ]

    def gather_import_node_before_hook(self, vnode, gltf_node, import_settings):
        if self.properties.enabled:
            pass

    def gather_import_node_after_hook(self, vnode, gltf_node, blender_object, import_settings):
        if self.properties.enabled:
            pass

def glTF2_pre_export_callback(export_settings): pass

def glTF2_post_export_callback(export_settings): pass
        
addon_classes = [
    OMIColliderExportExtensionProperties,
    OMIColliderImportExtensionProperties,
    OMIColliderProperties,
    GLTF_PT_OMIColliderObjectPropertiesPanel,
    GLTF_OT_OMIColliderSelectInvalidHullEdgesOperator,
    GLTF_OT_OMIColliderCheckIfHullIsValidOperator
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
