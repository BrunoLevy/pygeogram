import polyscope as ps
import numpy as np
import time

import gompy
gom = gompy.interpreter()
OGF = gom.meta_types.OGF

from mesh_grob_ops import MeshGrobOps

#==== PolyScope display for Graphite objects ==============================

class GrobView:
    """ @brief Manages PolyScope structures associated with Graphite objects """

    def __init__(self, grob : OGF.Grob):
        """
        @brief GrobView constructor
        @param[in] grob the Grob this GrobView is associated with
        """
        self.grob = grob
        self.connection = gom.connect(grob.value_changed,self.update)
        self.visible = True

    def __del__(self):
        """
        @brief GrobView destructor
        @details removes PolyScope structures associated with this view
        """
        self.remove()

    def show(self):
        """
        @brief Shows this view
        """
        self.visible = True

    def hide(self):
        """
        @brief Hides this view
        """
        self.visible = False

    def update(self,grob):
        """
        @brief Reconstructs PolyScope structures
        @brief Called whenever the associated Grob changes
        """
        None

    def remove(self):
        """
        @brief Removes this View
        @details Called whenever the associated Grob no longer exists
        """
        if self.connection != None:
            self.connection.remove() # Important! don't leave pending connections
        self.connection = None

    def commit_transform(self):
        """
        @brief Applies transforms in PolyScope guizmos to Graphite objects
        """
        None

    def highlight(self):
        """
        @brief Briefly change object colors to highlight it
        """
        None

    def unhighlight(self):
        """
        @brief Restore previous colors of highlighted object
        """
        None

    def get_structure_params(self, structure = None) -> dict:
        """
        @brief Gets parameters of a PolyScope structure
        @details Parameters are what have a get_xxx and set_xxx functions
        @param[in] structure an optional PolyScope structure, if unspecified
          it is taken from self.structure
        @return a dictionary with the parameters
        """
        if structure == None:
            structure = self.structure
        params = {}
        for getter_name in dir(structure):
            if (
                    getter_name.find('buffer') == -1 and
                    getter_name != 'get_ignore_slice_plane' and
                    getter_name.startswith('get_')
            ):
                param_name = getter_name.removeprefix('get_')
                setter_name = 'set_'+param_name
                if hasattr(structure, setter_name):
                    param_val = getattr(structure, getter_name)()
                    params[param_name] = param_val
        return params

    def set_structure_params(self, params, structure=None):
        """
        @brief Sets parameters of a PolyScope structure
        @details Parameters are what have a get_xxx and set_xxx functions
        @param[in] params a dictionary with the parameters
        @param[in] structure an optional PolyScope structure, if unspecified
          it is taken from self.structure
        """
        if structure == None:
            structure = self.structure
        for k,v in params.items():
            setter_name = 'set_' + k
            if hasattr(self.structure, setter_name):
                getattr(structure,setter_name)(v)

    def copy_polyscope_params_to_grob(self):
        """
        @brief copies polyscope parameters from structure to graphite Grob
        """
        params = self.get_structure_params()
        for k,v in params.items():
            self.grob.set_grob_attribute('polyscope.'+k, str(v))

    def copy_grob_params_to_polyscope(self):
        """
        @brief copies polyscope parameters from graphite Grob to structure
               and resets Grob attributes
        """
        if self.structure == None:
            return
        for i in range(self.grob.nb_grob_attributes()):
            k = self.grob.ith_grob_attribute_name(i)
            v = self.grob.ith_grob_attribute_value(i)
            if not k.startswith('polyscope.') or v == '':
                continue

            # transform value from string to native type
            if v == 'True':                    # convert boolean
                v = True
            elif v == 'False':
                v = False
            elif v[0] == '(' and v[-1] == ')': # convert vector
                v = [ float(x) for x in v[1:-1].split(',') ]
            elif (
                    len(v) > 4 and
                    v[0:2] == '[[' and
                    v[-2:] == ']]'
            ):                                 # convert matrix
                v = v.replace('[',' ').replace(']',' ')
                v = [ float(x) for x in v.split() ]
                v = np.asarray(v).reshape(4,4)
            else:
                try:
                    v = float(v)               # convert float
                except:
                    None

            setter_name = 'set_'+k.removeprefix('polyscope.')
            try:
                if hasattr(self.structure,setter_name):
                    getattr(self.structure,setter_name)(v)
                    self.grob.set_grob_attribute(k,'') # reset grob attribute
            except:
                None

class MeshGrobView(GrobView):
    """ PolyScope view for MeshGrob """

    def __init__(self, o: OGF.MeshGrob):
        """
        @brief GrobView constructor
        @param[in] grob the MeshGrob this GrobView is associated with
        """
        super().__init__(o)
        self.structure = None
        self.old_attributes = []
        self.shown_attribute = ''
        self.component_attributes = []
        self.create_structures()

    def create_structures(self):
        """
        @brief Creates PolyScope structures
        """
        o = self.grob
        E = o.I.Editor
        pts = np.asarray(E.get_points())[:,0:3] # some meshes are in nD.

        if E.nb_facets == 0 and E.nb_cells == 0:
            if E.nb_vertices != 0:
                self.structure = ps.register_point_cloud(o.name,pts)
        elif E.nb_cells == 0:
            self.structure = ps.register_surface_mesh(
                o.name, pts,
                np.asarray(o.I.Editor.get_triangles())
            )
        else:
            self.structure = ps.register_volume_mesh(
                o.name, pts,
                np.asarray(o.I.Editor.get_tetrahedra())
            )

        if self.structure == None:
            return

        self.structure.set_enabled(self.visible)

        # Display scalar attributes
        new_attributes = self.grob.list_attributes('vertices','double',1)
        new_attributes = (
            [] if new_attributes == '' else new_attributes.split(';')
        )
        # If there is a new attribute, show it
        # (else keep shown attribute if any)
        for attr in new_attributes:
            if attr not in self.old_attributes:
                self.shown_attribute = attr
        for attr in new_attributes:
            attrarray = np.asarray(E.find_attribute(attr))
            self.structure.add_scalar_quantity(
                attr.removeprefix('vertices.'),
                attrarray, enabled = (attr == self.shown_attribute)
            )
        self.old_attributes = new_attributes

        # Display component attributes
        for (attr, component) in self.component_attributes:
            attrarray = np.asarray(E.find_attribute('vertices.'+attr))
            attrname = attr + '[' + str(component) + ']'
            self.structure.add_scalar_quantity(
                attrname, attrarray[:,component],
                enabled = (attrname == self.shown_attribute)
            )

    def remove_structures(self):
        """
        @brief Removes PolyScope structures
        """
        if self.structure != None:
            self.structure.remove()
        self.structure = None

    def remove(self):
        self.remove_structures()
        super().remove()

    def show(self):
        super().show()
        if self.structure == None:
            return
        self.structure.set_enabled(True)

    def hide(self):
        super().hide()
        if self.structure == None:
            return
        self.structure.set_enabled(False)

    def update(self,grob):
        super().update(grob)
        self.remove_structures()
        self.create_structures()

    def commit_transform(self):
        super().commit_transform()
        if self.structure == None:
            return
        xform = self.structure.get_transform()
        if not np.allclose(xform,np.eye(4)):
            MeshGrobOps.transform_object(self.grob,xform)
            self.structure.reset_transform()
            self.grob.update()

    def highlight(self):
        try:
            self.prev_color = self.structure.get_color()
            self.prev_edge_color = self.structure.get_edge_color()
            self.prev_edge_width = self.structure.get_edge_width()
            self.prev_material = self.structure.get_material()
            self.structure.set_color([0.1,0.1,0.1])
            self.structure.set_edge_color([1,1,0])
            self.structure.set_edge_width(1)
            self.structure.set_material('flat')
            self.structure.set_enabled(True)
        except:
            None

    def unhighlight(self):
        try:
            self.structure.set_color(self.prev_color)
            self.structure.set_edge_color(self.prev_edge_color)
            self.structure.set_edge_width(self.prev_edge_width)
            self.structure.set_material(self.prev_material)
            self.structure.set_enabled(self.visible)
        except:
            None

    def show_component_attribute(self, attribute : str, component : int):
        """
        @brief shows a component of a vector attribute
        @param[in] attribute the attribute name
        @param[in] component the component, in 0..dim
        """
        if (attribute, component) in self.component_attributes:
            gom.err('component attribute already shown')
            return
        attr = self.grob.I.Editor.find_attribute('vertices.'+attribute,True)
        if attr == None:
            gom.err('no such attribute')
            return
        if component >= attr.dimension:
            gom.err('component larger than attribute dimension')
            return
        self.shown_attribute = attribute + '[' + str(component) + ']'
        self.component_attributes.append((attribute,component))

#================================================================================

class VoxelGrobView(GrobView):
    """ PolyScope view for VoxelGrob """
    def __init__(self, o: OGF.VoxelGrob):
        super().__init__(o)
        self.structure = None
        self.create_structures()
        self.old_attributes = []
        self.shown_attribute = ''

    def create_structures(self):
        """
        @brief Creates PolyScope structures
        """
        E = self.grob.I.Editor
        bound_low = [ float(x) for x in E.origin.split()]
        U = [ float(x) for x in E.U.split()]
        V = [ float(x) for x in E.V.split()]
        W = [ float(x) for x in E.W.split()]
        bound_high = [bound_low[0] + U[0], bound_low[1]+V[1], bound_low[2]+W[2]]
        dims = [E.nu, E.nv, E.nw]
        self.structure = ps.register_volume_grid(
            self.grob.name, dims, bound_low, bound_high
        )
        self.structure.set_enabled(self.visible)
        new_attributes = self.grob.displayable_attributes
        new_attributes = (
            [] if new_attributes == '' else new_attributes.split(';')
        )
        # If there is a new attribute, show it
        # (else keep shown attribute if any)
        for attr in new_attributes:
            if attr not in self.old_attributes:
                self.shown_attribute = attr
        for attr in new_attributes:
            attrarray = np.asarray(E.find_attribute(attr))
            attrarray = attrarray.reshape(E.nu, E.nv, E.nw).transpose()
            self.structure.add_scalar_quantity(
                attr, attrarray, enabled = (self.shown_attribute == attr)
            )
        self.old_attributes = new_attributes

    def remove_structures(self):
        """
        @brief Removes PolyScope structures
        """
        if self.structure != None:
            self.structure.remove()
        self.structure = None

    def remove(self):
        self.remove_structures()
        super().remove()

    def show(self):
        super().show()
        if self.structure == None:
            return
        self.structure.set_enabled(True)

    def hide(self):
        super().hide()
        if self.structure == None:
            return
        self.structure.set_enabled(False)

    def update(self,grob):
        super().update(grob)
        self.remove_structures()
        self.create_structures()

    def highlight(self):
        try:
            self.prev_edge_color = self.structure.get_edge_color()
            self.prev_edge_width = self.structure.get_edge_width()
            self.structure.set_edge_color([1,1,0])
            self.structure.set_edge_width(1.5)
            self.structure.set_enabled(True)
        except:
            None

    def unhighlight(self):
        try:
            self.structure.set_edge_color(self.prev_edge_color)
            self.structure.set_edge_width(self.prev_edge_width)
            self.structure.set_enabled(self.visible)
        except:
            None

#===============================================================================

class SceneGraphView(GrobView):
    """
    @brief PolyScope view for Graphite SceneGraph
    @details Manages a dictionary that maps Grob names to PolyScope views
    """

    def __init__(self, grob: OGF.SceneGraph):
        """
        @brief SceneGraphView constructor
        @param[in] grob the SceneGraph this SceneGraphView is associated with
        """
        super().__init__(grob)
        self.view_map = {}
        gom.connect(grob.values_changed, self.update_objects)
        self.highlighted = None
        self.highlight_timestamp = 0.0

    def update_objects(self,new_list: str):
        """
        @brief Updates the list of objects
        @param[in] new_list the new list of objects as a ';'-separated string
        @details Called whenever the list of Graphite objects changed
        """

        old_list = list(self.view_map.keys())
        new_list = [] if new_list == '' else new_list.split(';')

        # Remove views for objects that are no longer there
        for objname in old_list:
            if objname not in new_list:
                self.view_map[objname].remove()
                del self.view_map[objname]

        # Create views for new objects
        for objname in new_list:
            object = getattr(self.grob.objects, objname)
            if objname not in self.view_map:
                viewclassname = (
                    object.meta_class.name.removeprefix('OGF::')+'View'
                )
                try:
                    self.view_map[objname] = globals()[viewclassname](object)
                except:
                    print('Error: ', viewclassname, ' no such view class')
                    self.view_map[objname] = GrobView(object) # dummy view

        # copy viewing parameters from loaded objects to polyscope
        self.copy_grob_params_to_polyscope()

    def show_all(self):
        """ @brief Shows all objects """
        for shd in self.view_map.values():
            shd.show()

    def hide_all(self):
        """ @brief Hides all objects """
        for shd in self.view_map.values():
            shd.hide()

    def show_only(self, obj: OGF.Grob):
        """
        @brief Shows only one object
        @param[in] obj the object to be shown, all other objects will be hidden
        """
        self.hide_all()
        self.view_map[obj.name].show()

    def commit_transform(self):
        super().commit_transform()
        for shd in self.view_map.values():
            shd.commit_transform()

    def highlight_object(self, o:OGF.Grob):
        if self.highlighted != None:
            self.view_map[self.highlighted].unhighlight()
        self.view_map[o.name].highlight()
        self.highlighted = o.name
        self.highlight_timestamp = time.time()

    def unhighlight_object(self):
        if self.highlighted == None:
            return
        if time.time() - self.highlight_timestamp > 0.25:
            self.view_map[self.highlighted].unhighlight()
            self.highlighted = None

    def copy_polyscope_params_to_grob(self):
        for v in self.view_map.values():
            v.copy_polyscope_params_to_grob()

    def copy_grob_params_to_polyscope(self):
        for v in self.view_map.values():
            v.copy_grob_params_to_polyscope()

    def get_view(self, o: OGF.Grob) -> GrobView:
        """
        @brief Gets the view associated with a graphite object
        @param[in] o: the object
        @return the GrobView associated with o
        """
        return self.view_map[o.name]

    def get_views(self):
        """
        @brief Gets all the views associated with a SceneGraph
        @return the list of views
        """
        return self.view_map.values()

#===========================================================
