# HelloBooleanOps4:
# More options (choose objects, animate, next/prev frame)
# Cleaner code, create an Application class, no globals

import polyscope as ps
import numpy as np
import gompy
import math
import time

OGF = gom.meta_types.OGF # shortcut

# constants for boolean ops and shapes
UNION=0; INTERSECTION=1; DIFFERENCE=2
SPHERE=0; CUBE=1; ICOSAHEDRON=2

class MyApplication:
        def __init__(self):
            self.scene_graph = OGF.SceneGraph()
            self.running = True
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
            else:
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
            nv = R.I.Editor.nb_vertices
            nf = R.I.Editor.nb_facets
            ps.imgui.Text('Result of boolean operation:')
            ps.imgui.Text('   vertices: ' + str(nv))
            ps.imgui.Text('     facets: ' + str(nf))

        def register_graphite_object(self, O: OGF.MeshGrob):
            """
            Registers a graphite object to Polyscope
            @param[in] O the graphite object to be registered
            """
            pts = np.asarray(O.I.Editor.find_attribute('vertices.point'))
            tri = np.asarray(O.I.Editor.get_triangles())
            ps.register_surface_mesh(O.name,pts,tri)

        def register_graphite_objects(self):
            """
            Registers all the graphite objects in a scene graph to Polyscope
            @param[in] scene_graph the Graphite scene graph
            """
            for objname in dir(self.scene_graph.objects):
                self.register_graphite_object(self.scene_graph.resolve(objname))

        def unregister_graphite_objects(self):
            """
            Unregisters all the graphite objects in a scene graph to Polyscope
            @param[in] scene_graph the Graphite scene graph
            """
            for objname in dir(self.scene_graph.objects):
                ps.remove_surface_mesh(objname)

        def show_scene(self,alpha=0.25):
            """
            The function called for each frame
            @param[in] alpha the shifting amount of both spheres
            """
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

        def main_loop(self):
            ps.init()
            # Tell polyscope that it should call our function in each frame
            ps.set_user_callback(self.draw_GUI)
            self.frame = 0
            while self.running:
                if self.animate:
                    self.frame = self.frame+1
                self.show_scene(math.sin(self.frame*0.1))
                ps.frame_tick()
                # Be nice with the CPU/computer, sleep a little bit
                time.sleep(0.01) # micro-sieste: 1/100th second

app = MyApplication()
app.main_loop()
