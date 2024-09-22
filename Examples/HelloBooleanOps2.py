# HelloBooleanOps2:
# Computing boolean ops for moving objects is more fun !

import polyscope as ps
import numpy as np
import gompy
import math

OGF = gom.meta_types.OGF
scene_graph = OGF.SceneGraph()

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

# new function to unregister Graphite objects from PolyScope
def unregister_graphite_objects(scene_graph: OGF.SceneGraph):
   """
   Unregisters all the graphite objects in a scene graph to Polyscope
   @param[in] scene_graph the Graphite scene graph
   """
   for objname in dir(scene_graph.objects):
       ps.remove_surface_mesh(objname)

# ----------------------------------------------------------------------

def show_scene(alpha=0.25):
    """
    The function called for each frame
    @param[in] alpha the shifting amount of both spheres
    """
    unregister_graphite_objects(scene_graph)
    scene_graph.clear()
    S1 = OGF.MeshGrob('S1')
    S1.I.Shapes.create_sphere(
        center=[alpha, 0, 0], precision=3
    )
    S2 = OGF.MeshGrob('S2')
    S2.I.Shapes.create_sphere(
        center=[-alpha, 0, 0], precision=3
    )
    R = OGF.MeshGrob('R')
    S1.I.Surface.compute_intersection(S2,R)
    register_graphite_objects(scene_graph)
    ps.get_surface_mesh('S1').set_transparency(0.5)
    ps.get_surface_mesh('S2').set_transparency(0.5)
    ps.get_surface_mesh('R').set_edge_width(2)

ps.init()

# instead of calling ps.show(), we have our own display loop,
# that updates the scene at each frame. At the end of the
# frame, we call ps.frame_tick() to let PolyScope display the frame.
frame = 0
while True:
    frame = frame+1
    show_scene(math.sin(frame*0.1))
    ps.frame_tick()
