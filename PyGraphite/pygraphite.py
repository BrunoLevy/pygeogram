#!/usr/bin/env python

# TODO:
#  - Error messages, lock graphics
#  - Guizmo appears at a weird location (not always visible)
#  - Maybe the same "projection cube" as in Graphite to choose view
#  - multiple PolyScope objects for each Graphite object (points, borders,...) ?
#  - visualize vector fields
#  - commands that take attributes, get list from current object, as in Graphite
#      (parse special attributes)
#  - Some messages are not displayed in the tty
#  - Reset view on first object
#  - Splitter between scenelist and command

import polyscope as ps, numpy as np # of course we need these two ones
import sys                          # to get command line args
import gompy                        # always import gompy *after* polyscope

gom = gompy.interpreter()
OGF = gom.meta_types.OGF

from auto_gui      import PyAutoGUI   # to declare new Graphite cmds in Python
from graphite_app  import GraphiteApp # of course we need this one
from mesh_grob_ops import MeshGrobOps # some geometric xforms in Python

#=====================================================
# Create the graphite application

graphite = GraphiteApp()

#======================================================

# Extend Graphite in Python !
# Add custom commands to Graphite Object Model, so that
# they appear in the menus, exactly like native Graphite
# commands written in C++

# Declare a new enum type
PyAutoGUI.register_enum(
    'OGF::FlipAxis',
    ['FLIP_X','FLIP_Y','FLIP_Z','ROT_X','ROT_Y','ROT_Z','PERM_XYZ']
)

# Declare a new Commands class for MeshGrob
# The name should be something like MeshGrobXXXCommands
class MeshGrobPyGraphiteCommands:

    # You can add your own functions here, take a look at
    # the following ones to have an idea of how to do that.
    # Python functions declared to Graphite need type hints,
    # so that the GUI can be automatically generated.
    # There are always two additional arguments that appear first:
    # -interface: the target of the function call
    # -method: a string with the name of the method called. It can be used
    #  to dispatch several slots to the same function (but we don't do that here)
    # Note that Python functions declared to Graphite do not take self as
    #  argument (they are like C++ static class functions)
    # Note the default value for the 'axis' and 'center' args in the docstring
    # (it would have been better to let one put it with type hints,
    #  but I did not figure out a way of getting it from there)
    def flip_or_rotate(
        interface : OGF.Interface,
        method    : str,
        axis      : OGF.FlipAxis, # the new enum created above
        center    : bool
    ):
        # docstring is used to generate the tooltip, menu, and have additional
        # information attached to the "custom attributes" of the MetaMethod.
        """
        @brief flips axes of an object or rotate around an axis
        @param[in] axis = PERM_XYZ rotation axis or permutation
        @param[in] center = True if set, xform is relative to object's center
        @menu /Mesh
        """

        # the Graphite object target of the command is obtained like that:
        grob = interface.grob

        if center:
            C = MeshGrobOps.get_object_center(grob)
            # MeshGrobOps are also implemented in Python, with numpy !
            # (see mesh_grob_ops.py)
            MeshGrobOps.translate_object(grob, -C)

        # points array can be modified in-place !
        # (for that, note pts_array[:,[0,1,2]] instead of just pts_array)
        pts_array = np.asarray(grob.I.Editor.get_points())
        if   axis == 'FLIP_X':
            pts_array[:,0] = -pts_array[:,0]
        elif axis == 'FLIP_Y':
            pts_array[:,1] = -pts_array[:,1]
        elif axis == 'FLIP_Z':
            pts_array[:,2] = -pts_array[:,2]
        elif axis == 'ROT_X':
            pts_array[:,[0,1,2]] = pts_array[:,[0,2,1]]
            pts_array[:,1] = -pts_array[:,1]
        elif axis == 'ROT_Y':
            pts_array[:,[0,1,2]] = pts_array[:,[2,1,0]]
            pts_array[:,2] = -pts_array[:,2]
        elif axis == 'ROT_Z':
            pts_array[:,[0,1,2]] = pts_array[:,[1,0,2]]
            pts_array[:,0] = -pts_array[:,0]
        elif axis == 'PERM_XYZ':
            pts_array[:,[0,1,2]] = pts_array[:,[1,2,0]]

        if center:
            MeshGrobOps.translate_object(grob, C)

        grob.update() # updates the PolyScope structures in the view

    def randomize(
        interface : OGF.Interface,
        method    : str,
        howmuch   : float
    ):
        """
        @brief Applies a random perturbation to the vertices of a mesh
        @param[in] howmuch = 0.01 amount of perturbation rel to bbox diag
        @menu /Mesh
        """
        grob = interface.grob
        howmuch = howmuch * MeshGrobOps.get_object_bbox_diagonal(grob)
        pts = np.asarray(grob.I.Editor.get_points())
        pts += howmuch * np.random.rand(*pts.shape)
        grob.update()

    def inflate(
        interface : OGF.Interface,
        method    : str,
        howmuch   : float
    ):
        """
        @brief Inflates a surface by moving its vertices along the normal
        @param[in] howmuch = 0.01 inflating amount rel to bbox diag
        @menu /Surface
        """
        grob = interface.grob
        howmuch = howmuch * MeshGrobOps.get_object_bbox_diagonal(grob)
        grob.I.Attributes.compute_vertices_normals('normal')
        pts = np.asarray(grob.I.Editor.get_points())
        N   = np.asarray(grob.I.Editor.find_attribute('vertices.normal'))
        pts += howmuch * N
        grob.update()

    def mesh_as_tubes(
        interface  : OGF.Interface,
        method     : str,
        new_mesh   : OGF.NewMeshGrobName,
        cyl_radius : float,
        sph_radius : float,
        cyl_prec   : int,
        sph_prec   : int
    ):
        """
        @brief Creates a surface with edges as cylinders
        @param[in] new_mesh = tubes new mesh name
        @param[in] cyl_radius = 0.002  cylinders radius rel to bbox diag or 0
        @param[in] sph_radius = 0.003 spheres radius rel to bbox diag or 0
        @advanced
        @param[in] cyl_prec = 10 cylinder precision
        @param[in] sph_prec = 2  sphere precision
        """
        grob = interface.grob
        R = MeshGrobOps.get_object_bbox_diagonal(grob)
        cyl_radius = cyl_radius * R
        sph_radius = sph_radius * R
        if grob.scene_graph().is_bound(new_mesh):
            tubes = grob.scene_graph().resolve(new_mesh)
            tubes.I.Editor.clear()
        else:
            tubes = OGF.MeshGrob(new_mesh)

        tubes.disable_signals()

        points = np.asarray(grob.I.Editor.get_points())
        triangles = np.asarray(grob.I.Editor.get_triangles())

        # Get all the edges of all triangles
        edges = np.concatenate(
            (triangles[:,[0,1]],
             triangles[:,[1,2]],
             triangles[:,[2,0]]),
            axis=0
        )

        # Remove duplicates
        keep_edges = (edges[:,0] > edges[:,1])
        edges = edges[keep_edges]

        # Lookup vertices
        edges_points = np.take(points, edges, axis=0)

        if cyl_radius != 0.0:
            # Can we avoid this loop ?
            for i in range(edges_points.shape[0]):
                p1 = edges_points[i][0]
                p2 = edges_points[i][1]
                tubes.I.Shapes.create_cylinder_from_extremities(
                    p1, p2, cyl_radius, cyl_prec
                )

        if sph_radius != 0.0:
            # Can we avoid this loop ?
            for i in range(points.shape[0]):
                p = points[i]
                tubes.I.Shapes.create_sphere(
                    p, sph_radius, sph_prec
                )

        tubes.enable_signals()
        tubes.update()


    def show_component_attribute(
        interface : OGF.Interface,
        method    : str,
        attribute : str,
        component : OGF.index_t
    ):
        """
        @brief sends a component of a vector attribute to Polyscope
        @param[in] attribute name of the attribute
        @param[in] component index of the component to be extracted
        @menu /Attributes/Polyscope
        """
        grob = interface.grob
        view = graphite.scene_graph_view.get_view(grob)
        view.show_component_attribute(attribute,component)
        grob.update()

    def create_icosahedron(
        interface  : OGF.Interface,
        method     : str
    ):
        """
        @brief replaces the current mesh with a unit icosahedron
        """
        pts = np.array(
            [[ 0.        , 0.        , 1.175571 ],
             [ 1.051462  , 0.        , 0.5257311],
             [ 0.3249197 , 1.        , 0.5257311],
             [-0.8506508 , 0.618034  , 0.5257311],
             [-0.8506508 ,-0.618034  , 0.5257311],
             [ 0.3249197 ,-1.        , 0.5257311],
             [ 0.8506508 , 0.618034  ,-0.5257311],
             [ 0.8506508 ,-0.618034  ,-0.5257311],
             [-0.3249197 , 1.        ,-0.5257311],
             [-1.051462  , 0.        ,-0.5257311],
             [-0.3249197 ,-1.        ,-0.5257311],
             [ 0.        , 0.        ,-1.175571 ]])

        tri = np.array(
            [[ 0 , 1 , 2],
             [ 0 , 2 , 3],
             [ 0 , 3 , 4],
             [ 0 , 4 , 5],
             [ 0 , 5 , 1],
             [ 1 , 5 , 7],
             [ 1 , 7 , 6],
             [ 1 , 6 , 2],
             [ 2 , 6 , 8],
             [ 2 , 8 , 3],
             [ 3 , 8 , 9],
             [ 3 , 9 , 4],
             [ 4 , 9 ,10],
             [ 4 ,10 , 5],
             [ 5 ,10 , 7],
             [ 6 , 7 ,11],
             [ 6 ,11 , 8],
             [ 7 ,10 ,11],
             [ 8 ,11 , 9],
             [ 9 ,11 ,10]], dtype=np.uint32)

        grob = interface.grob
        MeshGrobOps.set_triangle_mesh(grob, pts, tri)

    def create_UV_sphere(
            interface  : OGF.Interface,
            method     : str,
            ntheta     : int,
            nphi       : int
    ):
        """
        @brief replaces the current mesh with a sphere
        @param[in] ntheta = 20 number of subdivisions around equator
        @param[in] nphi = 10 number of subdivisions around meridian
        """
        MeshGrobOps.set_parametric_surface(
            interface.grob,
            lambda U,V: (np.cos(U)*np.cos(V),np.sin(U)*np.cos(V),np.sin(V)),
            ntheta, nphi,
            0.0, 2.0*np.pi,
            -0.5*np.pi, 0.5*np.pi
        )

# register our new commands so that Graphite GUI sees them
PyAutoGUI.register_commands(
    graphite.scene_graph, OGF.MeshGrob, MeshGrobPyGraphiteCommands
)

#=====================================================
# Initialize Polyscope and enter app main loop
ps.set_program_name('PyGraphite/PolyScope')
ps.init()
ps.set_up_dir('z_up')
ps.set_front_dir('y_front')
graphite.run(sys.argv) # Let's rock and roll !
