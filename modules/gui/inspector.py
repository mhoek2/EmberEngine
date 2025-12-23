from typing import TYPE_CHECKING

from modules.context import Context
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.console import Console
from modules.scene import SceneManager
from modules.transform import Transform
from modules.script import Script
from modules.engineTypes import EngineTypes


from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.camera import Camera
from gameObjects.skybox import Skybox

from gameObjects.attachables.physic import Physic
from gameObjects.attachables.physicLink import PhysicLink

from modules.gui.types import GameObjectTypes, RotationMode_

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

from pathlib import Path
import enum
import uuid as uid

import pybullet as p

class Inspector( Context ):
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

        self.rotation_mode = RotationMode_.radians
        self.rotation_step : dict = {
            RotationMode_.radians   :  0.01,
            RotationMode_.degrees   :  0.250,
        }

    def _transform( self ) -> None:
        gameObject  : GameObject    = self.gui.selectedObject
        _t          : Transform     = gameObject.transform

        # todo:
        # switch from local to world space editing using viewport gizmo mode?

        # local space
        if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Transform local", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()

            self.helper.draw_transform_local( _t, mask=[ 1, 1, (0 if gameObject.physic_link else 1) ] )

            imgui.tree_pop()

        # world space --should b hidden or disabled?
        #if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Transform world", imgui.TreeNodeFlags_.default_open ):
        #    self.helper.draw_transform_world( _t )
        #    imgui.tree_pop()

    def _material_thumb( self, label, texture_id ) -> None:
        imgui.text( f"{label}" );
        imgui.next_column()
        self.helper.draw_thumb( texture_id, imgui.ImVec2(75.0, 75.0) )
        imgui.next_column()

    def _material( self ) -> None:
        gameObject  : GameObject    = self.gui.selectedObject

        if not isinstance( gameObject, GameObject ):
            return

        self.helper._node_sep()

        if imgui.tree_node( f"{fa.ICON_FA_BRUSH} Material" ):
            self.helper._node_header_pad()

            _models = self.gui.models
            _images = self.gui.images
            _materials = self.gui.materials

            # collect material(s)
            materials = []

            for mesh in _models.model[gameObject.model].meshes:
                mesh_index = _models.model[gameObject.model].meshes.index(mesh)
                mesh_gl = _models.model_mesh[gameObject.model][mesh_index]
      
                if mesh_gl["material"] >= 0:
                    materials.append( mesh_gl["material"] )

            # visualize material(s)
            multi_mat : bool = True if len(materials) > 1 else False

            for material_id in materials:
                mat : Materials.Material = _materials.getMaterialByIndex( material_id )

                is_open : bool = False

                # use tree node of this mesh has multiple materials
                if multi_mat:
                    if imgui.tree_node( f"Material ID: { material_id }" ):
                        is_open = True
                else:
                    imgui.text( f"Material ID: { material_id }" );
                    imgui.separator()
                    is_open = True

                if is_open:
                    imgui.columns( count=2, borders=False )
                    imgui.set_column_width (0, 70.0 )

                    self._material_thumb( "Albedo",     mat["albedo"]   if 'albedo'     in mat else _images.defaultImage    )
                    self._material_thumb( "Normal",     mat["normal"]   if 'normal'     in mat else _images.defaultNormal   )
                    self._material_thumb( "Phyiscal",   mat["phyiscal"] if 'phyiscal'   in mat else _images.defaultRMO      )
                    self._material_thumb( "Emissive",   mat["emissive"] if 'emissive'   in mat else _images.blackImage      )
            
                    imgui.columns( count=1 )

                if multi_mat and is_open:
                    imgui.tree_pop()

            self.helper._node_sep()
            imgui.tree_pop()

    def _draw_script_exported_attributes( self, script: Script ):
        if not script.active or not script.exports:
            return 

        self.helper._node_header_pad()  

        if imgui.tree_node_ex( f"Exports##ScriptExports", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()  

            for class_attr_name, class_attr in script.exports.items():
                # at this point, the effective value 'default' or '.get()' has already been initialized (from class or scene)

                # shuldnt this be at the beginning?
                if script.instance is None:
                    continue

                # exported attribute contains error, type mismatch?
                if not class_attr.active:
                    continue

                #_instance_value = getattr(script["instance"], instance_attr_name)
                _value = class_attr.get()
                _t = class_attr.type
                _changed = False
                _t_engine_type : EngineTypes.Meta = EngineTypes.get_engine_type( _t )

                # FLOAT
                if _t is float:
                    _changed, new = imgui.drag_float(f"{class_attr_name}:", _value, 0.01)

                # INT
                elif _t is int:
                    _changed, new = imgui.drag_int(f"{class_attr_name}:", _value, 1)

                # STRING
                elif _t is str:
                    _changed, new = imgui.input_text(f"{class_attr_name}:", _value, 256)

                # BOOL
                elif _t is bool:
                    _changed, new = imgui.checkbox(f"{class_attr_name}:", _value)

                # ENGINE TYPE
                elif _t_engine_type is not None:
                    _uuid               : uid.UUID = None

                    obj     : GameObject = self.context.world.findGameObject(_value)
                    _name   : str = obj.name if obj is not None else "Select"

                    imgui.text( f"{class_attr_name} ({_t.__name__})")
                    imgui.same_line(225.0)

                    if imgui.button( f"{_name}##{class_attr_name}" ):
                        imgui.open_popup(f"##{class_attr_name}_select")


                    # dnd: receive
                    if imgui.begin_drag_drop_target():
                        payload = imgui.accept_drag_drop_payload_py_id(self.gui.dnd_payload.Type_.hierarchy)
                        if payload is not None:
                            payload_obj : GameObject = self.gui.dnd_payload.get_payload_data()
                            new = payload_obj.uuid
                            _changed = True

                        imgui.end_drag_drop_target()

                    else:
                        _changed, new = self.helper.draw_popup_gameObject(
                            f"##{class_attr_name}_select", filter=lambda obj: isinstance(obj, GameObject ))

                # Unsupported type
                else:
                    imgui.text(f"{class_attr_name}: <unsupported {_t.__name__}>")

                if _changed:
                    # engine type (uuid)
                    if _t_engine_type is not None:
                        new_obj : GameObject = self.context.world.findGameObject( new )

                        if new_obj is None:
                            self.console.error( "gameObject is invalid.")
                            return

                        # set the UUID as the experted meta value
                        class_attr.set( new )
                        
                        # get the engine type (Transform, GameObject, etc) and set reference on instance attribute
                        _ref = new_obj.getAttachable( _t_engine_type._name )
                        setattr( script.instance, class_attr_name, _ref )

                    # primitive types are a COPY
                    else:
                        class_attr.set( new )
                        setattr( script.instance, class_attr_name, new )

            imgui.tree_pop()

    def _draw_script( self, script: Script ) -> None:
        imgui.push_id( f"{script.uuid}" )
        _region = imgui.get_content_region_avail()

        if not imgui.tree_node_ex( f"{fa.ICON_FA_CODE} {script.class_name_f} (Script)##GameObjectScript", imgui.TreeNodeFlags_.default_open ):
            imgui.pop_id()
            return

        # actions
        if not self.renderer.game_runtime: 
            imgui.same_line()

            if self.helper.draw_trash_button( f"{fa.ICON_FA_TRASH}", _region.x - 20 ):
                self.gui.selectedObject.removeScript( script )

            if self.helper.draw_edit_button( f"{fa.ICON_FA_PEN_TO_SQUARE}", _region.x - 40 ):
                self.gui.text_editor.open_file( script.path )


        imgui.push_style_color(imgui.Col_.child_bg, imgui.ImVec4(0.18, 0.18, 0.18, 1.0))
        imgui.begin_child("ScriptHeader", imgui.ImVec2(0.0, 50.0) )

        if imgui.begin_table("HeaderTable", 3):
            imgui.table_setup_column("Icon", imgui.TableColumnFlags_.width_fixed, 24)
            imgui.table_setup_column("Active", imgui.TableColumnFlags_.width_fixed, 24)
            imgui.table_setup_column("Name", imgui.TableColumnFlags_.width_stretch)

            imgui.table_next_row()

            # icon
            imgui.table_set_column_index(0)
            text_size = imgui.calc_text_size( fa.ICON_FA_CODE )
            col_width = imgui.get_column_width()
            imgui.set_cursor_pos_x(
                imgui.get_cursor_pos_x() + (col_width - text_size.x) * 0.5
            )

            imgui.align_text_to_frame_padding()
            imgui.text( f"{fa.ICON_FA_CODE}" )

            # active state
            imgui.table_set_column_index(1)
            changed, active = imgui.checkbox("##active", script.active)
            if changed:
                script.active = active
                self.scene.updateScriptonGameObjects( script.path )

            # uuid
            imgui.table_set_column_index(2)
            self.helper.draw_framed_text( str(script.path) )
            imgui.text_colored( imgui.ImVec4(1.0, 1.0, 1.0, 0.6), f"uuid: { script.uuid.hex }" );

            imgui.end_table()

        imgui.end_child()
        imgui.pop_style_color()

        # script contains errors, return
        if script._error:
            imgui.text_colored( imgui.ImVec4(1.0, 0.0, 0.0, 0.9), script._error );
            imgui.tree_pop()
            imgui.pop_id()
            return

        # exported attributes
        self._draw_script_exported_attributes( script )

        imgui.tree_pop()

        imgui.pop_id()

    def _scripts( self ):
        for script in self.gui.selectedObject.scripts:
            self.helper._node_sep()
            self._draw_script( script )

    def _addAttachable( self ):
        if self.renderer.game_runtime: 
            return

        script_path = None
        attachable_type = None

        _tree_flags =   imgui.TreeNodeFlags_.default_open | \
                        imgui.TreeNodeFlags_.leaf | \
                        imgui.TreeNodeFlags_.span_full_width

        if not imgui.tree_node_ex( f"##AddAttachable", _tree_flags ):
            return

        _region_x = imgui.get_content_region_avail().x
        button_text = "Add Attachable"
        button_width = imgui.calc_text_size(button_text).x + imgui.get_style().frame_padding.x * 2
            
        offset = (_region_x - button_width ) * 0.5
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + offset)

        if imgui.button( button_text ):
            imgui.open_popup("add-attachable-popup")

        # dnd: receive
        if imgui.begin_drag_drop_target():
            is_asset = imgui.accept_drag_drop_payload_py_id(self.gui.dnd_payload.Type_.asset)
            if is_asset is not None:
                script_path = self.gui.dnd_payload.get_payload_data()

            imgui.end_drag_drop_target()

        imgui.same_line()

        if imgui.begin_popup("add-attachable-popup"):

            # todo:
            # perhaps there should be a separate thread for this
            # that either updates periodicly, or tracks changes in assets folder
            self.context.findScripts()

            # engine attachables
            attachables : list[EngineTypes.Meta] = EngineTypes.getAttachables()

            for attachable in attachables:
                imgui.push_id(f"addAttachable_{attachable._name}")
                _, clicked = imgui.selectable(
                    f"{attachable._name}", False
                )

                if clicked:
                    attachable_type = attachable

                imgui.pop_id()

            imgui.separator()

            # project assets scripts
            assets = Path( self.settings.assets ).resolve()
            for i, script in enumerate(self.context.asset_scripts):
                imgui.push_id(f"add_script_{str(script)}")
 
                name = str(script.relative_to(assets))
                _, clicked = imgui.selectable(
                    f"{name}", False
                )

                if clicked:
                    script_path = script

                imgui.pop_id()

            imgui.end_popup()

        if script_path:
            self.gui.selectedObject.addScript( 
                Script( 
                    context = self.context,
                    path    = script_path,
                    active  = True
                )   
            )

        if attachable_type:
            self.gui.selectedObject.addAttachable( attachable_type._class, attachable_type._class(
                    self.context, 
                    self.gui.selectedObject ) 
            )

        imgui.tree_pop()

    def _light( self ) -> None:
        gameObject  : GameObject    = self.gui.selectedObject

        if not isinstance( gameObject, Light ):
            return

        self.helper._node_sep()

        if imgui.tree_node_ex( f"{fa.ICON_FA_LIGHTBULB} Light", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()

            any_changed = False

            type_names = [t.name for t in Light.Type_]

            changed, new_light_index = imgui.combo(
                "Light type",
                gameObject.light_type,
                type_names
            )
            if changed:
                any_changed  = True
                gameObject.light_type = Light.Type_(new_light_index)

            changed, gameObject.light_color = imgui.color_edit3( "Light color", gameObject.light_color )
            if changed:
                any_changed  = True

            changed, gameObject.radius = imgui.drag_float( f"Radius", gameObject.radius, 0.1 )
            if changed:
                any_changed  = True

            changed, gameObject.intensity = imgui.drag_float( f"Intensity", gameObject.intensity, 0.1 )
            if changed:
                any_changed  = True

            if any_changed:
                gameObject._dirty |= GameObject.DirtyFlag_.light

            imgui.tree_pop()

    def _camera( self ) -> None:  
        gameObject  : GameObject    = self.gui.selectedObject

        if not isinstance( gameObject, Camera ):
            return

        self.helper._node_sep()

        if imgui.tree_node_ex( f"{fa.ICON_FA_CAMERA} Camera properties", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()

            changed, value = imgui.drag_float(
                f"Fov", gameObject.fov, 1
            )
            if changed:
                gameObject.fov = value

            changed, value = imgui.drag_float(
                f"Near", gameObject.near, 1
            )
            if changed:
                gameObject.near = value

            changed, value = imgui.drag_float(
                f"Far", gameObject.far, 1
            )
            if changed:
                gameObject.far = value

            imgui.tree_pop()

    def _physicProperties( self, physic_link : PhysicLink ) -> None:

        imgui.push_id("##PhysicTabs")
        _flags = imgui.TabBarFlags_.none

        if imgui.begin_tab_bar( "PhysicProperties", _flags ):
            if imgui.begin_tab_item("Inertia##Tab1")[0]:
                imgui.dummy( imgui.ImVec2(0.0, 10.0) )
                inertia : PhysicLink.Inertia = physic_link.inertia

                _, inertia.mass = imgui.drag_float("Mass", inertia.mass, 1.0)
                imgui.end_tab_item()

            if imgui.begin_tab_item("Joint##Tab2")[0]:
                imgui.dummy( imgui.ImVec2(0.0, 10.0) )
                joint : PhysicLink.Joint = physic_link.joint

                # type
                type_names = [t.name for t in PhysicLink.Joint.Type_]

                changed, new_index = imgui.combo(
                    "Joint type",
                    joint.geom_type,
                    type_names
                )
                if changed:
                    joint.geom_type = PhysicLink.Joint.Type_( new_index )

                imgui.end_tab_item()

            if imgui.begin_tab_item("Visual##Tab3")[0]:
                imgui.dummy( imgui.ImVec2(0.0, 10.0) )
                visual : PhysicLink.Visual = physic_link.visual

                #_t : Transform = visual.transform
                #self.helper.draw_transform_local( _t )

                imgui.end_tab_item()

            if imgui.begin_tab_item("Collision##Tab4")[0]:
                imgui.dummy( imgui.ImVec2(0.0, 10.0) )
                collision : PhysicLink.Collision = physic_link.collision

                # type
                geom_type_names = [t.name for t in PhysicLink.GeometryType_]

                _changed_type, type_index = imgui.combo(
                    "Geometry type",
                    collision.geom_type,
                    geom_type_names
                )
                if _changed_type:
                    collision.geom_type = PhysicLink.GeometryType_( type_index )

                    if collision.geom_type == PhysicLink.GeometryType_.sphere:
                        _t.scale = [collision.radius, collision.radius, collision.radius]

                # size based on type
                if collision.geom_type == PhysicLink.GeometryType_.sphere:
                    _changed_radius, radius = imgui.drag_float(f"Radius##CollisionShapeSize", collision.radius, 0.01)

                    if _changed_radius:
                        collision.radius = radius

                elif collision.geom_type == PhysicLink.GeometryType_.cilinder:
                    _changed_radius, radius = imgui.drag_float(f"Radius##CollisionShapeSize", collision.radius, 0.01)
                    _changed_height, height = imgui.drag_float(f"Height##CollisionShapeSize", collision.height, 0.01)

                    if _changed_radius or _changed_height:
                        collision.radius = radius
                        collision.height = height

                self.helper._node_sep()

                _t : Transform = collision.transform
                self.helper.draw_transform_local( _t, 
                    mask=[1, 1, (1 if collision.geom_type == PhysicLink.GeometryType_.box else 0)] 
                )

                #Bullet uses either:
                #lateralFriction (simple model), or
                #contactStiffness + contactDamping
                self.helper._node_sep()

                if imgui.tree_node_ex( f"Contact##PhysicContact", imgui.TreeNodeFlags_.default_open ):
                    self.helper._node_header_pad()  

                    changed, collision.lateral_friction = imgui.drag_float(
                        "Lateral Friction", collision.lateral_friction, 0.01, 0.0, 10.0
                    )

                    changed, collision.rolling_friction = imgui.drag_float(
                        "Rolling Friction", collision.rolling_friction, 0.01, 0.0, 10.0
                    )

                    changed, collision.stiffness = imgui.drag_float(
                        "Stiffness", collision.stiffness, 100.0, 0.0, 1e6
                    )

                    changed, collision.damping = imgui.drag_float(
                        "Damping", collision.damping, 10.0, 0.0, 1e5
                    )

                    imgui.tree_pop()

                imgui.end_tab_item()

            # End tab bar
            imgui.end_tab_bar()

        imgui.pop_id()
        
    def _physic( self ) -> None: 
        gameObject      : GameObject    = self.gui.selectedObject
        is_base_physic  : bool          = bool(gameObject.children)

        if Physic not in gameObject.attachables:
            return

        physic : Physic = gameObject.getAttachable(Physic)
        is_base_physic = bool(gameObject.children)

        self.helper._node_sep()

        if imgui.tree_node_ex( f"{fa.ICON_FA_PERSON_FALLING_BURST} Physics Base", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()

            # no children, meaning its just a single world physic object
            if not is_base_physic:
                self._physicProperties( physic )

            else:
                _, physic.base_mass = imgui.drag_float("Base Mass", physic.base_mass, 1.0)

                # visualize relations
                if self.context.renderer.game_running and physic.physics_id is not None:
                    imgui.separator()

                    _num_joints = p.getNumJoints( physic.physics_id )
                    imgui.text( f"Num Joints: {_num_joints}" )

                    # should match with getJointInfo() below
                    #for link in physic.links.index_to_link:
                    #    imgui.text( link.gameObject.name )

                    for i in range(_num_joints):
                        info = p.getJointInfo( physic.physics_id, i )
                        _link_index         : int = i

                        _link               : PhysicLink = physic.links.index_to_link[_link_index]
                        parent_link_index   : int = info[16]
                        _link_parent        : PhysicLink = physic.links.index_to_link[parent_link_index] if parent_link_index >= 0 else physic

                        _info = f"Link[{_link_index}] = {_link.gameObject.name} with Parent: {_link_parent.gameObject.name} | PyBullet link name: {info[12].decode()}"
                        imgui.text( _info )
                        imgui.separator()

            imgui.tree_pop()

    def _physicLink( self ) -> None:
        # inspiration:
        # https://tobas-wiki.readthedocs.io/en/latest/create_urdf/

        gameObject  : GameObject    = self.gui.selectedObject

        if PhysicLink not in gameObject.attachables:
            return

        physic_link : PhysicLink = gameObject.getAttachable(PhysicLink)

        self.helper._node_sep()

        if imgui.tree_node_ex( f"{fa.ICON_FA_PERSON_FALLING_BURST} Physic", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()

            # visualize relations
            if physic_link.runtime_base_physic:
                _base_footprint : Physic = physic_link.runtime_base_physic
                _link_index     : int = physic_link.runtime_link_index
                
                _link           : PhysicLink = _base_footprint.links.index_to_link[_link_index]
                parent_link_index   : int = -1
                if gameObject.parent and gameObject.parent.physic_link:
                    parent_link_index = gameObject.parent.physic_link.runtime_link_index

                _link_parent        : PhysicLink = _base_footprint.links.index_to_link[parent_link_index] if parent_link_index >= 0 else _base_footprint

                _info = f"Link[{_link_index}] = {_link.gameObject.name} with Parent: {_link_parent.gameObject.name}"
                imgui.text(_info)

                imgui.separator()

            self._physicProperties( physic_link )

            imgui.tree_pop()

    def render( self ) -> None:
        imgui.begin("Inspector")
  
        if not self.gui.selectedObject:
            imgui.end()
            return

        gameObject = self.gui.selectedObject
        _t_game_object = GameObjectTypes.get_gameobject_type( type(gameObject) )

        if _t_game_object and isinstance( gameObject, GameObject ):
            imgui.push_style_color(imgui.Col_.child_bg, imgui.ImVec4(0.18, 0.18, 0.18, 1.0))
            imgui.begin_child("ObjectHeader", imgui.ImVec2(0.0, 50.0) )

            if imgui.begin_table("HeaderTable", 3):
                imgui.table_setup_column("Icon", imgui.TableColumnFlags_.width_fixed, 24)
                imgui.table_setup_column("Active", imgui.TableColumnFlags_.width_fixed, 24)
                imgui.table_setup_column("Name", imgui.TableColumnFlags_.width_stretch)

                imgui.table_next_row()

                # icon
                imgui.table_set_column_index(0)
                text_size = imgui.calc_text_size( _t_game_object._icon )
                col_width = imgui.get_column_width()
                imgui.set_cursor_pos_x(
                    imgui.get_cursor_pos_x() + (col_width - text_size.x) * 0.5
                )

                imgui.align_text_to_frame_padding()
                imgui.text( f"{_t_game_object._icon}" )

                # active state
                imgui.table_set_column_index(1)
                changed, active = imgui.checkbox("##active", gameObject.active)
                if changed:
                    gameObject.active = active

                # debug
                #_, _ = imgui.checkbox( "Active Parent", gameObject.hierachyActive() )

                # name
                imgui.table_set_column_index(2)
                _, gameObject.name = imgui.input_text( "##ObjectName", gameObject.name )

                imgui.text_colored( imgui.ImVec4(1.0, 1.0, 1.0, 0.6), f"uuid: { gameObject.uuid.hex }" );

                imgui.end_table()

            imgui.end_child()
            imgui.pop_style_color()
            imgui.dummy( imgui.ImVec2(0.0, 20.0) )

            self._transform()
            self._camera()
            self._light()
            self._physic()
            self._physicLink()
            self._material()
            self._scripts()

            self.helper._node_sep()

            self._addAttachable()

        imgui.end()
        return