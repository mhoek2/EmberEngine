# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
from pathlib import Path

#sys.path.insert(0, os.path.abspath('../../'))
#sys.path.insert(1, os.path.abspath('../../modules'))
sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))
sys.path.append(str(Path(".").resolve()))
#sys.path.insert(1, os.path.abspath(os.path.join('..', '..', 'modules')))

project = 'EmberEngine'
copyright = '2025, Marco Hoekstra'
author = 'Marco Hoekstra'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx_design",
    "myst_parser",
    "_extension.gallery_directive",
]
autodoc_mock_imports = ['imgui_bundle', 'modules.context', 'pygame', 'OpenGL', 'impasse']
autosummary_generate = True
autosummary_imported_members = True
autosummary_generate_overwrite = True


autodoc_default_options = {
    'special-members': '__init__',  # Explicitly include __init__
}

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'alabaster'
html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']

html_logo = "_static/logo.ico"
html_favicon = "_static/logo.png"

html_css_files = [
    'main.css',
]

myst_enable_extensions = [
    "colon_fence",      # allows ::: directives
    #"linkify",          # auto-detect URLs
    "substitution",     # supports content substitutions
    "attrs_block",      # allows block-level attributes
]

html_theme_options = {
    "show_nav_level": 2,
    "header_links_before_dropdown": 4,
    "icon_links": [
        {
            "name": "Author",
            "url": "https://mhoek2.github.io/",
            "icon": "fa-regular fa-address-card",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/mhoek2/EmberEngine",
            "icon": "fa-brands fa-github",
        },
    ],

    "logo": {
        "text": "EmberEngine",
        "image_light": "_static/logo.png",
        "image_dark": "_static/logo.png",
    },
}
