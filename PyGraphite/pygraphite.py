#!/usr/bin/env python

# TODO:
#  - Guizmo appears at a weird location (not always visible)
#  - Maybe the same "projection cube" as in Graphite to choose view
#  - multiple PolyScope objects for each Graphite object (points, borders,...) ?
#  - do not triangulate meshes with polygonal facets, triangulate them in View
#     (or in Interface ! Yes, let us do that...)
#  - a basic file browser
#  - commands that take attributes, get list from current object, as in Graphite
#  - I need a console to enter Python commands, with autocompletion of course
#  - Some messages are not displayed in the tty
#  - Reset view on first object
#  - Extract scalar attribute
#  - cleaner gom module, make it behave like standard Python module

import polyscope as ps, numpy as np
import sys
import gompy # always import gompy *after* polyscope

gom = gompy.interpreter()
OGF = gom.meta_types.OGF

from auto_gui import PyAutoGUI
from graphite_app import GraphiteApp

#=====================================================
# Graphite application

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
class MeshGrobPolyScopeCommands:
    
    # Python functions declared to Graphite need type hints,
    # so that the GUI can be automatically generated.
    # There are always two additional arguments that appear first:
    #   interface: the target of the function call
    #   method: a string with the name of the method called. It can be used
    #   to dispatch several slots to the same function
    # Note that Python functions declared to Graphite do not take self as
    #   argument (they are like C++ static class functions)
    def extract_component(
            interface : OGF.Interface,
            method    : str,
            attr_name : str,
            component : OGF.index_t
    ):
        # docstring is used to generate the tooltip, menu, and have additional
        # information attached to the "custom attributes" of the MetaMethod.
        """
        @brief sends component of a vector attribute to Polyscope
        @param[in] attr_name name of the attribute
        @param[in] component index of the component to be extracted
        @menu /Attributes/Polyscope
        @keep_structures True # see GraphiteApp.handle_queued_command()
        """
        None
        # TODO ...
        #grob = interface.grob
        #attr_array = np.asarray(
        #    grob.I.Editor.find_attribute('vertices.'+attr_name)
        #)
        #attr_array = attr_array[:,component]
        #graphite.structure_map[grob.name].add_scalar_quantity(
        #    attr_name+'['+str(component)+']', attr_array
        #)

    # Note the default value for the 'center' arg in the docstring
    # (it would have been better to let one put it with type hints,
    #  but I did not figure out a way of getting it from there)
    def flip_or_rotate(
            interface : OGF.Interface,
            method    : str,
            axis      : OGF.FlipAxis, # the new enum created above
            center    : bool
    ):
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
            
# register our new commands so that Graphite GUI sees them            
PyAutoGUI.register_commands(
    graphite.scene_graph, OGF.MeshGrob, MeshGrobPolyScopeCommands
)

#=====================================================
# Initialize Polyscope and enter app main loop
ps.set_program_name('PyGraphite/PolyScope')
ps.init()
ps.set_up_dir('z_up')
ps.set_front_dir('y_front')
graphite.run(sys.argv)
