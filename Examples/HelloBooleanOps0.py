# HelloBooleanOps0:
# How to create Graphite objects and display them in Polyscope
# (there is no boolean op for now)

import polyscope as ps
import numpy as np
import gompy
OGF = gom.meta_types.OGF # All graphite classes are there, create a shortcut

def register_graphite_object(O: OGF.MeshGrob):
   """
   @brief Registers a graphite object to Polyscope
   @param[in] O the graphite object to be registered
   """
   # One can directly access the points and the triangles in a graphite
   # object as numpy arrays, using the Editor interface, as follows:
   pts = np.asarray(O.I.Editor.get_points())
   tri = np.asarray(O.I.Editor.get_triangles())
   # Then the numpy arrays are sent to polyscope as follows:
   ps.register_surface_mesh(O.name,pts,tri)

def register_graphite_objects(scene_graph: OGF.SceneGraph):
   """
   @brief Registers all the graphite objects in a scene graph to Polyscope
   @param[in] scene_graph the Graphite scene graph
   """
   for objname in dir(scene_graph.objects):
       register_graphite_object(scene_graph.resolve(objname))

# First create a SceneGraph. It will contain
# all the subsequently created Graphite objects.
scene_graph = OGF.SceneGraph()


# Create an empty mesh. The specified string is the name of the mesh as
# it will appear in Polyscope (and also how it is bound in the SceneGraph)
S1 = OGF.MeshGrob('S1')


# Create a sphere in the mesh
# Functions that operate on a mesh are available through "Interfaces". All
# the interfaces are accessed through S1.I. ...
# To learn what you can do, try this:
#   In an interactive session, create a mesh (M = OGF.Mesh()), then use
#   autocompletion (M.I. then press 'tab')
#   All functions have an online help, use M.I.Shapes.create_sphere.help() to
#   display it (for instance)
S1.I.Shapes.create_sphere(center=[0,0,0])

# Initialize polyscope
ps.init()

# Register all graphite objects to polyscope
register_graphite_objects(scene_graph)

# Enter polyscope main loop
ps.show()
