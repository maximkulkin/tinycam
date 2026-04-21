"""
Build Cython extensions for TinyCAM.

Usage:
    python setup.py build_ext --inplace

This compiles _line2d_cy.pyx into a native extension that is loaded
automatically by line2d.py when present, falling back to pure Python
if the extension is not built.
"""

from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

extensions = [
    Extension(
        name="tinycam.ui.view_items.core._line2d_cy",
        sources=["tinycam/ui/view_items/core/_line2d_cy.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=["-O3", "-ffast-math"],
    ),
]

setup(
    name="tinycam",
    ext_modules=cythonize(
        extensions,
        language_level=3,
        compiler_directives={
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
            "nonecheck": False,
        },
    ),
)
