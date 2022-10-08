import types
import json

import bpy
from bpy.types import PropertyGroup, Scene, Panel, Operator, Object, PropertyGroup
from bpy.props import BoolProperty, PointerProperty, FloatProperty, EnumProperty, StringProperty
from bpy.props import FloatVectorProperty
from bpy.utils import register_class, unregister_class

from mathutils import Vector, Quaternion

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
    use_mesh_center: BoolProperty(name='Use Mesh Center', default=True)
    use_offsets: BoolProperty(name='Use Offsets')
    collider_type: EnumProperty(items=collider_types, name='Collider Type')
    collider_is_trigger: BoolProperty(name='Is Trigger')
    offset_location: FloatVectorProperty(name='Location', subtype='TRANSLATION')
    offset_rotation: FloatVectorProperty(name='Rotation', subtype='EULER')
    offset_scale: FloatVectorProperty(name='Scale', default=(1, 1, 1), subtype='XYZ')

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

def _convert_to_y_up_vector(blender_vector, is_scale=False):
    vector = blender_vector
    if type(blender_vector) is Vector: vector = [v for v in blender_vector]

    x, old_y, old_z = vector

    y = old_z
    z = old_y * -1

    if is_scale: z *= -1

    if type(blender_vector) is Vector: return Vector([x, y, z])
    else: return [x, y, z]

def _convert_to_y_up_location(blender_vector):
    return _convert_to_y_up_vector(blender_vector)

def _convert_to_y_up_scale(blender_vector):
    return _convert_to_y_up_vector(blender_vector, is_scale=True)

def _convert_to_y_up_rotation(blender_quaternion):
    quat = blender_quaternion
    if type(blender_quaternion) is Quaternion:
        quat = [v for v in blender_quaternion]

    w, x, old_y, old_z = quat

    y = old_z
    z = old_y * -1

    if type(blender_quaternion) is Quaternion: return Quaternion([w, x, y, z])
    else: return [w, x, y, z]
    
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
        layout.use_property_split = True

        def _new_row(layout):
            row = layout.row()
            col = row.column()
            return row, col

        layout.prop(collider_props, 'is_collider')
        is_collider_enabled = True if collider_props is not None and collider_props.is_collider else False

        container_row, container_col = _new_row(layout)
        container_row.enabled = is_collider_enabled
        
        row, col = _new_row(container_col)

        col.label(text='Properties')
        col.prop(collider_props, 'collider_type')
        col.prop(collider_props, 'collider_is_trigger')
            
        row, col = _new_row(container_col)
            
        col.label(text='Export Settings')
        col.prop(collider_props, 'is_display_mesh')
        col.prop(collider_props, 'use_offsets')
            
        row, col = _new_row(container_col)
            
        col.prop(collider_props, 'use_mesh_center')
        row.enabled = True if collider_props.collider_type in ['box', 'sphere', 'capsule'] else False

        row, col = _new_row(container_col)
                
        col.label(text='Collider Offsets')
        col.prop(collider_props, 'offset_location')
        col.prop(collider_props, 'offset_rotation')
        col.prop(collider_props, 'offset_scale')
        row.enabled = collider_props.use_offsets

        row, col = _new_row(layout)

        col.label(text='Operators')
        col.operator('gltf2_omi_collider_extension.copy_properties_from_active')
        col.operator('gltf2_omi_collider_extension.check_if_hull_is_valid')
        col.operator('gltf2_omi_collider_extension.select_invalid_hull_edges')

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

class GLTF_OT_OMIColliderCopyPropertiesFromActiveOperator(Operator):

    bl_idname = 'gltf2_omi_collider_extension.copy_properties_from_active'
    bl_label = 'Copy Properties from Active'
    bl_description = 'Copy the collider properties from the active object to selected objects.'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if not _is_mesh_object_active(context): return False
        return True

    def execute(self, context):
        active_props = context.active_object.OMIColliderProperties

        selected_objs = context.selected_objects.copy()
        selected_objs.remove(context.active_object)

        for o in selected_objs:
            props = o.OMIColliderProperties

            props.is_collider = active_props.is_collider
            props.is_display_mesh = active_props.is_display_mesh
            props.use_mesh_center = active_props.use_mesh_center
            props.use_offsets = active_props.use_offsets
            props.collider_type = active_props.collider_type
            props.collider_is_trigger = active_props.collider_is_trigger

            def _copy_vector(source, target):
                for attr in ['x', 'y', 'z']: setattr(target, attr, getattr(source, attr))

            _copy_vector(active_props.offset_location, props.offset_location)
            _copy_vector(active_props.offset_rotation, props.offset_rotation)
            _copy_vector(active_props.offset_scale, props.offset_scale)
    
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return self.execute(context)
    
class glTF2ExportUserExtension:

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.extension = Extension
        self.properties = bpy.context.scene.OMIColliderExportExtensionProperties

    def _get_axis_min_and_max(self, mesh, is_y_up=False):
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

        if is_y_up:
            x_min, y_min, z_min = _convert_to_y_up_location([x_min, y_min, z_min])
            x_max, y_max, z_max = _convert_to_y_up_location([x_max, y_max, z_max])
            
        return (
            (x_min, x_max),
            (y_min, y_max),
            (z_min, z_max)
        )
        
    def _get_half_extents_for_mesh(self, mesh, is_y_up=False):
        axes = self._get_axis_min_and_max(mesh, is_y_up)
        x_axis, y_axis, z_axis = axes

        x_min, x_max = x_axis
        y_min, y_max = y_axis
        z_min, z_max = z_axis
            
        x_extent = abs(x_min - x_max) * 0.5
        y_extent = abs(y_min - y_max) * 0.5
        z_extent = abs(z_min - z_max) * 0.5
        
        return (x_extent, y_extent, z_extent)

    def _get_radius_for_mesh(self, mesh, is_y_up=False):
        extents = self._get_half_extents_for_mesh(mesh, is_y_up)
        x_extent, y_extent, z_extent = extents

        radius = x_extent if x_extent > y_extent else y_extent
        
        return radius

    def _get_height_for_mesh(self, mesh, is_y_up=False):
        axes = self._get_axis_min_and_max(mesh, is_y_up)
        x_axis, y_axis, z_axis = axes

        z_min, z_max = z_axis

        height = abs(z_min - z_max)
        
        return height

    def _get_mesh_center(self, blender_object, use_world_space=False, is_y_up=False):
        obj = blender_object

        center = (1 / len(obj.bound_box)) * sum((Vector(b) for b in obj.bound_box), Vector())
        if use_world_space: center = obj.matrix_world @ center
        if is_y_up: center = _convert_to_y_up_location(center)

        return [v for v in center]

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

        is_y_up = export_settings.get('gltf_yup', False)
        
        collider_props = blender_object.OMIColliderProperties
        collider_type = collider_props.collider_type

        extension_data['type'] = collider_type
        if collider_props.collider_is_trigger: extension_data['isTrigger'] = True

        mesh = blender_object.data

        # saved for use later in gather_gltf_extensions_hook()
        setattr(gltf2_object, '_collider_mesh', gltf2_object.mesh)
            
        if collider_type == 'box':
            gltf2_object.mesh = None
            extension_data['extents'] = self._get_half_extents_for_mesh(mesh, is_y_up)
        elif collider_type == 'sphere':
            gltf2_object.mesh = None
            extension_data['radius'] = self._get_radius_for_mesh(mesh, is_y_up)
        elif collider_type == 'capsule':
            gltf2_object.mesh = None
            extension_data['radius'] = self._get_radius_for_mesh(mesh, is_y_up)
            extension_data['height'] = self._get_height_for_mesh(mesh, is_y_up)
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

                # saved for use later in gather_gltf_extensions_hook()
                setattr(gltf2_object, '_blender_object', blender_object)
                if collider_props.is_display_mesh: setattr(gltf2_object, 'is_display_mesh', True)
                if collider_props.use_mesh_center: setattr(gltf2_object, 'use_mesh_center', True)
                if collider_props.use_offsets: setattr(gltf2_object, 'use_offsets', True)

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

    def _apply_mesh_center_to_translation(self, glTF, node, is_y_up=False):
        blender_object = node._blender_object
        collider_props = blender_object.OMIColliderProperties

        if collider_props.collider_type in ['hull', 'mesh']: return

        translation = Vector(node.translation) if node.translation is not None else Vector()
        center = Vector(self._get_mesh_center(blender_object, is_y_up=is_y_up))
        translation += center

        node.translation = [v for v in translation]

    def _apply_offsets_to_transform(self, glTF, node, is_y_up=False):
        blender_object = node._blender_object
        collider_props = blender_object.OMIColliderProperties

        offset_translation = collider_props.offset_location
        offset_rotation = collider_props.offset_rotation.to_quaternion()
        offset_scale = collider_props.offset_scale
        
        if is_y_up:
            offset_translation = _convert_to_y_up_location(offset_translation)
            offset_rotation = _convert_to_y_up_rotation(offset_rotation)
            offset_scale = _convert_to_y_up_scale(offset_scale)

        translation = Vector(node.translation) if node.translation is not None else Vector()
        scale = Vector(node.scale) if node.scale is not None else Vector([1, 1, 1])

        if node.rotation is not None:
            x, y, z, w = node.rotation
            rotation = Quaternion([w, x, y, z])
        else:
            rotation = Quaternion()
            
        translation += offset_translation
        rotation @= offset_rotation
        scale *= offset_scale

        node.translation = [v for v in translation]
        node.rotation = [rotation.x, rotation.y, rotation.z, rotation.w]
        node.scale = [v for v in scale]
        
    def gather_gltf_extensions_hook(self, glTF, export_settings):
        is_y_up = export_settings.get('gltf_yup', False)
        
        for node in glTF.nodes.copy():
            if getattr(node, 'is_display_mesh', False): self._add_display_mesh_node(glTF, node)
            if getattr(node, 'use_mesh_center', False): self._apply_mesh_center_to_translation(glTF, node, is_y_up)
            if getattr(node, 'use_offsets', False): self._apply_offsets_to_transform(glTF, node, is_y_up)

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
    GLTF_OT_OMIColliderCheckIfHullIsValidOperator,
    GLTF_OT_OMIColliderCopyPropertiesFromActiveOperator
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
