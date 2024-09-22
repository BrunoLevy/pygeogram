import polyscope as ps
import numpy as np
import gompy
import math

OGF = gom.meta_types.OGF
scene_graph = OGF.SceneGraph()
running = True
op = 1  # the operation, 0: union, 1: intersection, 2: difference
shape1 = 0; shape2 = 0 # 0: sphere 1: cube 2: icosahedron
show_input_shapes = True

def create_shape(shape: int, center: list, name: str) -> OGF.MeshGrob:
    """
    @brief creates a sphere, cube or icosahedron
    @param[in] shape one of 0: sphere, 1: cube, 2: icosahedron
    @param[in] center the center as a list of 3 coordinates
    @param[in] name the name of the mesh in the scene graph and in polyscope
    @return the newly created mesh
    """
    result = OGF.MeshGrob(name)
    result.I.Editor.clear()
    if(shape == 0):
        result.I.Shapes.create_sphere(center=center, radius=1.0, precision=3)
    elif(shape ==1):
        result.I.Shapes.create_box(
            [ center[0]-0.5, center[1]-0.5, center[2]-0.5],
            [ center[0]+0.5, center[1]+0.5, center[2]+0.5]
        )
        result.I.Surface.triangulate() # needed by boolean ops
    else:
        result.I.Shapes.create_icosahedron(center)
    return result

def draw_my_own_window():
    """
    Called by Polyscope to draw and handle additional windows
    """
    global running, op, shape1, shape2, scene_graph, show_input_shapes
    # The "quit" button
    if ps.imgui.Button('quit'):
        running = False

    ps.imgui.SameLine()
    _,show_input_shapes = ps.imgui.Checkbox('show inputs',show_input_shapes)

    # The combo-boxes to chose two shapes
    shapes = ['sphere','cube','icosahedron']
    _,shape1 = ps.imgui.Combo('shape 1',shape1,shapes)
    _,shape2 = ps.imgui.Combo('shape 2',shape2,shapes)

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
    global show_input_shapes
    unregister_graphite_objects(scene_graph)
    scene_graph.clear()
    S1 = create_shape(shape1, [0,0,-alpha], 'S1')
    S2 = create_shape(shape2, [0,0, alpha], 'S2')
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
    ps.get_surface_mesh('S1').set_enabled(show_input_shapes)
    ps.get_surface_mesh('S2').set_enabled(show_input_shapes)

ps.init()
# Tell polyscope that it should call our function in each frame
ps.set_user_callback(draw_my_own_window)


frame = 0
while running:
    frame = frame+1
    show_scene(math.sin(frame*0.1))
    ps.frame_tick()
