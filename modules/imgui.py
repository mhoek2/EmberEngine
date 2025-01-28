from pickletools import read_stringnl_noescape_pair
from typing import List
from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import imgui
from pygame import Vector2

from modules.context import Context
from modules.material import Material
from modules.images import Images
from modules.models import Models
from modules.console import Console
from modules.scene import SceneManager

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.camera import Camera

from pathlib import Path
import textwrap

class ImGui( Context ):
    def __init__( self, context ):
        super().__init__( context )

        self.io = imgui.get_io()

        self.drawWireframe = False
        self.selectedObject = False
        self.selectedObjectIndex = -1

        self.initialized = False

        self.char_game_state = ["play", "stop"]
        self.color_game_state = [(0.2, 0.7, 0.2), (0.8, 0.1, 0.15)]

    def load_gui_icons( self ) -> None:
        """Load icons from game assets gui folder"""
        self.icons = {}
        self.icon_dir = Path( f"{self.settings.engine_gui_path}\\icons" ).resolve()

        if any( self.icon_dir.glob("*") ):
            for path in self.icon_dir.glob("*"):
                if path.suffix != ".png":
                    continue
                
                icon_id = path.name.replace( path.suffix, "")
                self.icons[f".{icon_id}"] = self.context.images.loadOrFindFullPath( str(path), flip_y=False )


    def initialize_context( self ) -> None:
        if self.initialized:
            return

        self.materials  : Material = self.context.materials
        self.images     : Images = self.context.images
        self.models     : Models = self.context.models

        self.scene      : SceneManager = self.context.scene

        self.file_browser_init()
        self.load_gui_icons()

        self.initialized = True

    # https://github.com/pyimgui/pyimgui/blob/9adcc0511c5ce869c39ced7a2b423aa641f3e7c6/doc/examples/integrations_glfw3_docking.py#L10
    def docking_space( self, name: str ):
        flags = (imgui.WINDOW_MENU_BAR 
        | imgui.WINDOW_NO_DOCKING 
        # | imgui.WINDOW_NO_BACKGROUND
        | imgui.WINDOW_NO_TITLE_BAR
        | imgui.WINDOW_NO_COLLAPSE
        | imgui.WINDOW_NO_RESIZE
        | imgui.WINDOW_NO_MOVE
        | imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS
        | imgui.WINDOW_NO_NAV_FOCUS
        )

        viewport = imgui.get_main_viewport()
        x, y = viewport.pos
        w, h = viewport.size
        imgui.set_next_window_position(x, y)
        imgui.set_next_window_size(w, h)
        # imgui.set_next_window_viewport(viewport.id)
        imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 0.0)
        imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 0.0)

        # When using ImGuiDockNodeFlags_PassthruCentralNode, DockSpace() will render our background and handle the pass-thru hole, so we ask Begin() to not render a background.
        # local window_flags = self.window_flags
        # if bit.band(self.dockspace_flags, ) ~= 0 then
        #     window_flags = bit.bor(window_flags, const.ImGuiWindowFlags_.NoBackground)
        # end

        # Important: note that we proceed even if Begin() returns false (aka window is collapsed).
        # This is because we want to keep our DockSpace() active. If a DockSpace() is inactive,
        # all active windows docked into it will lose their parent and become undocked.
        # We cannot preserve the docking relationship between an active window and an inactive docking, otherwise
        # any change of dockspace/settings would lead to windows being stuck in limbo and never being visible.
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
        imgui.begin(name, None, flags)
        imgui.pop_style_var()
        imgui.pop_style_var(2)

        # DockSpace
        dockspace_id = imgui.get_id(name)
        imgui.dockspace(dockspace_id, (0, 0), imgui.DOCKNODE_PASSTHRU_CENTRAL_NODE)

        imgui.end()

    def draw_menu_bar( self, frame_time, fps ) -> None:
        if imgui.begin_main_menu_bar():

            viewport = imgui.get_main_viewport()
            x, y = viewport.pos
            w, h = viewport.size  

            if imgui.begin_menu("File", True):

                # quit
                clicked_quit, _ = imgui.menu_item( "Quit", '', False, True )
                if clicked_quit:
                    self.renderer.running = False

                # save scene
                clicked_save, _ = imgui.menu_item( "Save", 'CTRL+S', False, True )
                if clicked_save:
                    self.scene.saveScene()

                # scene manager
                clicked_scene, _ = imgui.menu_item( "Scene Manager", '', False, True )
                if clicked_scene:
                    self.scene.toggleWindow()

                imgui.end_menu()

            imgui.same_line( w - 400.0 )
            state = "enabled" if not self.renderer.ImGuiInput else "disabled"
            imgui.text( f"[F1] Input { state }" );

            imgui.same_line( w - 200.0 )
            imgui.text( f"{frame_time:.3f} ms/frame ({fps:.1f} FPS)" )

            imgui.end_main_menu_bar()

    def draw_gamestate( self ):
        width = imgui.get_window_size().x / 2
        imgui.same_line( width - 50 )

        game_state = int(self.settings.game_running)
        imgui.push_style_color(imgui.COLOR_BUTTON, 
                               self.color_game_state[game_state][0], 
                               self.color_game_state[game_state][1], 
                               self.color_game_state[game_state][2]
                               )

        if imgui.button( self.char_game_state[game_state] ):
            if self.settings.game_running:
                self.settings.game_running = False
            else:
                self.settings.game_start = True
                self.settings.game_running = True

        imgui.pop_style_color(1)

    def draw_viewport( self ) -> None:

        imgui.set_next_window_size( 915, 640, imgui.FIRST_USE_EVER )

        imgui.begin( "Viewport" )

        # select render mode
        imgui.push_item_width( 150.0 );
        clicked, self.renderer.renderMode = imgui.combo(
            "##renderMode", self.renderer.renderMode, self.renderer.renderModes
        )
        imgui.pop_item_width();

        imgui.same_line()
        self.draw_gamestate()

        # resize
        size : Vector2 = imgui.get_window_size()

        bias_y = 58
        if size != self.renderer.viewport_size:
            self.renderer.viewport_size = Vector2( int(size.x), int(size.y) )
            self.renderer.setup_projection_matrix( self.renderer.viewport_size - Vector2(0, bias_y) )

        glBindTexture( GL_TEXTURE_2D, self.renderer.main_fbo["output"] )
        imgui.image( self.renderer.main_fbo["output"], self.renderer.viewport_size.x, (self.renderer.viewport_size.y - bias_y), uv0=(0, 1), uv1=(1, 0) )

        imgui.end()

    def draw_hierarchy( self ) -> None:
        imgui.begin( "Hierarchy" )

        if imgui.button( "Cube" ):
            self.context.addDefaultCube()

        imgui.same_line()

        if imgui.button( "Light" ):
            self.context.addDefaultLight()

        imgui.same_line()

        if imgui.button( "Empty" ):
            self.context.addEmptyGameObject()

        imgui.same_line()

        if imgui.button( "Camera" ):
            self.context.addDefaultCamera()


        if imgui.tree_node( "Hierarchy", imgui.TREE_NODE_DEFAULT_OPEN ):

            for n, gameObject in enumerate( self.context.gameObjects ):
                if isinstance( gameObject, GameObject ): # link class name
                    imgui.push_id( f"gameObject_{n}" )

                    clicked, _ = imgui.selectable(
                        label = gameObject.name,
                        selected = ( self.selectedObjectIndex == n )
                    )

                    if clicked:
                        self.selectedObjectIndex = n
                        self.selectedObject = self.context.gameObjects[ n ]
                    
                    imgui.pop_id()
            imgui.tree_pop()

        imgui.end()
        return

    def draw_settings( self ) -> None:
        imgui.begin( "Settings" )

        changed, self.settings.drawWireframe = imgui.checkbox( 
            "Wireframe", self.settings.drawWireframe 
        )

        imgui.separator()

        changed, self.settings.grid_color = imgui.color_edit3(
            "Grid color", *self.settings.grid_color
        )

        changed, self.settings.grid_size = imgui.drag_float(
                f"Grid size", self.settings.grid_size, 1
        )

        changed, self.settings.grid_spacing = imgui.drag_float(
                f"Grid spacing", self.settings.grid_spacing, 0.01
        )

        imgui.separator()

        changed, self.context.roughnessOverride = imgui.drag_float(
                f"Roughness override", self.context.roughnessOverride, 0.01
        )

        changed, self.context.metallicOverride = imgui.drag_float(
                f"Metallic override", self.context.metallicOverride, 0.01
        )

        imgui.end()
        return

    def draw_vec3_control( self, label, vector, resetValue = 0.0 ):

        labels = ["X", "Y", "Z"]
        label_colors = [(0.8, 0.1, 0.15), (0.2, 0.7, 0.2), (0.1, 0.25, 0.8)]

        imgui.push_id( f"{label}_vec3_control" )

        imgui.columns(count=2, identifier=None, border=False)
        imgui.set_column_width(0, 70.0)

        imgui.text( label )
        imgui.next_column()

        #imgui.push_multi_items_width(3, imgui.calc_item_width())
        width = min(125, max(40, (imgui.get_window_size().x / 3) - ( 20 * 3)))

        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (0.0, 0.0))

        for i in range( 0, 3 ):
            imgui.push_style_color(imgui.COLOR_BUTTON, label_colors[i][0], label_colors[i][1], label_colors[i][2])
            if imgui.button( labels[i] ):
                vector[i] = resetValue
            imgui.pop_style_color(1)
            imgui.same_line()
            imgui.push_item_width( width );
            changed, vector[i] = imgui.drag_float(
                f"##{labels[i]}", vector[i], 0.01
            )
            imgui.pop_item_width();

            if i < 2:
                imgui.same_line()
                imgui.dummy( 5, 5 )
                imgui.same_line()

        imgui.pop_style_var( 1 )

        imgui.columns(1)

        imgui.pop_id()
        return

    def draw_inspector_transform( self ) -> None:
        if not self.selectedObject:
            return

        gameObject = self.selectedObject

        if isinstance( gameObject, Mesh ):
            imgui.text( f"Mesh" );

        if isinstance( gameObject, Light ):
            imgui.text( f"Light" );

        if imgui.tree_node( "Transform", imgui.TREE_NODE_DEFAULT_OPEN ):

            self.draw_vec3_control( "Position", gameObject.translate, 0.0 )
            self.draw_vec3_control( "Rotation", gameObject.rotation, 0.0 )
            self.draw_vec3_control( "Scale", gameObject.scale, 0.0 )

            imgui.tree_pop()

        return

    def draw_thumb( self, image, size ):
        #glBindTexture( GL_TEXTURE_2D, image )
        imgui.image( image, size, size )

    def draw_inspector_material_thumb( self, label, texture_id ) -> None:
        imgui.text( f"{label}" );
        imgui.next_column()
        self.draw_thumb( texture_id, 75 )
        imgui.next_column()

    def draw_inspector_material( self ) -> None:
        if imgui.tree_node( "Material" ):

            if not self.selectedObject:
                imgui.tree_pop()
                return

            gameObject = self.selectedObject

            if not isinstance( gameObject, GameObject ):
                imgui.tree_pop()
                return

            # collect material(s)
            materials = []

            for mesh in self.models.model[gameObject.model].meshes:
                mesh_index = self.models.model[gameObject.model].meshes.index(mesh)
                mesh_gl = self.models.model_mesh[gameObject.model][mesh_index]
      
                if mesh_gl["material"] >= 0:
                    materials.append( mesh_gl["material"] )

            # visualize material(s)
            multi_mat : bool = True if len(materials) > 1 else False

            for material_id in materials:
                mat = self.materials.getMaterialByIndex( material_id )

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
                    imgui.columns( count=2, identifier=None, border=False )
                    imgui.set_column_width (0, 70.0 )

                    self.draw_inspector_material_thumb( "Albedo", mat["albedo"] if 'albedo' in mat else self.images.defaultImage )
                    self.draw_inspector_material_thumb( "Normal", mat["normal"] if 'normal' in mat else self.images.defaultNormal )
                    self.draw_inspector_material_thumb( "Phyiscal", mat["phyiscal"] if 'phyiscal' in mat else self.images.defaultRMO )
                    self.draw_inspector_material_thumb( "Emissive", mat["emissive"] if 'emissive' in mat else self.images.blackImage )
            
                    imgui.columns(1)

                if multi_mat and is_open:
                    imgui.tree_pop()

            imgui.tree_pop()
        return

    def draw_popup_gameObject( self, id : str, filter = None ):
        selected = -1
        clicked = False

        if imgui.begin_popup("select-camera"):

            _, clicked = imgui.selectable(
                f"None##object_-1", clicked
            )

            if clicked:
                imgui.end_popup()
                return True, -1

            for i, obj in enumerate(self.context.gameObjects):
                if filter is not None and not filter(obj):
                    continue

                _, clicked = imgui.selectable(
                    f"{obj.name}##object_{i}", clicked
                )

                if clicked:
                    selected = i
                    break;

            imgui.end_popup()

        return clicked, selected

    def draw_environment( self ) -> None:
        imgui.begin( "Environment" )

        imgui.text("camera")
        imgui.same_line(100.0)

        camera : GameObject = self.scene.getCamera()
        _scene_camera_name : str = camera.name if camera else "None" 

        if imgui.button( _scene_camera_name ):
            imgui.open_popup("select-camera")

        imgui.same_line()
        changed_camera_gameobject, _changed_id = self.draw_popup_gameObject(
            "select-camera", filter=lambda obj: isinstance(obj, Camera ))

        if changed_camera_gameobject:
            print(_changed_id)
            self.scene.scenes[self.scene.current_scene]["camera"] = _changed_id

        imgui.separator()

        changed, self.context.light_color = imgui.color_edit3(
            "Light color", *self.context.light_color
        )

        changed, self.context.ambient_color = imgui.color_edit3(
            "Ambient color", *self.context.ambient_color
        )

        imgui.end()
        return

    # combo example
    #selected = 0
    #items = self.context.asset_scripts
    #
    #if imgui.begin_combo("combo", items[selected]):
    #    for i, item in enumerate(items):
    #        is_selected = (i == selected)
    #        if imgui.selectable(item, is_selected)[0]:
    #            selected = i
    #        
    #        # Set the initial focus when opening the combo (scrolling + keyboard navigation focus)                    
    #        if is_selected:
    #            imgui.set_item_default_focus()
    #
    #    imgui.end_combo()

    def draw_inspector_scripts( self ):
        if imgui.tree_node( "Scripts", imgui.TREE_NODE_DEFAULT_OPEN ):
            assets = Path( self.settings.assets ).resolve()
            _shift_left = 20.0
            _region = imgui.get_content_region_available()
            _region = imgui.Vec2(_region.x + _shift_left, _region.y)

            i = -1
            for i, script in enumerate(self.selectedObject.scripts):
                imgui.push_id(f"draw_script_{str(script['file'])}")

                name = str(script['file'].relative_to(assets))

                draw_list = imgui.get_window_draw_list() 
                draw_list.channels_split(2)
                draw_list.channels_set_current(1)

                p_min = imgui.get_cursor_screen_pos()
                p_min = imgui.Vec2( (p_min.x-_shift_left), p_min.y)
                imgui.set_cursor_screen_pos(p_min)
                
                imgui.begin_group()

                imgui.text(name) # should become the Class name
                imgui.same_line( _region.x - 15 )
                if not self.settings.game_running and imgui.button("x"):
                    self.selectedObject.removeScript( script['file'] )

                #imgui.input_text( label="File##ScriptName", flags=imgui.INPUT_TEXT_READ_ONLY, value=name)

                imgui.end_group()
                _group_height = imgui.get_item_rect_size().y

                # background rect
                _header_height = 20
                p_max = imgui.Vec2( p_min.x + _region.x, p_min.y + _group_height)

                draw_list.channels_set_current(0)
                draw_list.add_rect_filled(p_min.x, p_min.y, p_max.x, (p_min.y + _header_height), imgui.get_color_u32_rgba(1, 1, 1, 0.2))
                draw_list.add_rect_filled(p_min.x, p_min.y + _header_height, p_max.x, p_max.y, imgui.get_color_u32_rgba(1, 1, 1, 0.1))
                draw_list.channels_merge()
   
                imgui.pop_id()

            if i == -1:
                imgui.text("No scripts attached")

            imgui.tree_pop()

    def draw_inspector_add_script( self ):
        path = False
        
        _region = imgui.get_content_region_available()
        pos = imgui.get_cursor_screen_pos()
        pos = imgui.Vec2( pos.x + (_region.x / 2) - 50, pos.y + _region.y - 20)
        imgui.set_cursor_screen_pos(pos)

        if imgui.button("Add Script"):
            imgui.open_popup("add-script")

        imgui.same_line()

        if imgui.begin_popup("add-script"):

            # todo:
            # perhaps there should be a separate thread for this
            # that either updates periodicly, or tracks changes in assets folder
            self.context.findScripts()

            # project assets
            assets = Path( self.settings.assets ).resolve()
            for i, script in enumerate(self.context.asset_scripts):
                imgui.push_id(f"add_script_{str(script)}")
                clicked = False

                name = str(script.relative_to(assets))
                _, clicked = imgui.selectable(
                    f"{name}", clicked
                )

                if clicked:
                    path = script

                imgui.pop_id()

            # engine assets not supported yet
            # ..

            imgui.end_popup()

        if path:
            self.selectedObject.addScript( path )

    def draw_inspector( self ) -> None:
        imgui.begin( "Inspector" )

        if not self.selectedObject:
            imgui.end()
            return

        gameObject = self.selectedObject

        if isinstance( gameObject, GameObject ):
            #imgui.text( f"{ gameObject.name }" );
                
            changed, gameObject.name = imgui.input_text(
                label="Name##ObjectName", value=gameObject.name, buffer_length=400
            )

            # components
            self.draw_inspector_transform()
            imgui.separator()
            self.draw_inspector_material()
            imgui.separator()
            self.draw_inspector_scripts()

            if not self.settings.game_running:
                self.draw_inspector_add_script()

        imgui.end()
        return

    #
    # asset explorer
    #
    def open_file( self, path ) -> None:
        if path.suffix == ".fbx" or path.suffix == ".obj":
            game_object_name = path.name.replace(path.suffix, "")
            self.context.addGameObject( 
                    Mesh( self.context,
                    name        = game_object_name,
                    model_file  = str( path ),
                    translate   = [ 0, 0, 0 ],
                    scale       = [ 1, 1, 1 ],
                    rotation    = [ 0.0, 0.0, 0.0 ]
            ) )

    def file_browser_rootpath( self ) -> Path:
        return Path( self.settings.assets ).resolve()

    def file_browser_init( self ):
        self._file_browser_dir = self.file_browser_rootpath()
        self.icon_dim = 75.0

    def get_file_browser_item_icon( self, path ) -> None:
        icon = self.icons['.unknown']

        if path.is_file() and path.suffix in self.icons:
            icon = self.icons[path.suffix]

        if path.is_dir() and ".folder" in self.icons:
            icon = self.icons['.folder']

        return icon

    def set_file_browser_path( self, path ) -> None:
        self._file_browser_dir = path

    def file_browser_go_back( self ) -> None:
        path = self._file_browser_dir.parent
        self.set_file_browser_path( path )

    def draw_file_browser_item( self, path ):
        imgui.push_style_color(imgui.COLOR_BUTTON,          1.0, 1.0, 1.0, 0.0 ) 
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED,  1.0, 1.0, 1.0, 0.1 ) 
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE,   1.0, 1.0, 1.0, 0.2 ) 
               
        icon = self.get_file_browser_item_icon( path )
        if imgui.image_button( icon, self.icon_dim, self.icon_dim):
            if path.is_file():
                self.open_file( path )

            elif path.is_dir():
                self.set_file_browser_path( path )
        
        hovered : bool = imgui.is_item_hovered()

        draw_list = imgui.get_window_draw_list()  # Get the draw list for the current window
        button_size = imgui.get_item_rect_size()
        button_pos = imgui.get_item_rect_max()
        #window_pos = imgui.get_window_position()

        # Get path name and text wrap centered
        path_name = textwrap.fill( str(path.name), width=10 )
        text_size = imgui.calc_text_size( path_name )

        alpha = 1.0 if hovered else 0.7

        draw_list.add_text( 
            (button_pos.x - button_size.x) + (button_size.x - text_size.x) * 0.5 , 
            button_pos.y, 
            imgui.get_color_u32_rgba( 1.0, 1.0, 1.0, alpha ), 
            path_name )

        imgui.pop_style_color(3)

    def draw_file_browser( self ) -> None:
        imgui.begin( "Project Assets" )

        imgui.text( str(self._file_browser_dir) )

        if self._file_browser_dir != self.file_browser_rootpath():
            if imgui.button( "Page up ^" ):
                self.file_browser_go_back()

        if any( self._file_browser_dir.glob("*") ):
            row_width = 0
            for i, path in enumerate(self._file_browser_dir.glob("*")):
                imgui.push_id( str(path.name) )

                # wrapping
                if i > 0 and ( row_width + self.icon_dim ) < imgui.get_window_size().x:
                    imgui.same_line()
                elif i > 0:
                    row_width = 0
                    imgui.dummy(0, 35)


                row_width += (self.icon_dim + 18.0)
                
                self.draw_file_browser_item( path )

                imgui.pop_id()

        imgui.dummy(0, 50)
        imgui.end()
       
    def draw_console_entry( self, i, entry : Console.Entry ):
        imgui.push_id( f"exception_{i}" )
   
        _line_height = 17
        _region = imgui.get_content_region_available()
        _color = self.console.entry_type_color[entry["type_id"]]

        # header background
        draw_list = imgui.get_window_draw_list() 
        p_min = imgui.get_cursor_screen_pos()
        p_max = imgui.Vec2( p_min.x + _region.x, p_min.y + _line_height)
        draw_list.add_rect_filled(p_min.x, p_min.y, p_max.x, p_max.y, imgui.get_color_u32_rgba(_color[0], _color[1], _color[2], 0.2))
        
        # header hover background
        imgui.push_style_color(imgui.COLOR_HEADER_HOVERED, _color[0], _color[1], _color[2], 0.4 ) 

        if imgui.tree_node( f"{ entry['message'] }" ):
            # content background
            _h_cor_bias = 4 # imgui.STYLE_ITEM_SPACING
            p_min = imgui.Vec2(p_min.x, p_max.y)
            _height = (_line_height * entry["_n_lines"]) - _h_cor_bias
            p_max = imgui.Vec2(p_max.x, p_min.y + _height)
            draw_list.add_rect_filled(p_min.x, p_min.y, p_max.x, p_max.y, imgui.get_color_u32_rgba(_color[0], _color[1], _color[2], 0.1))

            for tb in entry["traceback"]:
                imgui.text( f"{tb}" )

            imgui.tree_pop()

        imgui.pop_style_color(1)
        imgui.pop_id()

    def draw_console( self ):
        imgui.begin( "Console" )
        entries : List[Console.Entry] = self.console.getEntries()

        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (0.0, 6.0))

        for i, entry in enumerate(entries):
            self.draw_console_entry( i, entry )

        imgui.pop_style_var(1)
        imgui.end()

    def draw_scene_manager(self ):
        if not self.scene._window_is_open:
            return

        _, self.scene._window_is_open = imgui.begin( "Scene Manager", closable=True )

        if imgui.button( "Save scene" ):
            self.scene.saveScene()

        imgui.end()

    def render( self ):
        # init
        self.initialize_context()

        # global
        frame_time = 1000.0 / self.io.framerate
        fps = self.io.framerate

        self.docking_space('docking_space')
        
        self.draw_menu_bar( frame_time, fps )

        # windows
        self.draw_viewport()
        self.draw_file_browser()
        self.draw_hierarchy()
        self.draw_settings()
        self.draw_inspector()
        self.draw_environment()
        self.draw_console()
        self.draw_scene_manager()
