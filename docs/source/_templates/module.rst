{{ fullname }}
{{ underline }}

{% if fullname == "modules.userInterface" %}
.. automodule:: {{ fullname }}
   :members:
   :exclude-members: DragAndDropPayload, Type_, ImGuizmo, TextEditor, Inspector, AssetBrowser, ConsoleWindow, Project
   :undoc-members:
   :show-inheritance:

.. autoclass:: modules.userInterface.UserInterface.DragAndDropPayload
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.Type_
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.ImGuizmo
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.ImGuizmo.OperationMode
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.TextEditor
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.Hierarchy
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.GameObjectTypes
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.Inspector
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.AssetBrowser
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.ConsoleWindow
   :members:
   :undoc-members:
   :show-inheritance:
.. autoclass:: modules.userInterface.UserInterface.Project
   :members:
   :undoc-members:
   :show-inheritance:
{% else %}
.. automodule:: {{ fullname }}
   :members:
   :undoc-members:
   :show-inheritance:
{% endif %}

