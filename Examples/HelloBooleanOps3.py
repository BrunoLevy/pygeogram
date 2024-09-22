# HelloBooleanOps3:
# Adding a new Polyscope window and interactive controls to change the
# boolean operation

import polyscope as ps
import numpy as np
import gompy
import math

OGF = gom.meta_types.OGF
scene_graph = OGF.SceneGraph()
running = True
op = 1  # the operation, 0: union, 1: intersection, 2: difference

def draw_GUI():
    """
    @brief Called by Polyscope to draw and handle additional windows
    """
    global running, op, scene_graph
    # The "quit" button
    if ps.imgui.Button('quit'):
        running = False
    # The combo-box to chose the boolean operation
    ops = ['union','intersection','difference']
    _,op = ps.imgui.Combo('operation',op,ops)
    # Display number of vertices and facets in result mesh
    R = scene_graph.objects.R
    nv = R.I.Editor.nb_vertices
    nf = R.I.Editor.nb_facets
    ps.imgui.Text('Result of boolean operation:')
    ps.imgui.Text('   vertices: ' + str(nv))
    ps.imgui.Text('     facets: ' + str(nf))

# ---------------------- Same as before --------------------------------

def register_graphite_object(O: OGF.MeshGrob):
   """
   @brief Registers a graphite object to Polyscope
   @param[in] O the graphite object to be registered
   """
   pts = np.asarray(O.I.Editor.find_attribute('vertices.point'))
   tri = np.asarray(O.I.Editor.get_triangles())
   ps.register_surface_mesh(O.name,pts,tri)

def register_graphite_objects(scene_graph: OGF.SceneGraph):
   """
   @brief Registers all the graphite objects in a scene graph to Polyscope
   @param[in] scene_graph the Graphite scene graph
   """
   for objname in dir(scene_graph.objects):
       register_graphite_object(scene_graph.resolve(objname))

def unregister_graphite_objects(scene_graph: OGF.SceneGraph):
   """
   @brief Unregisters all the graphite objects in a scene graph to Polyscope
   @param[in] scene_graph the Graphite scene graph
   """
   for objname in dir(scene_graph.objects):
       ps.remove_surface_mesh(objname)

# ----------------------------------------------------------------------

def draw_scene(alpha=0.25):
    """
    @brief The function called for each frame
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
    if op == 0:
       S1.I.Surface.compute_union(S2,R)
    elif op == 1:
       S1.I.Surface.compute_intersection(S2,R)
    elif op == 2:
       S1.I.Surface.compute_difference(S2,R)
    register_graphite_objects(scene_graph)
    ps.get_surface_mesh('S1').set_transparency(0.5)
    ps.get_surface_mesh('S2').set_transparency(0.5)
    ps.get_surface_mesh('R').set_edge_width(2)

ps.init()
# Tell polyscope that it should call our function in each frame
ps.set_user_callback(draw_GUI)


frame = 0
while running:
    frame = frame+1
    draw_scene(math.sin(frame*0.1))
    ps.frame_tick()
