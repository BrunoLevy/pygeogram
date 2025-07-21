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
            ps.remove_surface_mesh(objname)

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

# constants for boolean ops and shapes
UNION=0; INTERSECTION=1; DIFFERENCE=2
SPHERE=0; CUBE=1; ICOSAHEDRON=2

class MyApplication(Application):

    def __init__(self):
        super().__init__()
        self.op = 1
        self.shape1 = 0
        self.shape2 = 0
        self.animate = True
        self.show_input_shapes = True
        self.frame = 0

    def create_shape(
        self, shape: int, center: list, name: str
    ) -> OGF.MeshGrob:
        """
        @brief creates a sphere, cube or icosahedron
        @param[in] shape one of SPHERE, CUBE, ICOSAHEDRON
        @param[in] center the center as a list of 3 coordinates [x, y, z]
        @param[in] name the name of the mesh in the scene graph
        @return the newly created mesh
        """
        result = OGF.MeshGrob(name)
        result.I.Editor.clear()
        if shape == SPHERE:
            result.I.Shapes.create_sphere(
                center=center, radius=1.0, precision=3
            )
        elif shape == CUBE:
            result.I.Shapes.create_box(
                [ center[0]-0.5, center[1]-0.5, center[2]-0.5],
                [ center[0]+0.5, center[1]+0.5, center[2]+0.5]
            )
            result.I.Surface.triangulate() # needed by boolean ops
        elif shape == ICOSAHEDRON:
            result.I.Shapes.create_icosahedron(center)
        return result

    def draw_GUI(self):
        """
        Called by Polyscope to draw and handle additional windows
        """
        # The "quit" button
        if ps.imgui.Button('quit'):
            self.running = False

        ps.imgui.SameLine()
        _,self.show_input_shapes = ps.imgui.Checkbox(
            'show inputs',self.show_input_shapes
        )

        ps.imgui.SameLine()
        _,self.animate = ps.imgui.Checkbox('animate',self.animate)

        if not self.animate:
            ps.imgui.SameLine()
            if ps.imgui.Button('<'):
                self.frame = self.frame - 1
            ps.imgui.SameLine()
            if ps.imgui.Button('>'):
                self.frame = self.frame + 1

        # The combo-boxes to chose two shapes
        shapes = ['sphere','cube','icosahedron']
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

    def draw_scene(self,alpha=0.25):
        """
        The function called for each frame
        @param[in] alpha the shifting amount of both spheres
        """
        alpha = math.sin(self.frame*0.1)
        self.unregister_graphite_objects()
        self.scene_graph.clear()
        S1 = self.create_shape(self.shape1, [0,0,-alpha], 'S1')
        S2 = self.create_shape(self.shape2, [0,0, alpha], 'S2')
        R = OGF.MeshGrob('R')
        if self.op == UNION:
            S1.I.Surface.compute_union(S2,R)
        elif self.op == INTERSECTION:
            S1.I.Surface.compute_intersection(S2,R)
        elif self.op == DIFFERENCE:
            S1.I.Surface.compute_difference(S2,R)
        self.register_graphite_objects()
        ps.get_surface_mesh('S1').set_transparency(0.5)
        ps.get_surface_mesh('S2').set_transparency(0.5)
        ps.get_surface_mesh('R').set_edge_width(2)
        ps.get_surface_mesh('S1').set_enabled(self.show_input_shapes)
        ps.get_surface_mesh('S2').set_enabled(self.show_input_shapes)
        if self.animate:
            self.frame = self.frame+1

# =============================================================================

app = MyApplication()
app.main_loop()
