

# Ember Engine 3D

Developed using ```Python```, ```OpenGL```,```Pygame```, ```ImGui```, and ```Assimp/Impasse```.  
It demonstrates the core principles of interactive 3D rendering.


## :mortar_board: Built for educational purposes
3D Engines are rarely written in Python. –And for good reason.  
Python is interpreted, resulting in runtime overhead and efficiency loss

"How controversial it may be. it provides a nice way to explore engine design and development concepts hands-on.  
I value that as a good exercise!"

## :high_brightness: Showcase
![](docs/source/_static/showcase/ImGuizmo.gif)

![](docs/source/_static/showcase/inspector_script.jpg)

![](docs/source/_static/showcase/PyBullet.gif)

![](docs/source/_static/showcase/hierarchy.jpg)

## :fire: Installation (Windows)
Download [Release or Beta](https://github.com/mhoek2/EmberEngine/releases) here.

## Development
1. Install ```python``` from [the website](https://www.python.org/downloads/) ```*verified version: 3.12.7```
2. Create a directory, then [download](https://github.com/mhoek2/EmberEngine/archive/refs/heads/main.zip) and extract the codebase there.
3. Open a terminal in the fresh copy of the codebase and install the requirements
	```bash
	pip install -r requirements.txt
	```
4. Download binary dependency [Assimp](https://github.com/assimp/assimp/releases)
	1. Move ``Release\assimp-vc143-mt.dll`` from the ``zip`` to one of the PATH folders listed in your system variables
5. Open project folder in your preferred IDE and set main.py as startup item

### Build local docs
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


## Latest version:
https://github.com/user-attachments/assets/7746df9e-e854-4730-9cb1-69f35433d842

## Older version:
https://github.com/user-attachments/assets/3027674b-0132-4761-9c3c-612fa972be97

## First version:
![372034450-06b15505-977c-48d2-b492-d4c78cba1962](https://github.com/user-attachments/assets/f2b619b4-5a28-4c22-8374-0e1d7e261763)
