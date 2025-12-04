import os, sys, enum
from pathlib import Path

from modules.settings import Settings
from modules.engineTypes import EngineTypes

from gameObjects.scriptBehaivior import ScriptBehaivior

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject

import inspect
import importlib
import traceback
import uuid as uid

class Script:
    def __init__( self, context : "EmberEngine", 
                    uuid            : uid.UUID      = None,
                    path            : Path          = None,
                    active          : bool          = False,
                    class_name      : str           = "",
                    class_name_f    : str           = "",
                    exports         : dict          = {}
                 ) -> None :
        # partial context
        self.context    = context
        self.settings   = context.settings
        self.console    = context.console

        if uuid is None:
            uuid = self.__create_uuid()

        self.instance       = None
        self.gameObject     : "GameObject" = None
         
        self.uuid           : uid.UUID = uuid
        self.path           : Path     = path.relative_to(self.settings.rootdir)
        self.active         : bool     = active
        self.class_name     : str      = class_name
        self.class_name_f   : str      = class_name_f
        self.exports        : dict     = exports
        self._error         : str = None

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

    #
    # path
    #
    def __resolve_script_path( self ):
        """Resolve the absolute file path of a script as a Path object.

        If the script path is relative, it is resolved against the project root
        (or current working directory if project root is not defined). Checks if
        the file exists.

        :param script: The Script TypedDict containing the 'path' key (Path or str)
        :return: Tuple (found: bool, file_path: Path)
        """
        __func_name__ = inspect.currentframe().f_code.co_name

        _file_path = self.path
        _found = True

        # resolve relative paths (important when running from .exe)
        if not os.path.isabs(_file_path):
            # assuming your engine has a context.project_root or similar path
            base_path = getattr(self.context, "project_root", os.getcwd())
            _file_path = os.path.join(base_path, _file_path)

        if not os.path.isfile(_file_path):
            self.console.error( f"[{__func_name__}] Script file not found: {_file_path}" )

            _found = False

        return _found, _file_path

    #
    # class
    #
    def __get_class_name_from_script( self, path: Path ) -> str:
        """Scan the content of the script to find the first class name.

        :param path: The path to a .py script file
        :type path: Path
        :return: A class name if its found, return None otherwise
        :rtype: str | None
        """
        filepath = (self.settings.rootdir / path).resolve()

        if os.path.isfile(filepath):
            code = filepath.read_text()
        else:
            return None

        for line in code.splitlines():
            if line.strip().startswith("class "):
                class_name = line.strip().split()[1].split('(')[0]

                if class_name.endswith(":"):
                    return class_name[:-1]

                return class_name

        return None

    def __format_class_name( self, name : str ) -> str:
        """Format the classname
        
        :return: Formatted string with space after any uppercased letter
        :rtype: str | None
        """
        formatted : str = ""

        for char in name:
            if char.isupper():
                formatted += f" {char}"
            else:
                formatted += char

        return formatted

    def __set_class_name( self ) -> None:
        """Gets the class name for a given scripts, also formats it for GUI
        
        :param script: The Script object containing a file path
        :type script: GameObject.Script
        """
        class_name = self.__get_class_name_from_script( self.path )

        self.class_name = class_name or "Invalid"
        self.class_name_f = self.__format_class_name( self.class_name )

    #
    # attribute export
    #
    def __load_script_exported_attributes( self, _ScriptClass ):
        """Loads and initializes exported attributes from a script class.

        If the attribute already exists in the scene (script["exports"), it overrides the default, 
        if the types match or is castable

        :param script: The Script TypedDict containing file path, class name, and existing exports
        :param _ScriptClass: The loaded class from the script module
        """
        __func_name__ = inspect.currentframe().f_code.co_name

        _exports = {}

        for class_attr_name, class_attr in _ScriptClass.__dict__.items():
            if isinstance(class_attr, ScriptBehaivior.Exported):
                _exports[class_attr_name] = class_attr

                class_attr_value = class_attr.get()
                class_attr_type = class_attr.type           # extract type from exported.default or annotated type
                #class_attr_type = type(class_attr_value)   # extract type from exported.default -deprectated

                # failed to export, type mismatch?
                if not class_attr.active:
                    self.console.error( f"[{__func_name__}] Export failed: {class_attr_name} = {class_attr_type.__name__}({class_attr_value})" )
                    continue

                # attribute NOT stored in the scene, use default class attribute value
                if class_attr_name not in self.exports:
                    self.console.log( f"[{__func_name__}] Export new: {class_attr_name} = {class_attr_type.__name__}({class_attr_value})" )
                    continue

                #
                # find export in saved scene and override attribute value
                #
                scene_instance_attr = self.exports[class_attr_name]

                # Sanity check
                if not isinstance(scene_instance_attr, ScriptBehaivior.Exported):
                    self.console.error( f"Export error: [{class_attr_name}] improperly loaded in script {self.class_name} from scene" )
                    continue

                scene_instance_attr_value = scene_instance_attr.get()

                # Try casting scene instance attribute value to new current type
                # Preserve if is of type UUID, the instance attribute is later resolved using this
                try:
                    # UUID type:
                    if isinstance( scene_instance_attr_value, uid.UUID ):
                        #self.console.log( f"[{__func_name__}] Export uuid: [{class_attr_name} = {scene_instance_attr_value.hex}] in script {script["class_name"]}" )
                        casted_value : uid.UUID = scene_instance_attr_value

                    # primitive types: attempt explicit cast
                    else:
                        casted_value = class_attr_type(scene_instance_attr_value)

                except Exception:
                    self.console.warn(
                        f"[{__func_name__}] Type change for '{class_attr_name}': "
                        f"scene instance value '{scene_instance_attr_value}' cannot convert to {class_attr_type.__name__}; "
                        f"using default '{class_attr_value}'"
                    )

                    # set class default value
                    casted_value = class_attr_value

                finally:
                    _exports[class_attr_name].set(casted_value)

                self.console.log( f"[{__func_name__}] Export found: {class_attr_name} = {class_attr_type.__name__}({casted_value})" )

        self.exports = _exports

    def __apply_script_exported_attributes( self ):
        """Apply exported class attributes to the script instance, resolving
        UUID references to GameObjects and/or copying primitive defaults.
        """
        __func_name__ = inspect.currentframe().f_code.co_name
        num_exports = 0

        for name, exported in self.exports.items():
            # engine type (uuid)
            if isinstance( exported.default, uid.UUID ):
                _t_engine_type : EngineTypes.EngineTypeInfo = EngineTypes.get_engine_type( exported.type )

                obj : "GameObject" = self.context.findGameObject( exported.default )

                if obj is None or _t_engine_type is None:
                    print( "failed to export.." )
                    setattr( self.instance, name, exported.default  )
                    continue

                # get the component and set reference on instance attribute
                _ref = obj.get_component( _t_engine_type._name )
                setattr( self.instance, name, _ref )

            # primitive types are a COPY
            # at this point, the effective value 'default' or '.get()' has already been initialized (from class or scene)
            else:
                setattr( self.instance, name, exported.default )

            num_exports += 1

        self.console.log( f"[{__func_name__}] Resolved and set ['{self.class_name}'] with {num_exports} exported attributes"  )

    #
    # instance
    #
    def init_instance( self, gameObject : "GameObject"  = None ) -> bool:
        """Initialize script attached to this gameObject,
        Try to load and parse the script, then convert to module in sys.

        Loads exported attribute, values from scene instance will override default class values

        :param script: The Script object containing a file path
        :type script: GameObject.Script
        """
        __func_name__ = inspect.currentframe().f_code.co_name

        if gameObject is None:
            self.console.error( f"GameObject is required for script" )
            return

        self.gameObject = gameObject

        self.console.log( f"[{__func_name__}] Init script: {self.path}" )

        try:
            if not self.active:
                self.instance = None
                self.console.note( f"[{__func_name__}] '{self.class_name}' is not active, skip" )
                return False

            # find and set class name
            self.__set_class_name()

            # destroy, somewhat ..
            # avoid storing direct references to objects inside script["instance"] 
            self.instance = None

            # Resolve the absolute script file path
            _found, file_path = self.__resolve_script_path()
            if not _found:
                raise FileNotFoundError( f"Script '{file_path}' not found!")

            # Derive a simple module name from the file name
            module_name = os.path.splitext(os.path.basename(file_path))[0]

            # Remove from sys.modules if already loaded (hot reload)
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Load the module from the file path
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                self.console.error( f"[{__func_name__}] Failed to load spec for {file_path}" )
                raise ImportError(f"Cannot import module from {file_path}")

            module = importlib.util.module_from_spec(spec)
        
            # Load ScriptBehaivior
            _script_behavior = importlib.import_module("gameObjects.scriptBehaivior")
            ScriptBehaivior = getattr(_script_behavior, "ScriptBehaivior")

            # define class attribute export method from ScriptBehaivior
            # making it callable from a dynamic script
            module.__dict__["export"] = ScriptBehaivior.export

            # import exportable engine types
            for _engine_type_class in EngineTypes.registry().keys():
                module.__dict__[_engine_type_class.__name__] = _engine_type_class

            # auto import modules
            for auto_mod_name, auto_mod_as in self.settings.SCRIPT_AUTO_IMPORT_MODULES.items():
                imported = importlib.import_module(auto_mod_name)

                if auto_mod_as is not None:
                    module.__dict__[auto_mod_as] = imported
                else:
                    module.__dict__[auto_mod_name] = imported

            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if not hasattr(module, self.class_name):
                self.console.error( f"[{__func_name__}] No class named '{self.class_name}' found in {file_path}" )
                raise AttributeError(
                    f"[{__func_name__}] No class named '{self.class_name}' found in {file_path}"
                )

            _ScriptClass = getattr(module, self.class_name)

            # load and initialize exported script attributes
            # either with class default, or stored value from scene
            self.__load_script_exported_attributes( _ScriptClass )

            class ClassPlaceholder(_ScriptClass, ScriptBehaivior):
                def __init__(self, context, gameObject):
                    ScriptBehaivior.__init__(self, context, gameObject)
                    if hasattr(_ScriptClass, "__init__"):
                        try:
                            _ScriptClass.__init__(self)
                        except TypeError:
                            pass

            self.instance = ClassPlaceholder(self.context, self.gameObject)
        
            # apply exported class attributes as script instance attributes
            self.__apply_script_exported_attributes( )

            # clear existing errors
            self._error = None

            # cache base methods
            self.base_methods = {
                "onStart"   : getattr( self.instance, "onStart", None ),
                "onUpdate"  : getattr( self.instance, "onUpdate", None ),
                "onEnable"  : getattr( self.instance, "onEnable", None ),
                "onDisable" : getattr( self.instance, "onDisable", None ),
            }
        
        # an error was raised  
        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.error( e, traceback.format_tb(exc_tb) )
            #self.console.warn(f"Script: [{self.path.name}] contains errors GameObject: [{self.name}]")
            self.console.warn(f"Script: [{self.path.name}] contains errors.")
        
            # mark as disabled
            self.instance = None
            self.active   = False
            self._error   = str(e)

            return False

        return True
