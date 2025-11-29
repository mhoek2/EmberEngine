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


Installation (Windows)
======================
1. Download [Release or Beta](https://github.com/mhoek2/EmberEngine/releases) here.

Development
============
1. Download this repository
2. Open a terminal of your choice
3. Browse to the root folder of the downloaded project files
4. install dependencies using: ``pip install -r requirements.txt``
5. Download binary dependency [Assimp](https://github.com/assimp/assimp/releases)
	1. Move ``Release\assimp-vc143-mt.dll`` from the ``zip`` to one of the PATH folders listed in your system variables
6. Open project folder in your preferred IDE and set main.py as startup item

Build local docs
================
1. Open a terminal of your choice
2. Install ``python -m pip install sphinx pydata-sphinx-theme``
3. Execute ``python -m sphinx -b html docs/source docs/build`` from project root


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   main
   modules
   gameObjects

