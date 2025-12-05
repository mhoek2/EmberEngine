::::::{div} landing-title
:style: "padding: 0.1rem 0.5rem 0.6rem 0; background-image: linear-gradient(270deg, #e2b48000 0%, #d1705412 74%); clip-path: polygon(0px 0px, 100% 0%, 100% 100%, 0% calc(100% - 1.5rem)); -webkit-clip-path: polygon(0px 0px, 100% 0%, 100% 100%, 0% calc(100% - 1.5rem));"

::::{grid}
:reverse:
:gutter: 2 3 3 3
:margin: 4 4 1 2

:::{grid-item}
:columns: 12 4 4 4


:::

:::{grid-item}
:columns: 12 8 8 8
:child-align: justify
:class: sd-text-white sd-fs-3

Not a Spark, but a Start

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

```{button-link} engine/index.html
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

Get Latest Release
```
:::
::::

:::
::::

::::::


::::{grid} 2
:gutter: 3 3 4 5
:margin: 5 5 0 0
:padding: 5 5 0 0

:::{grid-item}
```{button-link} engine/index.html
:color: info
:align: right

See Engine Docs
```
:::
:::{grid-item}

```{button-link} https://github.com/mhoek2/EmberEngine/releases/tag/latest
:color: warning
:align: left
 
Get Latest Release
```
:::
::::


### Features
```{gallery-grid}
:grid-columns: 1 2 2 3

- header: "{fas}`bolt;pst-color-primary` Export to Binary"
  content: "Export a runtime scene to a Windows executable"

- header: "{fas}`circle-half-stroke;pst-color-primary` Script Behaivior"
  content: "Write and attach scripts to game objects. Including attribute exporting to the Inspector"

- header: "{fab}`bootstrap;pst-color-primary` Hierarchy"
  content: "Organize game objects by dragging them into parent-child relationships and control how they move together"

- header: "{fas}`lightbulb;pst-color-primary` Viewport Gizmos"
  content: "[ImGuizmo](https://github.com/CedricGuillemet/ImGuizmo) integrated in the viewport"

- header: "{fas}`palette;pst-color-primary` PyBullet Integration"
  content: "[PyBullet](https://github.com/bulletphysics/bullet3): Real-time collision detection and multi-physics simulation for VR, games, visual effects, robotics, machine learning etc."

- header: "{fab}`python;pst-color-primary` OpenGL and PyGame"
  content: "PyGame controls window context and event handlers, Native OpenGL is used for rendering"

```

#### Educational
::::{grid} 1
:margin: 0 5 0 0
:padding: 0 5 0 0

:::{grid-item}
```{admonition} Built for educational purposes
:class: warning

#### Design Philosophy
**Modern AAA 3D engines are like sparks** --Powerful, instant and designed to ignite a fire of ideas. \
They're packed with optimized tools that turn a concept into an inferno of graphics and performance

**Ember Engine is diffrent**. Its not the spark at the start of the fire, but the ember at the end of one.\
It burns slower, softer and with less intensity.

3D Engines are rarely written in Python. --And for good reason. Python is interpreted, resulting in runtime overhead and [efficiency](https://en.wikipedia.org/wiki/Interpreter_(computing)#Efficiency) loss \
It simply cannot match the raw speed offered by AAA Engines.

**But an ember has its own purpose.** It's warm, safe and approachable. Yet holds the power to grow and rekindle itself.

#### Ember Engine
The Gui, Physics, Renderer back-end, and Scripting are implemented in Python. \
Though ```C++ -> Python bindings``` are used. --The core logic that connects everything is pure Python.

"How controversial it may be. it provides a nice way to explore engine design and game development concepts hands-on.

And I value that as a good exercise!"
```
:::
::::


### Development
1. Download this repository
2. Open a terminal of your choice
3. Browse to the root folder of the downloaded project files
4. install dependencies using: ``pip install -r requirements.txt``
5. Download binary dependency [Assimp](https://github.com/assimp/assimp/releases)
	1. Move ``Release\assimp-vc143-mt.dll`` from the ``zip`` to one of the PATH folders listed in your system variables
6. Open project folder in your preferred IDE and set main.py as startup item

### Build local docs
1. Open a terminal of your choice
2. Install ``python -m pip install sphinx pydata-sphinx-theme``
3. Execute ``python -m sphinx -b html docs/source docs/build`` from project root

### Engine Documentation

```{toctree}
:maxdepth: 2

engine/index
engine/modules
engine/gameObjects

```

```sources:
https://sphinx-design.readthedocs.io/en/pydata-theme/
```