# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

#sys.path.insert(0, os.path.abspath('../../'))
#sys.path.insert(1, os.path.abspath('../../modules'))
sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))
#sys.path.insert(1, os.path.abspath(os.path.join('..', '..', 'modules')))

project = 'EmberEngine'
copyright = '2025, Marco Hoekstra'
author = 'Marco Hoekstra'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
]
autodoc_mock_imports = ['imgui', 'modules.context', 'pygame', 'OpenGL', 'impasse']

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
