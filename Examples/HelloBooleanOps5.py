# HelloBooleanOps4:
# More options (choose objects, animate, next/prev frame)
# Cleaner code, create an Application class, no globals

import polyscope as ps
import numpy as np
import gompy.types.OGF as OGF
import math
import time

# =============================================================================

class Application:
    """
    @brief A generic Polyscope/geogram application framework
    """

    def __init__(self):
       self.scene_graph = OGF.SceneGraph()
       self.running = True
       self.dirty = False

    def draw_scene(self):
        """
        @brief To be overloaded in subclasses
        """

    def draw_GUI(self):
        """
        @brief To be overloaded in subclasses
        """

    def register_graphite_object(self, O: OGF.MeshGrob):
        """
        @brief Registers a graphite object to Polyscope
        @param[in] O the graphite object to be registered
        """
        pts = np.asarray(O.I.Editor.find_attribute('vertices.point'))
        tri = np.asarray(O.I.Editor.get_triangles())
        ps.register_surface_mesh(O.name,pts,tri)

    def register_graphite_objects(self):
        """
        @brief Registers all the graphite objects in a scene graph to Polyscope
        @param[in] scene_graph the Graphite scene graph
        """
        for objname in dir(self.scene_graph.objects):
            self.register_graphite_object(self.scene_graph.resolve(objname))

    def unregister_graphite_objects(self):
        """
        @brief Unregisters all the graphite objects in a scene graph to Polyscope
        @param[in] scene_graph the Graphite scene graph
        """
        for objname in dir(self.scene_graph.objects):
            try:
               ps.remove_surface_mesh(objname)
            except:
               None

    def main_loop(self):
        """
        @brief The main application loop
        @details Initializes polyscope and displays the scene while application
          is running
        """
        ps.init()
        # Tell polyscope that it should call our function in each frame
        ps.set_user_callback(self.draw_GUI)
        self.frame = 0
        while self.running:
            self.draw_scene()
            ps.frame_tick()
            # Be nice with the CPU/computer, sleep a little bit
            time.sleep(0.01) # micro-sieste: 1/100th second

# =============================================================================

class MeshGrobOps:

    def scale_object(o: OGF.MeshGrob, s):
        vertices = np.asarray(o.I.Editor.get_points())
        vertices *= s

    def translate_object(o: OGF.MeshGrob, T: np.ndarray):
        vertices = np.asarray(o.I.Editor.get_points())
        vertices += T

    def rotate_object(o: OGF.MeshGrob, alpha):
        c = math.cos(alpha)
        s = math.sin(alpha)
        M = np.array(
            [[c,   0.0,   s],
             [0.0, 1.0, 0.0],
             [-s,   0.0,  c],
            ]
        );
        vertices = np.asarray(o.I.Editor.get_points())
        np.matmul(vertices,M,vertices)

# =============================================================================

# constants for boolean ops and shapes
UNION=0; INTERSECTION=1; DIFFERENCE=2

SPHERE=0; CUBE=1; ICOSAHEDRON=2; CYLINDER=3



class MyApplication(Application):

    def __init__(self):
        super().__init__()
        self.op = 1
        self.shape1 = SPHERE
        self.shape2 = CUBE
        self.animate = False
        self.frame = 0
        self.reset()

    def set_shape(self, mesh: OGF.MeshGrob, shape: int):
        center = [0,0,0]
        mesh.I.Editor.clear()
        if shape == SPHERE:
            mesh.I.Shapes.create_sphere(
                center, radius=1.0, precision=2
            )
        elif shape == CUBE:
            mesh.I.Shapes.create_box(
                [ center[0]-0.5, center[1]-0.5, center[2]-0.5],
                [ center[0]+0.5, center[1]+0.5, center[2]+0.5]
            )
            mesh.I.Surface.triangulate() # needed by boolean ops
        elif shape == ICOSAHEDRON:
            mesh.I.Shapes.create_icosahedron(center)
        elif shape == CYLINDER:
            mesh.I.Shapes.create_cylinder_from_extremities(
                [0,-1.5,0],[0,1.5,0],1.0,30
            )
            mesh.I.Surface.triangulate() # needed by boolean ops

    def draw_GUI(self):
        if ps.imgui.Button('quit'):
            self.running = False

        ps.imgui.SameLine()
        if ps.imgui.Button('reset'):
            self.reset()

        ps.imgui.SameLine()
        _,self.animate = ps.imgui.Checkbox('animate',self.animate)

        if not self.animate:
            ps.imgui.SameLine()
            if ps.imgui.Button('<'):
                self.step_backward()
            ps.imgui.SameLine()
            if ps.imgui.Button('>'):
                self.step_forward()

        # The combo-boxes to chose two shapes
        shapes = ['sphere','cube','icosahedron', 'cylinder']
        _,self.shape1 = ps.imgui.Combo('shape 1',self.shape1,shapes)
        _,self.shape2 = ps.imgui.Combo('shape 2',self.shape2,shapes)

        # The combo-box to chose the boolean operation
        ops = ['union','intersection','difference']
        _,self.op = ps.imgui.Combo('operation',self.op,ops)

        # Display number of vertices and facets in result mesh
        R = self.scene_graph.objects.R
        if R != None:
            nv = R.I.Editor.nb_vertices
            nf = R.I.Editor.nb_facets
            ps.imgui.Text('Result of boolean operation:')
            ps.imgui.Text('   vertices: ' + str(nv))
            ps.imgui.Text('     facets: ' + str(nf))

    def reset(self):
        self.frame = 0
        self.scene_graph.clear()
        self.S1 = OGF.MeshGrob('S1')
        self.set_shape(self.S1, self.shape1)
        self.S2 = OGF.MeshGrob('S2')
        self.set_shape(self.S2, self.shape2)
        self.R = OGF.MeshGrob('R')
        self.set_shape(self.R, self.shape1)
        MeshGrobOps.translate_object(self.S2,[1,0,0])

    def step_forward(self):
        self.frame = self.frame+1
        self.dirty = True

    def step_backward(self):
        self.frame = self.frame-1
        self.dirty = True

    def update(self):
        MESH_BOOL_OPS_DEFAULT = 0
        MESH_BOOL_OPS_VERBOSE = 1
        MESH_BOOL_OPS_ATTRIBS = 2
        MESH_BOOL_OPS_NO_SIMPLIFY = 4
        MESH_BOOL_OPS_NO_CHECK_NEIGHBORS = 8
        if not self.dirty:
            return
        self.S2.clear()
        self.set_shape(self.S2, self.shape2)
        MeshGrobOps.scale_object(self.S2,0.3)
        MeshGrobOps.translate_object(
            self.S2,[1.0+0.05*(math.sin(self.frame*0.01)),0,0]
        )
        MeshGrobOps.translate_object(
            self.S2,[0,0.7*math.sin(self.frame*0.01),0]
        )
        MeshGrobOps.rotate_object(self.S2,0.1*self.frame)
        self.R.I.Mesh.copy('S1')
        self.S1.I.Surface.compute_boolean_operation(
            self.S2, self.R, 'A-B',
            False, False,
            MESH_BOOL_OPS_NO_CHECK_NEIGHBORS
        )
        self.dirty = False

    def draw_scene(self):
        self.unregister_graphite_objects()
        self.update()
        self.register_graphite_objects()
        ps.get_surface_mesh('S1').set_transparency(0.5)
        ps.get_surface_mesh('S2').set_transparency(0.5)
        ps.get_surface_mesh('R').set_edge_width(1.3)
        if self.animate:
            self.step_forward()

# =============================================================================

app = MyApplication()
app.main_loop()
