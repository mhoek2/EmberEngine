from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

from typing import TYPE_CHECKING

from modules.context import Context
from modules.transform import Transform

from gameObjects.gameObject import GameObject

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa
from imgui_bundle import imgui_color_text_edit as ImGuiColorTextEdit

if TYPE_CHECKING:
    from main import EmberEngine

from pathlib import Path

class TextEditor( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

        #with open(__file__, encoding="utf8") as f:
        #    this_file_code = f.read()

        self._current_file : Path = None

        self.ed : ImGuiColorTextEdit.TextEditor = ImGuiColorTextEdit.TextEditor()
        self.ed.set_text("")
        self.ed.set_palette(ImGuiColorTextEdit.TextEditor.PaletteId.dark)
        self.ed.set_language_definition(ImGuiColorTextEdit.TextEditor.LanguageDefinitionId.python)
  
    def get_current_file( self ) -> None:
        """"Returns Path of current file, None if no file selected"""
        return self._current_file

    def reset( self ) -> None:
        """Completely clears the text editor and resets its state."""
        self.ed.set_text("")
        self.ed.set_cursor_position(0, 0)
        self.ed.clear_selections()
        self.ed.clear_extra_cursors()

        self._current_file = None

    def save( self ) -> None:
        text = self.ed.get_text()

        if self._current_file:
            with open(self._current_file, "w", encoding="utf8") as f:
                f.write(text)

            self.console.note( f"Saved to {self._current_file}")

            self.scene.updateScriptonGameObjects( self._current_file )

        else:
            self.console.error( "No file selected yet.")

    def open_file( self, path : Path ) -> None:
        """Opens a file and make its content the current text of the text editor"""
        buffer = None

        if path.is_absolute():
            relative_path = path.relative_to(self.settings.rootdir)
        else:
            relative_path = path

        if not relative_path.is_file():
            self.console.error( f"File: {relative_path} does not exist!" )
            return

        with open(relative_path, encoding="utf8") as f:
            buffer = f.read()

        self.reset();
        self.ed.set_text( buffer )
        self._current_file = relative_path

    def fix_tabs( self ) -> None:
        """"Hacky but fine for now
 
        This will replace all tabs '\t' with 4 spaces, not just the freshly added tab
        """
        if self._current_file.suffix == self.settings.SCRIPT_EXTENSION:
            _text = self.ed.get_text()
            self.ed.set_text( _text.replace("\t", "    ") )

    def render( self ) -> None: 
        """handles ImGuiColorTextEdit rendering and logic"""
        imgui.begin( "IDE" )

        self.ed.render("Code")

        # handle events
        if imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows):
            self.context.cevent.handle( "save",   self.save )
            self.context.cevent.handle( "copy",   self.ed.copy )
            self.context.cevent.handle( "paste",  self.ed.paste )
            self.context.cevent.handle( "undo",   self.ed.undo )
            self.context.cevent.handle( "redo",   self.ed.redo )
            self.context.cevent.handle( "tab",    self.fix_tabs )

        imgui.end()