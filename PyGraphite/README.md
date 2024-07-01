# PyGraphite

Here you will find a version of [Graphite](https://github.com/BrunoLevy/GraphiteThree) that runs
in [PolyScope](https://polyscope.run/) using [PolyScope Python bindings](https://polyscope.run/py/).

What is Graphite ?
------------------

Graphite is an experimental 3D modeler, built around
[geogram](https://github.com/BrunoLevy/geogram). 

It has [Pointset processing and reconstruction](Points), 
[Surface remeshing and repair](Remeshing) and many other functionalities,
see [Mesh commands reference](Mesh) for the complete list.

It contains the main results in Geometry Processing from the former
ALICE Inria project, that is, more than 30 research articles published
in ACM SIGGRAPH, ACM Transactions on Graphics, Symposium on Geometry 
Processing and Eurographics. It was supported by two grants from the
European Research Council (ERC): GOODSHAPE and VORPALINE.

How to install PyGraphite ?
---------------------------

You will need to compile Graphite and gompy (see below). In the future I'll do something to have a pip-installable or a conda-installable pre-compiled package (but I need to learn how to do that, will take me a while).

- Step 1: install Graphite from sources, see [instructions here](https://github.com/BrunoLevy/GraphiteThree/wiki#installing)
- Step 2: install gompy (Python bindings for Graphite), see [instructions here](https://github.com/BrunoLevy/GraphiteThree/wiki/python)
- Step 3: install Python bindings for PolyScope, see [instructions here](https://github.com/nmwsharp/polyscope-py?tab=readme-ov-file#installation)
- Step 4: get [`pygraphite.py`](https://raw.githubusercontent.com/BrunoLevy/pygeogram/main/PyGraphite/pygraphite.py)
- Step 5: run it !
```
python3 graphite.py <optional files to load ....>
```

How to use PyGraphite ?
-----------------------

See Graphite tutorial [here](https://github.com/BrunoLevy/GraphiteThree/wiki#manuals-and-tutorials) _note: these tutorials are for the regular version of Graphite, appearance and behavior are slightly different, for instance, one needs to right-click on the name of an object in the list to get the list of commands_