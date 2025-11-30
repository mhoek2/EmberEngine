class ScriptBehaivior:
    def __init__( self, context, gameObject ):
        """Base class for dynamic loaded scripts, 
        setting up references to context, events and the gameObject itself
        
        :param context: This is the main context of the application
        :type context: EmberEngine
        :param gameObject: A reference to the gameObject the script is attached to
        :type gameObject: GameObject
        """
        self.context    = context
        self.settings   = context.settings
        self.renderer   = context.renderer
        self.scene      = context.scene
        self.console    = context.console

        self.events     = context.events
        self.key        = context.key
        self.mouse      = context.mouse

        self.gameObject = gameObject
        self.transform  = self.gameObject.transform

    def onStart( self ):
        """Implemented by script"""
        pass

    def onUpdate( self ):
        """Implemented by script"""
        pass

    def onEnable( self ):
        """Implemented by script"""
        pass

    def onDisable( self ):
        """Implemented by script"""
        pass

    #
    # export class attributes
    #
    class Exported:
        """Exported Attribute System - IMPORTANT DESIGN NOTES
        
        When a script declares:
        
            value : int = export(1)
        
        the class attribute `value` does **not** become an integer.
        Instead, it becomes an instance of `Exported`, which stores metadata
        about the exported field:
        
          - the default value (1)
          - the expected type (int)
          - whether the export is active/valid
        
        At runtime, the script instance receives a **separate** attribute:
        
            self.value
        
        This is initialized during script loading using:
            setattr(script_instance, name, value.default)
        
        Meaning:
          - Class-level:  value  -> Exported(...)     (metadata object)
          - Instance:     self.value -> actual runtime value (e.g. int)
        
        For primitive types (int, float, bool, str):
          - value.default holds the raw primitive value
          - self.value receives a COPY of that primitive
          - They contain the same data but are distinct objects
        
        For engine reference types (e.g. Transform, GameObject references):
          - value.default stores a UUID (persistent identifier)
          - self.value is resolved at runtime into the actual GameObject with to that UUID
        
        In other words:
          - value       = Exported(...): metadata about the field
          - self.value  = the runtime value used during script execution (onUpdate, etc.)
        """


        def __init__( self, default=None ):
            self.default    = default           # the value stored as meta, used to init instance value 
            self.type       = type(default)     # type from default argument, override with annotated type in __set_name__
            self.active     = True              # non-matching primitive types are set in-active

        def is_primitive_type( self, t ) -> bool:
            """Wheter a type is of primitive type.

            :param t: Type to check
            :return: True if t is int, float, bool, or str
            """
            return t in (int, float, bool, str)

        def default_for_annotation_type( self, t ):
            """
            Return a default value for a given type.

            For primitive types: returns 0, 0.0, False, or ""  
            For other types: tries to instantiate t(), returns None when failed.

            :param t: Type to get default value for
            :return: Default value for the type or None
            """
            _defaults = {
                int     : 0,
                float   : 0.0,
                bool    : False,
                str     : ""
            }

            if t in _defaults:
                return _defaults[t]
            
            # try calling default constructor of engine types
            try:
                return t() 

            except Exception:
                return None

        def __set_name__( self, owner, name ):
            """Allows to set a custom datatype, compare default value type with the annotated (: str) type
            Mark as disabled when it does not match.
            """
            annotated_type = None

            if hasattr(owner, '__annotations__'):
                annotated_type = owner.__annotations__.get(name)

            if annotated_type:
                self.type = annotated_type # override manual datatype

                # no default value, just initialize to 0 or "" or False based on requrested type
                if not self.default:
                    self.default = self.default_for_annotation_type( annotated_type )

                    # only mark disabled when it is a primitive type
                    if self.is_primitive_type( annotated_type ) and not self.default:
                        self.active = False

                    return

                # annotated type does not match default type, just throw and error for now
                #       annotated       default
                #          ^               ^
                # value : int = export("string")
                #
                # or .. we can do same as above, init to the datatypes default?
                # or .. when not active, init instance attribute to None in GameObject.__load_script_exported_attributes()?
                if self.default is not None and not isinstance(self.default, annotated_type):
                    self.default = None
                    self.active = False

                    print(
                        f"Exported attribute '{name}' expected type "
                        f"{annotated_type.__name__}, got {type(self.default).__name__}"
                    )

        def get( self ):
            """Get the meta value used to init the instance attribute

            :return: Either primitive value, or UUID
            :rtype: int | float | bool | str | uuid.UUID
            """
            return self.default

        def set( self, value ) -> None:
            """Set meta value for this export, user for saving and loading

            if primitive type, validate that the value matches the current data type
            
            else, engine types allow mismatched types.
            eg, 'value.default' contains the UUID, and instance 'self.value' is resolved to that GameObject at runtime
            """
            if self.is_primitive_type(self.type) and not isinstance(value, self.type):
                print(f"Type of {type(value)} does not match expected type of {self.type}")
                return

            self.default = value

    def export( default=None ):
        """Create an exported script attribute.

        Used inside script classes to declare editable fields:

            - value: int = export(1)
            - value: float = export(1.0)
            - value: bool = export(True)
            - value: str = export("Hello world")
            - value: Transform = export() # no argument

        During script loading, exported class attributes are detected and
        their values are copied into the script instance as:

            # either the stored scene value, a type-based default, or a resolved GameObject reference (for engine types) \n
            self.value
        
        :param default: Optional initial value. When omitted, a type-based default is used.
        :return: An Exported metadata descriptor.
        :rtype: ScriptBehaivior.Exported
        """
        return ScriptBehaivior.Exported( default )
