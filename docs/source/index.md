

::::::{div} landing-title
:style: "margin-bottom:100px;padding: 0.1rem 0.5rem 0.6rem 0; background-image: linear-gradient(270deg, #e2b48000 0%, #d1705412 74%); clip-path: polygon(0px 0px, 100% 0%, 100% 100%, 0% calc(100% - 1.5rem)); -webkit-clip-path: polygon(0px 0px, 100% 0%, 100% 100%, 0% calc(100% - 1.5rem));"

::::{grid}
:reverse:
:gutter: 2 3 3 3
:margin: 4 4 1 2


:::{grid-item}
:columns: 12 12 12 12
:child-align: justify
:class: sd-text-white sd-fs-3 sd-text-center

Where Ideas Find Their Ember.

::::{grid}
:reverse:
:gutter: 2 3 3 3
:margin: 4 4 1 2

:::{grid-item}
:columns: 12 4 4 4
:::

::::{grid}
:gutter: 1
:margin: 0

:::{grid-item}
:columns: 6
:child-align: center

```{button-link} engine/engine.html
:ref-type: doc
:outline:
:color: white
:class: sd-px-4 sd-fs-5
:align: right

Engine Docs
```
:::

:::{grid-item}
:columns: 6
:child-align: center

```{button-link} https://github.com/mhoek2/EmberEngine/releases/tag/latest
:ref-type: doc
:outline:
:color: warning
:class: sd-px-4 sd-fs-5
:align: left
:target: blank

Get Latest Release
```
:::
::::

:::
::::

::::::


### Features
::::{grid} 1
:gutter: 0

:::{grid-item}
:::{gallery-grid}
:grid-columns: 1 2 2 3

- header: "{fas}`binary;pst-color-warning` Export to Binary"
  content: "Export a runtime scene to a Windows executable"

- header: "{fas}`code;pst-color-warning` Script Behaivior"
  content: "Write and attach scripts to objects. Including attribute exporting to the Inspector."

- header: "{fas}`sitemap;pst-color-warning` Hierarchy"
  content: "Organize objects by dragging them into parent-child relationships and control how they move together."

- header: "{fas}`group-arrows-rotate;pst-color-warning` Viewport Gizmos"
  content: "[ImGuizmo](https://github.com/CedricGuillemet/ImGuizmo): Allowing for easy object transform manipulations."

- header: "{fas}`person-falling-burst;pst-color-warning` PyBullet Integration"
  content: "[PyBullet](https://github.com/bulletphysics/bullet3): Real-time collision detection and multi-physics simulation for VR, games, visual effects, robotics, machine learning etc."

- header: "{fas}`cube;pst-color-warning` OpenGL and PyGame"
  content: "PyGame controls window context and event handlers, Native OpenGL is used for rendering."

- header: "{fas}`tv;pst-color-warning` Working With Scenes"
  content: "Scenes are stored as serialized JSON, making it easy to create, save, and switch between them."

- header: "{fas}`keyboard;pst-color-warning` Integrated IDE"
  content: "[ImColorTextEdit](https://github.com/CedricGuillemet/ImGuizmo): Scripts can be edited directly in the Engine."

:::
:::
::::


#### Educational
::::{grid} 1
:margin: 0 5 0 0
:padding: 0 5 0 0

:::{grid-item}
```{admonition} Built for educational purposes
:class: warning

#### Design Philosophy
**Modern AAA 3D engines are like sparks** --Powerful, instant and designed to ignite a fire of ideas.  
They're packed with optimized tools that turn a concept into an inferno of graphics and performance

**Ember Engine is diffrent**. Its not the spark at the start of the fire, but the ember at the end of one.  
It burns slower, softer and with less intensity.

3D Engines are rarely written in Python. --And for good reason. Python is interpreted, resulting in runtime overhead and [efficiency](https://en.wikipedia.org/wiki/Interpreter_(computing)#Efficiency) loss  
It simply cannot match the raw speed offered by AAA Engines.

**But an ember has its own purpose.** It's warm, safe and approachable.  
Yet holds the power to grow and rekindle itself.

#### Python at its Core
The Gui, Physics, Renderer back-end, and Scripting are implemented in Python.  
Though ```C++ -> Python bindings``` are used. --The core logic that connects everything is pure Python.

"How controversial it may be. it provides a nice way to explore engine design and development concepts hands-on.  
I value that as a good exercise!"
```
:::
::::

#### Showcase
:::::{div} preview-showcase

::::{grid} 1
:gutter: 3

:::{grid-item}
![](_static/showcase/ImGuizmo.gif)
:::

:::{grid-item}
![](_static/showcase/inspector_script.jpg)
:::

:::{grid-item}
![](_static/showcase/PyBullet.gif)
:::

:::{grid-item}
![](_static/showcase/hierarchy.jpg)

:::
::::
:::::



### Development
1. Install ```python``` from [the website](https://www.python.org/downloads/) ```*verified version: 3.12.7```
2. Create a directory, then [download](https://github.com/mhoek2/EmberEngine/archive/refs/heads/main.zip) and extract the codebase there.
3. Open a terminal in the fresh copy of the codebase and install the requirements
	```bash
	pip install -r requirements.txt
	```
4. Download binary dependency [Assimp](https://github.com/assimp/assimp/releases)
	1. Move ``Release\assimp-vc143-mt.dll`` from the ``zip`` to one of the PATH folders listed in your system variables
5. Open project folder in your preferred IDE and set main.py as startup item

#### Build local docs
1. Open a terminal of your choice in the root of the codebase
2. Install sphinx and theme requirements
	```bash
	pip install sphinx sphinx-design myst-parser pydata-sphinx-theme
	```
3. Build the docs 
	```bash
	python -m sphinx -b html docs/source docs/build
	```
4. Open docs/build/index.html in the browser

#### Documentation
```{button-link} engine/engine.html
:hidden:
:color: info
:align: left

See Engine Docs
```

```{toctree}
:maxdepth: 2

engine/engine.rst
engine/modules.rst
engine/gameObjects.rst

```