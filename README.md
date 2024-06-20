# pygeogram
Python bindings for [geogram](https://github.com/BrunoLevy/geogram)

# Note
This is work in progress, be patient, I first need to understand how wheels work (that is, precompiled Python packages), how to generate them, how to publish them so that one can "pip install" them...

If you need to use geogram in Python **now** (I don't know how much time it will take me to learn all these things), there is a possibility: you can use [gompy](https://github.com/BrunoLevy/GraphiteThree/wiki/python), that is, Graphite's object model projected into Python.

For now this repository only contains notes and links to documents and projects (thank you Twitter friends).

# Links, resources
- How to build wheels [here](https://gertjanvandenburg.com/blog/wheels/) 
- Github action to build a wheel [here](https://github.com/pypa/cibuildwheel)
- [PyBind11](https://github.com/pybind/pybind11)
- [NanoBind](https://github.com/wjakob/nanobind)

# Examples of projects with actions that build wheels and that publish on PyPI
- [Rhino3Dm](https://github.com/mcneel/rhino3dm)
- [Nick Sharp's potpourri3d](https://github.com/nmwsharp/potpourri3d/blob/master/.github/workflows/build.yml)
- [Lagrange](https://github.com/adobe/lagrange)
