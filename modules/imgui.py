from pickletools import read_stringnl_noescape_pair
from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import imgui
from pygame import Vector2

from modules.context import Context
from modules.material import Material
from modules.images import Images
from modules.models import Models

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun

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

                clicked_quit, selected_quit = imgui.menu_item(
                    "Quit", 'Cmd+Q', False, True
                )

                if clicked_quit:
                    self.renderer.running = False

                imgui.end_menu()

            imgui.same_line( w - 400.0 )
            state = "enabled" if not self.renderer.ImGuiInput else "disabled"
            imgui.text( f"[F1] Input { state }" );

            imgui.same_line( w - 200.0 )
            imgui.text( f"{frame_time:.3f} ms/frame ({fps:.1f} FPS)" )

            imgui.end_main_menu_bar()

    def draw_viewport( self ) -> None:

        imgui.set_next_window_size( 915, 640, imgui.FIRST_USE_EVER )

        imgui.begin( "Viewport" )

        # select render mode
        imgui.push_item_width( 150.0 );
        clicked, self.renderer.renderMode = imgui.combo(
            "##renderMode", self.renderer.renderMode, self.renderer.renderModes
        )
        imgui.pop_item_width();

        # resize
        size : Vector2 = imgui.get_window_size()

        if size != self.renderer.viewport_size:
            self.renderer.viewport_size = Vector2( int(size.x), int(size.y) )
            self.renderer.setup_projection_matrix( self.renderer.viewport_size )

        glBindTexture( GL_TEXTURE_2D, self.renderer.main_fbo["output"] )
        imgui.image( self.renderer.main_fbo["output"], self.renderer.viewport_size.x, self.renderer.viewport_size.y, uv0=(0, 1), uv1=(1, 0) )

        imgui.end()

    def draw_hierarchy( self ) -> None:
        imgui.begin( "Hierarchy" )

        if imgui.tree_node( "Hierarchy", imgui.TREE_NODE_DEFAULT_OPEN ):

            for n, gameObject in enumerate( self.context.gameObjects ):
                if isinstance( gameObject, GameObject ): # link class name
                    clicked, _ = imgui.selectable(
                        label = gameObject.name,
                        selected = ( self.selectedObjectIndex == n )
                    )

                    if clicked:
                        self.selectedObjectIndex = n
                        self.selectedObject = self.context.gameObjects[ n ]

            imgui.tree_pop()

        imgui.end()
        return

    def draw_settings( self ) -> None:
        imgui.begin( "Settings" )

        changed, self.settings.drawWireframe = imgui.checkbox( 
            "Wireframe", self.settings.drawWireframe 
        )
        
        changed, self.settings.grid_color = imgui.color_edit3(
            "Grid color", *self.settings.grid_color
        )

        changed, self.settings.grid_size = imgui.drag_float(
                f"Grid size", self.settings.grid_size, 1
        )

        changed, self.settings.grid_spacing = imgui.drag_float(
                f"Grid spacing", self.settings.grid_spacing, 0.01
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

        if isinstance( gameObject, Sun ):
            imgui.text( f"Sun" );

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

    def draw_environment( self ) -> None:
        imgui.begin( "Environment" )

        changed, self.context.light_color = imgui.color_edit3(
            "Light color", *self.context.light_color
        )

        changed, self.context.ambient_color = imgui.color_edit3(
            "Ambient color", *self.context.ambient_color
        )

        changed, self.context.roughnessOverride = imgui.drag_float(
                f"Roughness override", self.context.roughnessOverride, 0.01
        )

        changed, self.context.metallicOverride = imgui.drag_float(
                f"Metallic override", self.context.metallicOverride, 0.01
        )

        imgui.end()
        return

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
            self.draw_inspector_material()

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
