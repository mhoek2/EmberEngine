from pathlib import Path

from typing import TYPE_CHECKING

from OpenGL.GL import *  # pylint: disable=W0614

from modules.context import Context

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa
from modules.gui.types import GameObjectTypes

from gameObjects.attachables.model import Model

if TYPE_CHECKING:
    from main import EmberEngine
    from modules.models import Models

import uuid as uid

class RendererInfo( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper
     
        self.extension_filter = imgui.TextFilter()
        self.gameObject_filter = imgui.TextFilter()
        self.modelMeshes_filter = imgui.TextFilter()

    def _openGLInfo( self ) -> None:
        imgui.text( f"GL_VERSION : { glGetString(GL_VERSION).decode() }" )   
        imgui.text( f"GL_VENDOR  : { glGetString(GL_VENDOR).decode() }" )    
        imgui.text( f"GL_RENDERER: { glGetString(GL_RENDERER).decode() }" )  

        self.helper._node_sep()

        # filter
        self.extension_filter.draw("Filter")

        _table_flags = imgui.TableFlags_.resizable | \
                       imgui.TableFlags_.hideable | \
                       imgui.TableFlags_.borders_v | \
                       imgui.TableFlags_.borders_outer | \
                       imgui.TableFlags_.row_bg | \
                       imgui.TableFlags_.scroll_x | \
                       imgui.TableFlags_.scroll_y

        if imgui.begin_table( "OpenGL Extensions", 1, _table_flags ):

            imgui.table_setup_column("Extensions")
            imgui.table_headers_row()

            for extension in self.context.renderer.gl_extensions:

                # filter
                if not self.extension_filter.pass_filter(extension):
                    continue

                imgui.table_next_row()
                imgui.table_set_column_index(0)
                imgui.text( extension )

            imgui.end_table()

    def _gameObjects( self ) -> None:
        # colors
        _disabled_color = imgui.color_convert_float4_to_u32( imgui.ImVec4(1, 1, 0, 0.5) )
        _removed_color = imgui.color_convert_float4_to_u32( imgui.ImVec4(1, 0, 0, 0.5) )


        self.helper.draw_color_legend_item( "Disabled", _disabled_color )
        self.helper.draw_color_legend_item( "Removed", _removed_color )

        # filter
        self.gameObject_filter.draw("Filter")

        _table_flags = imgui.TableFlags_.resizable | \
                       imgui.TableFlags_.hideable | \
                       imgui.TableFlags_.borders_v | \
                       imgui.TableFlags_.borders_outer | \
                       imgui.TableFlags_.row_bg | \
                       imgui.TableFlags_.scroll_x | \
                       imgui.TableFlags_.scroll_y

        if imgui.begin_table( "GameObjects", 3, _table_flags ):
        
            imgui.table_setup_column("name")
            imgui.table_setup_column("-")
            imgui.table_setup_column("model")
            imgui.table_headers_row()

            for uuid, obj in self.context.world.gameObjects.items():
                _t_game_object = GameObjectTypes.get_gameobject_type( type(obj) )

                # filter
                if not self.gameObject_filter.pass_filter( obj.name ):
                    continue

                imgui.table_next_row()

                # color
                if not obj.hierachyActive():
                    imgui.table_set_bg_color( 1, _disabled_color )

                if uuid in self.context.world.trash:
                    imgui.table_set_bg_color( 1, _removed_color )

                # content
                imgui.table_set_column_index(0)
                imgui.text( f"{_t_game_object._icon} {obj.name}" )
                imgui.set_item_tooltip( str(uuid)  )

                imgui.table_set_column_index(1)
                imgui.text( "-" )

                imgui.table_set_column_index(2)
                _handle : int = None
                _model  : Model = None

                if uuid in self.context.world.models:
                    _model = self.context.world.models[uuid]
                    _handle = self.context.world.models[uuid].handle

                    _path = str(_model.path.relative_to( self.settings.rootdir ))
                    imgui.text( f"[{_handle}] {_path}" )
                else:
                    imgui.text( "n/a" )

            imgui.end_table()

    def _draw_modelMesh(self, node, model_index: int, depth : int = 0 ):
        model = self.context.models.model[model_index]
        model_meshes = self.context.models.model_mesh[model_index]

        # node.meshes contains references to the mesh objects
        for mesh in node.meshes:
            mesh_index = model.meshes.index(mesh)
            _model_mesh = model_meshes[mesh_index]
        #for mesh in node.meshes:
        #    mesh_index  : int = self.context.models.model[model_index].meshes.index(mesh)
        #    _model_mesh : "Models.Mesh" = self.context.models.model_mesh[model_index][mesh_index]

            imgui.table_next_row()

            # treenode column
            imgui.table_set_column_index(0)
            flags = (
                imgui.TreeNodeFlags_.leaf
                | imgui.TreeNodeFlags_.no_tree_push_on_open
                | imgui.TreeNodeFlags_.span_all_columns
            )

            imgui.tree_node_ex( f"Mesh {mesh_index} {mesh.name}", flags )

            imgui.table_set_column_index(1)
            imgui.text( f"{_model_mesh["num_indices"]}" )

            imgui.table_set_column_index(2)
            imgui.text( f"{_model_mesh["baseVertex"]}" )

            imgui.table_set_column_index(3)
            imgui.text( f"{_model_mesh["firstIndex"]}" )

            imgui.table_set_column_index(4)
            imgui.text( f"{_model_mesh["material"]}" )

        for child in node.children:
            # root
            #if depth == 0:
            #    self._draw_modelMesh( child, model_index, depth + 1 )
            #    continue

            imgui.table_next_row()
            imgui.table_set_column_index(0)

            # nodes
            flags = imgui.TreeNodeFlags_.span_all_columns
            opened = imgui.tree_node_ex( child.name, flags )
            if opened:
                self._draw_modelMesh( child, model_index, depth + 1 )

                imgui.tree_pop()
    
    #def _getModelPath( self, index : int ) -> Path:
    #    for path, model_index in self.context.models.model_map.items():
    #        if model_index == index:
    #            return path
    #
    #    return None

    def _modelMeshes(self) -> None:
        self.gameObject_filter.draw("Filter")

        _table_flags = imgui.TableFlags_.resizable | \
                       imgui.TableFlags_.hideable | \
                       imgui.TableFlags_.borders_v | \
                       imgui.TableFlags_.borders_outer | \
                       imgui.TableFlags_.row_bg | \
                       imgui.TableFlags_.scroll_x | \
                       imgui.TableFlags_.scroll_y

        if imgui.begin_table("Model Meshes", 5, _table_flags):
            imgui.table_setup_column("Mesh")
            imgui.table_setup_column("indices")
            imgui.table_setup_column("baseVertex")
            imgui.table_setup_column("firstIndex")
            imgui.table_setup_column("material")
            imgui.table_headers_row()

            for i in range(self.context.models._num_models):
                _model      = self.context.models.model[i]
                root        = _model.root_node
                _path_full  = self.context.models.model_path[i]
                _path       = str(_path_full.relative_to( self.settings.rootdir )) if _path_full else "unknown"

                imgui.table_next_row()
                imgui.table_set_column_index(0)

                opened = imgui.tree_node_ex(
                    f"{_path}",
                    imgui.TreeNodeFlags_.span_all_columns# | imgui.TreeNodeFlags_.default_open
                )

                imgui.table_set_column_index(1)
                imgui.text("-")

                imgui.table_set_column_index(2)
                imgui.text("-")

                imgui.table_set_column_index(3)
                imgui.text("-")

                imgui.table_set_column_index(4)
                imgui.text("-")

                depth = 0
                if opened:
                    self._draw_modelMesh( root, i, depth )
                    imgui.tree_pop()

            imgui.end_table()

    def _textures( self ):
        _table_flags = imgui.TableFlags_.resizable | \
                       imgui.TableFlags_.hideable | \
                       imgui.TableFlags_.borders_v | \
                       imgui.TableFlags_.borders_outer | \
                       imgui.TableFlags_.row_bg | \
                       imgui.TableFlags_.scroll_x | \
                       imgui.TableFlags_.scroll_y

        if imgui.begin_table( "Textures", 4, _table_flags ):
        
            imgui.table_setup_column("#")
            imgui.table_setup_column("OpenGL ID")
            imgui.table_setup_column("Bindless Handle")
            imgui.table_setup_column("Path / Identifier")
            imgui.table_headers_row()

            for i in range(self.context.images._num_images):
                texture_id = self.context.images.images[i]
                _path = self.context.images.images_paths[i]
                _bindless = self.context.images.texture_to_bindless[i]

                imgui.table_next_row()

                # content
                imgui.table_set_column_index(0)
                imgui.text( f"{i}" )

                imgui.table_set_column_index(1)
                imgui.text( f"{texture_id}" )

                imgui.table_set_column_index(2)
                imgui.text( f"{_bindless}" )

                imgui.table_set_column_index(3)
                imgui.text( f"{_path}" )

            imgui.end_table()


    def render( self ):
        if imgui.begin_popup_modal("Renderer Info", None, imgui.WindowFlags_.no_resize)[0]:
            imgui.set_window_size( imgui.ImVec2(1024, 400) )  # Example: width=4

            if self.helper.draw_close_button( f"{fa.ICON_FA_CIRCLE_XMARK}", imgui.get_window_width() - 30 ):
                imgui.close_current_popup()

            _region = imgui.get_content_region_avail()
            pos = imgui.get_cursor_screen_pos()

            imgui.push_id("##RendererInfo")
            _flags = imgui.TabBarFlags_.none

            if imgui.begin_tab_bar( "PhysicProperties", _flags ):
                if imgui.begin_tab_item("OpenGL##Tab1")[0]:
                    self._openGLInfo()
                    imgui.end_tab_item()

                if imgui.begin_tab_item("GameObjects##Tab2")[0]:
                    self._gameObjects()
                    imgui.end_tab_item()

                if imgui.begin_tab_item("Model Meshes##Tab2")[0]:
                    self._modelMeshes()
                    imgui.end_tab_item()

                if imgui.begin_tab_item("Textures##Tab3")[0]:
                    self._textures()
                    imgui.end_tab_item()

                # End tab bar
                imgui.end_tab_bar()

            imgui.pop_id()
            imgui.end_popup()