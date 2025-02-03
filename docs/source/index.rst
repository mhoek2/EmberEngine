.. EmberEngine documentation master file, created by
   sphinx-quickstart on Thu Jan 30 10:10:56 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

EmberEngine documentation
=========================

This 3D engine is developed using Python, OpenGL, Pygame, ImGui docking, and Impasse. \
It demonstrates the core principles of 3D rendering and interactive graphics.

The primary goal of this project is to gain more knowledge in Python programming.

"Because of Python's limitations, it is not typically used for 3D graphics applications. However, I still value it as a good exercise!

Installation
============

1. Download this repository
2. Open a terminal of your choice
3. Browse to the root folder of the downloaded project files
4. install dependencies using: ``pip install -r requirements.txt``

5. Install dependency: **Assimp** - *requirement for [Impasse](https://github.com/SaladDais/Impasse)*:
	1. Get and build [Assimp](https://github.com/assimp/assimp/tree/master)
	2. Copy ``assimp\bin\Release\assimp-vc143-mt.dll``` to the python install location: eg. ``C:\Python39``

7. Install dependency: **pyImGui**:
	1. Get and build [pyImGui docking](https://github.com/pyimgui/pyimgui/tree/docking)
 		1. Windows: run ``pip install .`` in root folder of the project 
	3. Replace files in ``C:\Python39\Lib\site-packages\imgui`` with files in ``pyimgui\build\lib.win-amd64-3.9\imgui``




.. toctree::
   :maxdepth: 2
   :caption: Contents:

   main
   modules
   gameObjects

