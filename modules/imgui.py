from pickletools import read_stringnl_noescape_pair
from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import imgui
from pygame import Vector2

from modules.material import Material
from modules.images import Images
from modules.models import Models
from modules.renderer import Renderer

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun

class ImGui:
    def __init__( self, context ):
        self.context = context
        self.io = imgui.get_io()

        self.drawWireframe = False
        self.selectedObject = False
        self.selectedObjectIndex = -1

        self.initialized = False

    def initialize_context( self ) -> None:
        if self.initialized:
            return

        self.renderer   : Renderer = self.context.renderer
        self.materials  : Material = self.context.materials
        self.images     : Images = self.context.images
        self.models     : Models = self.context.models

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

        # draw game framebuffer
        glBindTexture(GL_TEXTURE_2D, self.renderer.main_fbo["texture"])
        imgui.image( self.renderer.main_fbo["texture"], self.renderer.viewport_size.x, self.renderer.viewport_size.y, uv0=(0, 1), uv1=(1, 0) )

        imgui.end()

    def draw_hierarchy( self ) -> None:
        imgui.begin( "Hierarchy" )

        if imgui.tree_node("Hierarchy"):

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

    def draw_assets( self ) -> None:
        imgui.begin( "Assets" )

        for model_path in self.context.modelAssets:
            if imgui.button( model_path ):
                self.context.addGameObject( 
                        Mesh( self.context,
                        name        = f"GameObject { len( self.context.gameObjects ) }",
                        model_file  = model_path,
                        #material    = self.context.defaultMaterial,
                        translate   = [ 0, 0, 0 ],
                        scale       = [ 1, 1, 1 ],
                        rotation    = [ 0.0, 0.0, 0.0 ]
            ) )

        imgui.end()
        return

    def draw_settings( self ) -> None:
        imgui.begin( "Settings" )
        changed, self.drawWireframe = imgui.checkbox( "Wireframe", self.drawWireframe )
        imgui.end()
        return

    def draw_inspector_transform( self ) -> None:
        if not self.selectedObject:
            return

        gameObject = self.selectedObject

        if isinstance( gameObject, Mesh ):
            imgui.text( f"Mesh" );

        if isinstance( gameObject, Sun ):
            imgui.text( f"Sun" );

        if imgui.tree_node( "Transform" ):
            # rotation
            changed, (
                gameObject.translate[0],
                gameObject.translate[1],
                gameObject.translate[2],
            ) = imgui.drag_float3(
                label="Position",
                change_speed=0.01,
                value0=gameObject.translate[0],
                value1=gameObject.translate[1],
                value2=gameObject.translate[2],
            )

            # rotation
            changed, (
                gameObject.rotation[0],
                gameObject.rotation[1],
                gameObject.rotation[2],
            ) = imgui.drag_float3(
                label="Rotation",
                change_speed=0.01,
                value0=gameObject.rotation[0],
                value1=gameObject.rotation[1],
                value2=gameObject.rotation[2],
            )

            # scale
            changed, (
                gameObject.scale[0],
                gameObject.scale[1],
                gameObject.scale[2],
            ) = imgui.drag_float3(
                label="Scale",
                change_speed=0.01,
                value0=gameObject.scale[0],
                value1=gameObject.scale[1],
                value2=gameObject.scale[2],
            )

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

            # get material
            material_id = -1

            for mesh in self.models.model[gameObject.model].meshes:
                mesh_index = self.models.model[gameObject.model].meshes.index(mesh)

                mesh_gl = self.models.model_mesh[gameObject.model][mesh_index]
                material_id = mesh_gl["material"]

            if material_id < 0:
                imgui.tree_pop()
                return

            mat = self.materials.getMaterialByIndex( material_id )

            imgui.text( f"Material ID: { material_id }" );

            imgui.columns(count=2, identifier=None, border=False)

            self.draw_inspector_material_thumb( "Albedo", mat["albedo"] if 'albedo' in mat else self.images.defaultImage )
            self.draw_inspector_material_thumb( "Normal", mat["normal"] if 'normal' in mat else self.images.defaultNormal )
            self.draw_inspector_material_thumb( "Phyiscal", mat["phyiscal"] if 'phyiscal' in mat else self.images.defaultRMO )
            self.draw_inspector_material_thumb( "Emissive", mat["emissive"] if 'emissive' in mat else self.images.blackImage )
            
            imgui.columns(1)

            # specular scale

            imgui.tree_pop()
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
        self.draw_assets()
        self.draw_hierarchy()
        self.draw_settings()
        self.draw_inspector()
