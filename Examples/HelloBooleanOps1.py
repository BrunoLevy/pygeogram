# HelloBooleanOps1:
# Let us create two spheres and compute their intersections
# We shall also see how to change Polyscope graphic attributes

import polyscope as ps
import numpy as np
import gompy
OGF = gom.meta_types.OGF

# ---------------------- Same as before --------------------------------

def register_graphite_object(O: OGF.MeshGrob):
   """
   Registers a graphite object to Polyscope
   @param[in] O the graphite object to be registered
   """
   pts = np.asarray(O.I.Editor.find_attribute('vertices.point'))
   tri = np.asarray(O.I.Editor.get_triangles())
   ps.register_surface_mesh(O.name,pts,tri)

def register_graphite_objects(scene_graph: OGF.SceneGraph):
   """
   Registers all the graphite objects in a scene graph to Polyscope
   @param[in] scene_graph the Graphite scene graph
   """
   for objname in dir(scene_graph.objects):
       register_graphite_object(scene_graph.resolve(objname))

# ----------------------------------------------------------------------

# Create the SceneGraph
scene_graph = OGF.SceneGraph()

# Create two spheres
S1 = OGF.MeshGrob('S1')
S1.I.Shapes.create_sphere(center=[0,0,0])

S2 = OGF.MeshGrob('S2')
S2.I.Shapes.create_sphere(center=[0.5,0,0])

# Compute the intersection between the two spheres
Intersection = OGF.MeshGrob('Intersection')
S1.I.Surface.compute_intersection(other=S2,result=Intersection)

# Polyscope display
ps.init()
register_graphite_objects(scene_graph)

# Change some polyscope graphic attributes to better show the result
ps.get_surface_mesh('S1').set_transparency(0.5)
ps.get_surface_mesh('S2').set_transparency(0.5)
ps.get_surface_mesh('Intersection').set_edge_width(2)

ps.show()
