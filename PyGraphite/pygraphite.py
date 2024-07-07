# TODO:
#  - Guizmo appears at a weird location (not always visible)
#  - Maybe the same "projection cube" as in Graphite to choose view
#  - Views for VoxelGrob
#  - multiple PolyScope objects for each Graphite object (points, borders,...) ?
#  - Attributes in views
#  - do not triangulate meshes with polygonal facets, triangulate them in View
#  - a basic file browser
#  - pulldown to change target object in a command
#  - commands that take attributes, get list from current object, as in Graphite
#  - I need a console to enter Python commands, with autocompletion of course
#  - Highlight selected
#  - Moveable Graphite windows
#  - Some messages are not displayed in the tty
#  - Reset view on first object

import polyscope as ps
import numpy as np
import gompy
import math,sys,time
import typing

OGF = gom.meta_types.OGF
imgui = ps.imgui

#=========================================================================

class MenuMap:
    """ Handles the menu hierarchy associated with a grob """
    def __init__(self, grob_meta_class : gom.meta_types.OGF.MetaClass):
        self.root = dict()
        grob_class_name = grob_meta_class.name
        commands_str = gom.get_environment_value(grob_class_name + '_commands')
        for command_class_name in commands_str.split(';'):
            # skipped, already in context menu
            if command_class_name != 'OGF::SceneGraphSceneCommands': 
                default_menu_name = command_class_name
                mclass = gom.resolve_meta_type(command_class_name)
                # Command may be associated with a base class, so we find
	        # the name of this base class in the 'grob_class_name' attribute
	        # of the Command and strip it to generate the menu name.
                default_menu_name = default_menu_name.removeprefix(
	            mclass.custom_attribute_value('grob_class_name')
	        )
                default_menu_name = default_menu_name.removesuffix('Commands')
                for i in range(mclass.nb_slots()):
                    mslot = mclass.ith_slot(i)
                    menu_name = default_menu_name
                    if(mslot.has_custom_attribute('menu')):
                       submenu_name = mslot.custom_attribute_value('menu')
                       submenu_name.removesuffix('/')
                       if submenu_name[0] == '/':
                          menu_name = submenu_name[1:]
                          # Comment for Graphite (not relevant here, but kept):
                          # Particular case: SceneGraph commands starting
                          # with '/', to be rooted in the menu bar,
                          # are stored in the '/menubar' menumap
                          # (and handled with specific code in
                          #  graphite_gui.draw_menu_bar())
                          if grob_meta_class.name == 'OGF::SceneGraph':
                             menu_name = 'menubar/'+menu_name
                       else:
                          menu_name = menu_name + '/' + submenu_name
                    # Skip Object and Node functions, we don't want them to
                    # appear in the GUI
                    if (
                        OGF.Object.find_member(mslot.name)==None
                            and
                        OGF.Node.find_member(mslot.name)  ==None
                    ):
                        self.insert(self.root, menu_name, mslot)   

    def draw_menus(
            self, o : OGF.Object, menudict : dict = None
    ) -> OGF.Request:
        """ Draws the menus stored in a menumap, 
            Returns a request if a menu item was selected """
        if menudict == None:
            menudict = self.root
        result = None
        for k,v in menudict.items():
            if isinstance(v,dict):
                if imgui.BeginMenu(k.replace('_',' ')):
                    submenu_result = self.draw_menus(o,v)
                    if submenu_result != None:
                        result = submenu_result
                    imgui.EndMenu()
            else:
                mslot = v
                mclass = mslot.container_meta_class()
                if imgui.MenuItem(k.replace('_',' ')):
                    result = getattr(o.query_interface(mclass.name),mslot.name)
                if (imgui.IsItemHovered() and
                    mslot.has_custom_attribute('help')):
                    imgui.SetTooltip(mslot.custom_attribute_value('help'))
        return result

    def insert(
            self,
            menu_dict : dict, menu_name : str,
            mslot : OGF.MetaSlot
    ) :
        """ Inserts an entry in the menumap """
        if menu_name == '':
            menu_dict[mslot.name] = mslot
        else:
            # get leading path component
            k = menu_name[0:(menu_name+'/').find('/')]
            if k not in menu_dict:
                menu_dict[k] = dict()
            menu_name = menu_name.removeprefix(k)
            menu_name = menu_name.removeprefix('/')
            self.insert(menu_dict[k], menu_name, mslot)
        
#=========================================================================

class ArgList(dict):
    """ A dictionary with attribute-like access """
    def __getattr__(self, key):
        return self[key]
    
    def __setattr__(self, key, value):
        self[key] = value

    def __dir__(self):
        return super().__dir__() + [str(k) for k in self.keys()]
    
#=========================================================================

class AutoGUI:
    """ Functions to generate the GUI from GOM meta-information """
    
    #========= GUI handlers for commands =================================
    
    def draw_command(request : OGF.Request, args : ArgList):
        """ Handles the GUI for a Graphite command """
        imgui.Text(
            'Command: ' + request.method().name.replace('_',' ')
        )
        if (imgui.IsItemHovered() and
            request.method().has_custom_attribute('help')):
            imgui.SetTooltip(
                request.method().custom_attribute_value('help')
            )

        mmethod = request.method()
        if mmethod.nb_args() != 0:
            nb_standard_args = 0
            has_advanced_args = False
            for i in range(mmethod.nb_args()):
                if AutoGUI.ith_arg_is_advanced(mmethod,i):
                    has_advanced_args = True
                else:
                    nb_standard_args = nb_standard_args + 1
            height = 25 + nb_standard_args * 25
            if has_advanced_args:
                height = height + 25
            imgui.BeginListBox('##Command',[-1,height])
            imgui.Spacing()
            imgui.Spacing()
            for i in range(mmethod.nb_args()):
                if not AutoGUI.ith_arg_is_advanced(mmethod,i):
                    tooltip = None
                    if mmethod.ith_arg_has_custom_attribute(i,'help'):
                       tooltip = mmethod.ith_arg_custom_attribute_value(i,'help')
                    AutoGUI.arg_handler(
                        args,
                        mmethod.ith_arg_name(i), mmethod.ith_arg_type(i), tooltip
                    )
            if has_advanced_args:
                if imgui.TreeNode(
                        'Advanced'+'##'+str(request.object())+'.'+mmethod.name
                ):
                    imgui.TreePop()
                    for i in range(mmethod.nb_args()):
                        if AutoGUI.ith_arg_is_advanced(mmethod,i):
                            tooltip = None
                            if mmethod.ith_arg_has_custom_attribute(i,'help'):
                                tooltip = mmethod.ith_arg_custom_attribute_value(
                                    i,'help'
                                )
                            AutoGUI.arg_handler(
                                args,
                                mmethod.ith_arg_name(i),
                                mmethod.ith_arg_type(i), tooltip
                            )
            imgui.EndListBox()

    def init_command_args(request : OGF.Request) -> ArgList:
        """ Initializes an ArgList with command arguments """
        args = ArgList()
        mmethod = request.method()
        # This additional arg makes the command display more information
        # in the terminal. It is not set for methods declared in Python
        # that need to have the exact same number of args.
        if not mmethod.meta_class.is_a(OGF.DynamicMetaSlot):
            args['invoked_from_gui'] = True
        # Initialize arguments, get default values as string, convert them to
        # correct type.
        for i in range(mmethod.nb_args()):
            val = ''
            if mmethod.ith_arg_has_default_value(i):
                val = mmethod.ith_arg_default_value_as_string(i)
            mtype = mmethod.ith_arg_type(i)
            if mtype.is_a(gom.meta_types.bool):
                if val == '':
                    val = False
                else:
                    val = (val == 'true' or val == 'True')
            elif (
                mtype.is_a(gom.meta_types.int) or
                mtype.is_a(OGF.index_t) or
                mtype.name == 'unsigned int'
            ):
                if val == '':
                    val = 0
                else:
                    val = int(val)
            elif mmethod.ith_arg_type(i).is_a(gom.meta_types.float):
                if val == '':
                    val = 0.0
                else:
                    val = float(val)
            args[mmethod.ith_arg_name(i)] = val
        return args

    #========================================================================
    
    def ith_arg_is_advanced(
            mmethod: OGF.MetaMethod, i: int
    ) -> bool:
        """ Tests whether an argument of a method is declared as advanced """
        if not mmethod.ith_arg_has_custom_attribute(i,'advanced'):
           return False
        return (mmethod.ith_arg_custom_attribute_value(i,'advanced') == 'true')
    
    #========= GUI handlers for command args and properties ==============
    
    def arg_handler(
            o: object, property_name: str,
            mtype: OGF.MetaType, tooltip
    ):
        """ Handles the GUI for a parameter """
        if tooltip == None:
            tooltip = ''
        if mtype.meta_class.is_a(OGF.MetaEnum):
            AutoGUI.enum_handler(o, property_name, mtype, tooltip)
            return
        handler_name = mtype.name.replace(' ','_').replace(':','_') + '_handler'
        if hasattr(AutoGUI, handler_name):
            getattr(AutoGUI, handler_name)(o,property_name, mtype, tooltip)
            return
        AutoGUI.string_handler(o, property_name, mtype, tooltip)
        
    def string_handler(
            o: object, property_name: str,
            mtype: OGF.MetaType, tooltip: str
    ):
        """ Handles the GUI for a string parameter """
        AutoGUI.label(property_name, tooltip)        
        imgui.SameLine()
        imgui.PushItemWidth(-20)
        val = getattr(o,property_name)
        _,val = imgui.InputText(
            '##properties##' + property_name, val
        )
        imgui.PopItemWidth()
        setattr(o,property_name,val)

    def bool_handler(
            o: object, property_name: str,
            mtype: gom.meta_types.bool, tooltip: str
    ):
        """ Handles the GUI for a boolean parameter """
        imgui.PushItemWidth(-1)
        val = getattr(o,property_name)
        _,val = imgui.Checkbox(
            property_name.replace('_',' '), val
        )
        if tooltip != None and imgui.IsItemHovered():
            imgui.SetTooltip(tooltip)
        imgui.PopItemWidth()
        setattr(o,property_name,val)

    def int_handler(
            o: object, property_name: str,
            mtype: OGF.MetaType, tooltip: str
    ):
        """ Handles the GUI for an integer parameter """
        AutoGUI.label(property_name, tooltip)
        imgui.SameLine()
        imgui.PushItemWidth(-20)
        val = getattr(o,property_name)
        _,val = imgui.InputInt(
            '##properties##' + property_name, val, 1
        )
        imgui.PopItemWidth()
        setattr(o,property_name,val)

    def unsigned_int_handler(
            o: object, property_name: str,
            mtype: OGF.MetaType, tooltip: str
    ):
        """ Handles the GUI for an unsigned integer parameter """
        AutoGUI.label(property_name, tooltip)
        imgui.SameLine()
        imgui.PushItemWidth(-20)
        val = getattr(o,property_name)
        if val < 0:
            val = 0
        _,val = imgui.InputInt(
            '##properties##' + property_name, val, 1
        )
        imgui.PopItemWidth()
        setattr(o,property_name,val)

    def OGF__MeshGrobName_handler(
            o: object, property_name: str,
            mtype: OGF.MeshGrobName, tooltip: str
    ):
        """ Handles the GUI for a MeshGrobName parameter """
        values = gom.get_environment_value('OGF::MeshGrob_instances')
        AutoGUI.combo_box(o, property_name, values, tooltip)

    def OGF__GrobClassName_handler(
            o: object, property_name: str,
            mtype: OGF.GrobClassName, tooltip: str
    ):
        """ Handles the GUI for a GrobClassName parameter """
        values = gom.get_environment_value('grob_types')
        AutoGUI.combo_box(o, property_name, values, tooltip)

    def enum_handler(
            o: object, property_name: str,
            menum: OGF.MetaEnum, tooltip: str
    ):
        """ Handles the GUI for an enum parameter """
        values = ''
        for i in range(menum.nb_values()):
            if i != 0:
                values = values + ';'
            values = values + menum.ith_name(i)
        AutoGUI.combo_box(o, property_name, values, tooltip)

    def combo_box(
            o: object, property_name: str,
            values: str, tooltip: str
    ):
        """ Handles the GUI with a combobox, 
            given the possible values in a ';'-separated string """
        AutoGUI.label(property_name, tooltip)
        if values=='':
            return
        if values[0] == ';':
            values = values[1:]
        values = values.split(';')

        old_value = getattr(o,property_name)
        found = True
        try:
            old_index = values.index(old_value)
        except:
            found = False
            old_index = 0
        imgui.SameLine()
        imgui.PushItemWidth(-20)
        _,new_index = imgui.Combo(
            '##properties##'+property_name, old_index, values
        )
        imgui.PopItemWidth()
        setattr(o,property_name,values[new_index])

    def label(property_name: str, tooltip: str):
        """ Draws the label of a parameter, 
            and a tooltip if help is available in meta info """
        imgui.Text(property_name.replace('_',' '))
        if tooltip != '' and imgui.IsItemHovered():
            imgui.SetTooltip(tooltip)

#=========================================================================

class PyAutoGUI:
    """ Python-AutoGUI interop """

    def register_enum(name: str, values: list):
        menum = OGF.MetaEnum.create(name)
        index = 0
        for value in values:
            menum.add_value(value, index)
            index = index + 1
        gom.bind_meta_type(menum)
        return menum
    
    def register_commands(
            scene_graph: OGF.SceneGraph,
            grobclass: OGF.MetaClass,
            methodsclass: type
    ):
        baseclass = gom.resolve_meta_type(grobclass.name + 'Commands')
        mclass = baseclass.create_subclass(
            'OGF::' + methodsclass.__name__
        )
        mclass.add_constructor()
        
        if hasattr(methodsclass,'__dict__'):
            methods = methodsclass.__dict__.keys() # preserves order 
        else:
            methods = dir(methodsclass)
            
        for method_name in methods:
            if (
                    not method_name.startswith('__') or
                    not method_name.endswith('__')
            ):
                pyfunc = getattr(methodsclass,method_name)
                mslot = PyAutoGUI.register_command(mclass, pyfunc)
        scene_graph.register_grob_commands(grobclass,mclass)
        return mclass

    def register_command(mclass: OGF.MetaClass, pyfunc: callable):
        # small table to translate standard Python types into
        # GOM metatypes
        python2gom = {
            str:   gom.meta_types.std.string,
            int:   gom.meta_types.int,
            float: gom.meta_types.float,
            bool:  gom.meta_types.bool
        }
        mslot = mclass.add_slot(pyfunc.__name__,pyfunc)
        for argname, argtype in typing.get_type_hints(pyfunc).items():
            if argtype in python2gom:
                argtype = python2gom[argtype]
            if (
                    argname != 'interface' and
                    argname != 'method'   and
                    argname != 'return'
            ):
                mslot.add_arg(argname, argtype)
        PyAutoGUI.parse_doc(mslot,pyfunc)
        return mslot
    
    def parse_doc(mslot: OGF.MetaSlot, pyfunc: callable):
        """ parses the docstring of a python callable 
            and uses it to document a GOM MetaSlot """

        if pyfunc.__doc__ == None:
            return 
        for line in pyfunc.__doc__.split('\n'):
            try:
                kw,val = line.split(maxsplit=1)
                kw = kw[1:] # remove leading '@'
                if kw == 'param[in]':
                    # get default value from docstring (I'd prefer to get
                    # it from function's signature but it does not seems
                    # to be possible in Python)
                    eqpos = val.find('=')
                    if eqpos == -1:
                        argname,argdoc = val.split(maxsplit=1)
                    else:
                        val = val.replace('=',' ')
                        argname,argdef,argdoc = val.split(maxsplit=2)
                        mslot.set_arg_default_value(argname, argdef)
                    mslot.set_arg_custom_attribute(argname, 'help', argdoc)
                elif kw == 'brief':
                    mslot.set_custom_attribute('help',val)
                else:
                    mslot.set_custom_attribute(kw, val)
            except:
                None

#==== low-level object access =============================================

class MeshGrobOps:
    def get_object_bbox(o):
        vertices = np.asarray(o.I.Editor.get_points())
        pmin=np.array(
            [np.min(vertices[:,0]),np.min(vertices[:,1]),np.min(vertices[:,2])]
        )
        pmax=np.array(
            [np.max(vertices[:,0]),np.max(vertices[:,1]),np.max(vertices[:,2])]
        )
        return pmin, pmax

    def get_object_center(o):
        pmin,pmax = MeshGrobOps.get_object_bbox(o)
        return 0.5*(pmin+pmax)
                
    def translate_object(o, T):
        vertices = np.asarray(o.I.Editor.get_points())
        vertices[:,0] = vertices[:,0] + T[0] 
        vertices[:,1] = vertices[:,1] + T[1] 
        vertices[:,2] = vertices[:,2] + T[2] 

    def transform_object(o, xform):
        """ Applies a 4x4 homogeneous coord transform to object's vertices """
        # if xform is identity, nothing to do
        if np.allclose(xform,np.eye(4)):
            return
        object_vertices = np.asarray(o.I.Editor.get_points())
        vertices = np.c_[  # add a column of 1
            object_vertices, np.ones(object_vertices.shape[0])
        ]
        # transform all the vertices
        vertices = np.matmul(vertices,np.transpose(xform))
        weights  = vertices[:,-1]                 # get 4th column
        weights  = weights[:,np.newaxis]          # make it a Nx1 matrix
        vertices = vertices[:,:-1]                # get the x,y,z coords
        vertices = vertices/weights               # divide the x,y,z coords by w
        # Could be written also in 1 line only (but less legible I think):
        #    vertices = vertices[:,:-1] / vertices[:,-1][:,np.newaxis]
        np.copyto(object_vertices,vertices)       # inject into graphite object

#==== PolyScope display for Graphite objects ==============================

class GrobView:
    """ Manages PolyScope structures associated with a Graphite object """
    
    def __init__(self, grob):
        self.grob = grob
        self.connection = gom.connect(grob.value_changed,self.update)
        self.visible = True

    def __del__(self):
        self.remove()
        
    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def update(self,grob):
        """ Called whenever the PolyScope structure should be updated """
        None

    def remove(self):
        """ Called whenever the associated Graphite object no longer exists """
        if self.connection != None:
            self.connection.remove() # Important ! do not leave pending connections
        self.connection = None

    def commit_transform(self):
        """ Applies transforms in PolyScope guizmos to Graphite objects """
        None
        
class MeshGrobView(GrobView):
    """ PolyScope view for MeshGrob """
    def __init__(self, o):
        super().__init__(o)
        self.structure = None
        self.create_structures()
        self.old_attributes = []
        self.shown_attribute = ''

    def create_structures(self):
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

        # Display scalar attributes
        if self.structure != None:
            new_attributes = self.grob.list_attributes('vertices','double',1)
            new_attributes = [] if new_attributes == '' else new_attributes.split(';')
            # If there is a new attribute, show it (else keep shown attribute if any)
            for attr in new_attributes:
                if attr not in self.old_attributes:
                    self.shown_attribute = attr
            for attr in new_attributes:
                attrarray = np.asarray(E.find_attribute(attr))
                self.structure.add_scalar_quantity(
                    attr.removeprefix('vertices.'),
                    attrarray, enabled=(attr == self.shown_attribute)
                )
            self.old_attributes = new_attributes
            

    def remove_structures(self):
        if self.structure != None:
            self.structure.remove()
        self.structure = None

    def remove(self):
        self.remove_structures()
        super().remove()
        
    def show(self):
        super().show()
        self.structure.set_enabled(True)

    def hide(self):
        super().hide()
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
            
class SceneGraphView(GrobView):
    def __init__(self, grob):
        super().__init__(grob)
        self.view_map = {}
        gom.connect(grob.values_changed, self.update_objects)

    def update_objects(self,new_list):
        """ Called whenever the list of Graphite objects changed """
        
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
                viewclassname = object.meta_class.name.removeprefix('OGF::')+'View'
                try:
                    self.view_map[objname] = globals()[viewclassname](object)
                except:
                    print('Error: ', viewclassname, ' no such view class')
                    self.view_map[objname] = GrobView(object) # creates a dummy view

    def show_all(self):
        for shd in self.view_map.values():
            shd.show()

    def hide_all(self):
        for shd in self.view_map.values():
            shd.hide()

    def show_only(self, obj):
        self.hide_all()
        self.view_map[obj.name].show()

    def commit_transform(self):
        super().commit_transform()
        for shd in self.view_map.values():
            shd.commit_transform()

#=========================================================================

class GraphiteApp:

    #===== Application logic =============================================

    # Callback for printing, redirected to terminal and for progress,
    # redirecting to progress bar
    # Since commands are queued and called outside PolyScope rendering function,
    # they can draw an additional frame in need be
    # (by calling PolyScope.frame_tick)
    
    def out_CB(self,str):
        self.print(str)
        while self.running and self.message_changed_frames > 0:
            ps.frame_tick() 

    def err_CB(self,str):
        self.show_terminal=True # make terminal appear if it was hidden
        self.print(str)
        while self.running and self.message_changed_frames > 0:
            ps.frame_tick()
            
    def progress_begin_CB(self,taskname):
        self.progress_task = taskname
        self.progress_percent = 0
        if self.running:
            ps.frame_tick()

    def progress_CB(self,progress_percent):
        self.progress_percent = progress_percent
        if self.running:
            ps.frame_tick()

    def progress_end_CB(self):
        self.progress_task = None
        if self.running:
            ps.frame_tick()

    # constructor
            
    def __init__(self):
        self.running = False
        
        self.menu_maps = {}
        self.reset_command()
        self.queued_execute_command = False # command execution is queued, for 
        self.queued_close_command   = False # making it happen out off ps CB
        
        self.scene_graph = OGF.SceneGraph.create()
        
        # create a Graphite ApplicationBase. It has the printing and
        # progress callbacks, that are redirected here to some functions
        # (ending with _CB).
        application = OGF.ApplicationBase.create()
        self.scene_graph.application = application

        # printing callbacks
        self.message = ''
        self.message_changed_frames = 0
        self.show_terminal = True
        gom.connect(application.out, self.out_CB)
        gom.connect(application.err, self.err_CB)

        # progress callbacks
        self.progress_task = None
        self.progress_percent = 0
        gom.connect(application.notify_progress_begin, self.progress_begin_CB)
        gom.connect(application.notify_progress,       self.progress_CB)
        gom.connect(application.notify_progress_end,   self.progress_end_CB)

        # scene graph edition
        self.rename_old = None
        self.rename_new = None

        # Views
        self.scene_graph_view = SceneGraphView(self.scene_graph)
        
    #====== Main application loop ==========================================
    
    def run(self,args):

        PyAutoGUI.register_commands(
            self.scene_graph, OGF.SceneGraph, SceneGraphGraphiteCommands
        )
        
        for f in args[1:]:
            self.scene_graph.load_object(f)

        for objname in dir(self.scene_graph.objects):
            grob = self.scene_graph.resolve(objname)
            if (grob.meta_class.is_a(OGF.MeshGrob) and
                grob.I.Editor.nb_facets != 0):
                grob.I.Surface.triangulate()

        ps.set_open_imgui_window_for_user_callback(False) # we draw our own win
        ps.set_user_callback(self.draw_GUI)
        self.running = True
        quiet_frames = 0
        self.scene_graph.application.start()
        while self.running:
            ps.frame_tick()
            
            # Handle command out of frame tick so that CBs
            # can redraw GUI by calling frame tick again.
            self.handle_queued_command() 
            
            # Mechanism to make it sleep a little bit
            # if no mouse click/mouse drag happened
            # since 2000 frames or more. This leaves
            # CPU power for other apps and/or lets the
            # CPU cool down. There are two levels of
            # cooling down depending on how many frames
            # were "quiet" (that is, without mouse click
            # or mouse drag)
            if (
                    imgui.GetIO().MouseDown[0] or
                    imgui.GetIO().MouseDown[1] or
                    imgui.GetIO().MouseDown[2]
            ):
                quiet_frames = 0
            else:
                quiet_frames = quiet_frames + 1
            if quiet_frames > 2200:
                time.sleep(0.5)  # gros dodo: 1/2 second
                                 # (after 2000 + 200*1/20th second)
            elif quiet_frames > 2000:
                time.sleep(0.05) # petit dodo: 1/20th second
            else:
                time.sleep(0.01) # micro-sieste: 1/100th second
        self.scene_graph.clear()
        self.scene_graph.application.stop()
                
    def draw_GUI(self):
        imgui.SetNextWindowPos([340,10])
        imgui.SetNextWindowSize([300,ps.get_window_size()[1]-20])
        unfolded,_ = imgui.Begin(
            'Graphite',True,imgui.ImGuiWindowFlags_MenuBar
        )
        if unfolded:
            self.draw_menubar()
            self.draw_scenegraph_GUI()
            self.draw_command()
        imgui.End()
        self.draw_terminal_window()
        self.draw_progressbar_window()

    def print(self, str):
        self.message = self.message + str
        self.message_changed_frames = 3 # needs three frames for SetScrollY()
                                        # to do the job
        
    #====== Main elements of GUI ==========================================

    def draw_terminal_window(self):
        if self.show_terminal: 
            height = 150
            if self.progress_task == None:
                height = height + 50
            else:
                self.message_changed_frames = 3 # make tty scroll to end
            imgui.SetNextWindowPos([660,ps.get_window_size()[1]-210])
            imgui.SetNextWindowSize([600,height])
            _,self.show_terminal = imgui.Begin('Terminal',self.show_terminal)
            imgui.Text(self.message)
            if self.message_changed_frames > 0:
                imgui.SetScrollY(imgui.GetScrollMaxY())
                self.message_changed_frames = self.message_changed_frames - 1
            imgui.End()

    def draw_progressbar_window(self):
        if self.progress_task != None:
            imgui.SetNextWindowPos([660,ps.get_window_size()[1]-55])
            imgui.SetNextWindowSize([600,45])
            imgui.Begin('Progress',True,imgui.ImGuiWindowFlags_NoTitleBar)
            if imgui.Button('X'):
                self.scene_graph.application.progress_cancel()
            if imgui.IsItemHovered():
                imgui.SetTooltip('Cancel task')
            imgui.SameLine()
            imgui.Text(self.progress_task)
            imgui.SameLine()
            imgui.ProgressBar(self.progress_percent/100.0, [-1,0])
            imgui.End()
            
    def draw_menubar(self):
        if imgui.BeginMenuBar():
            if imgui.BeginMenu('File'):
                # self.draw_request_menuitem(self.scene_graph.load_object)
                # self.draw_request_menuitem(self.scene_graph.save)
                # self.draw_object_commands_menus(self.scene_graph)

                self.draw_interface_menuitems(self.scene_graph.I.Graphite)
                
                imgui.Separator()           
                if imgui.MenuItem('show all'):
                    self.scene_graph_view.show_all()
                if imgui.MenuItem('hide all'):
                    self.scene_graph_view.hide_all()
                imgui.Separator()
                if imgui.MenuItem('quit'):
                    self.running = False
                imgui.EndMenu()
            if imgui.BeginMenu('Windows'):
                if imgui.MenuItem(
                    'show terminal', None, self.show_terminal
                ):
                    self.show_terminal = not self.show_terminal
                imgui.EndMenu()
            imgui.EndMenuBar()

    def draw_scenegraph_GUI(self):
        # Get scene objects, I do that instead of dir(self.scene_graph.objects)
        # to keep the order of the objects.
        objects = []
        for i in range(self.scene_graph.nb_children):
            objects.append(self.scene_graph.ith_child(i).name)

        imgui.BeginListBox('##Objects',[-1,200])
        for objname in objects:
            object = getattr(self.scene_graph.objects,objname)        
            self.draw_object_GUI(object)
        imgui.EndListBox()

    def draw_object_GUI(self, object):
        objname = object.name
        itemwidth = imgui.GetContentRegionAvail()[0]
        show_buttons = (self.scene_graph.current_object == objname and
                        self.rename_old == None)

        if (show_buttons):
            itemwidth = itemwidth - 105

        if self.rename_old == objname: # if object is being renamed
            if self.rename_old == self.rename_new:
                imgui.SetKeyboardFocusHere(0)
            sel,self.rename_new=imgui.InputText(
                'rename##' + objname,self.rename_new,
                imgui.ImGuiInputTextFlags_EnterReturnsTrue |
		imgui.ImGuiInputTextFlags_AutoSelectAll
            )
            if sel: # <enter> was pressed, rename object
                if self.rename_old != self.rename_new:
                    object.rename(self.rename_new)
                    self.scene_graph.current_object = object.name
                self.rename_old = None
                self.rename_new = None
        else: # standard operation (object is not being renamed)

            view = self.scene_graph_view.view_map[objname]
            visible = (view != None and view.visible)

            selected,visible = imgui.Checkbox('##visible##'+objname, visible)
            imgui.SameLine()
            if selected and view != None:
                if visible:
                    view.show()
                else:
                    view.hide()
            
            selected = (self.scene_graph.current() != None and
                        self.scene_graph.current().name == objname)
            sel,_=imgui.Selectable(
                objname, selected,
                imgui.ImGuiSelectableFlags_AllowDoubleClick,
                [itemwidth,0]
            )
            if sel:
                self.scene_graph.current_object = objname
                if imgui.IsMouseDoubleClicked(0):
                    self.scene_graph_view.show_only(object)

        self.draw_object_menu(object)

        if show_buttons:
            imgui.SameLine()
            self.draw_object_buttons(object)
        
    def draw_object_menu(self, object):
        if imgui.BeginPopupContextItem(object.name+'##ops'):
            if imgui.MenuItem('rename'):
                self.rename_old = object.name
                self.rename_new = object.name

            if imgui.MenuItem('duplicate'):
                self.scene_graph.current_object = object.name
                new_object = self.scene_graph.duplicate_current()
                self.scene_graph.current_object = new_object.name
                self.rename_old = new_object.name
                self.rename_new = new_object.name
                
            if imgui.MenuItem('save object'):
                self.set_command(object.save)

            if imgui.MenuItem('commit transform'):
                self.commit_transform(object)
            if imgui.IsItemHovered():
                imgui.SetTooltip(
                    'transforms vertices according to Polyscope transform guizmo'
                )
                    
            imgui.Separator() 
            request = self.get_menu_map(object).draw_menus(object)
            if request != None:
                self.set_command(request)
            imgui.EndPopup()

    def draw_object_buttons(self, object):
        imgui.PushStyleVar(imgui.ImGuiStyleVar_FramePadding, [0,0])
        if imgui.ArrowButton('^'+object.name,imgui.ImGuiDir_Up):
            self.scene_graph.current_object = object.name
            self.scene_graph.move_current_up()
        if imgui.IsItemHovered():
            imgui.SetTooltip('Move object up')
        imgui.SameLine()
        if imgui.ArrowButton('v'+object.name,imgui.ImGuiDir_Down):
            self.scene_graph.current_object = object.name
            self.scene_graph.move_current_down()
        if imgui.IsItemHovered():
            imgui.SetTooltip('Move object down')
        imgui.SameLine()
        imgui.PushStyleVar(imgui.ImGuiStyleVar_FramePadding, [5,0])
        if imgui.Button('X'+'##'+object.name):
            if (self.request != None and
                self.get_grob(self.request).name == object.name):
                self.reset_command()
            self.scene_graph.current_object = object.name
            self.scene_graph.delete_current_object()
            if imgui.IsItemHovered():
                imgui.SetTooltip('Delete object')
            imgui.PopStyleVar()                    
            imgui.PopStyleVar()
            
            
    def draw_command(self):
        """ Draws the GUI for the current Graphite command """
        if self.request != None:
            grob = self.get_grob(self.request)
            if grob.meta_class.name == 'OGF::SceneGraph':
                objname = 'scene_graph'
                if self.scene_graph.current() != None:
                    objname = ( objname + ', current=' +
                                self.scene_graph.current().name )
            else:
                objname = grob.name
            imgui.Text('Object: ' + objname)
            AutoGUI.draw_command(self.request, self.args)
            if imgui.Button('OK'):
                self.queued_execute_command = True
                self.queued_close_command = True
            if imgui.IsItemHovered():
                imgui.SetTooltip('Apply and close command')
            imgui.SameLine()
            if imgui.Button('Apply'):
                self.queued_execute_command = True
            if imgui.IsItemHovered():
                imgui.SetTooltip('Apply and keep command open')
            imgui.SameLine()
            if imgui.Button('Cancel'):
                self.reset_command()
            if imgui.IsItemHovered():
                imgui.SetTooltip('Close command')
            imgui.SameLine()                
            if imgui.Button('Reset'):
                self.set_command(self.request)
            if imgui.IsItemHovered():
                imgui.SetTooltip('Reset factory settings')

    # This function is called right after PolyScope has finished rendering
                
    def handle_queued_command(self):
        
        if self.queued_execute_command:

            # Commit all transforms (guizmos)
            self.scene_graph_view.commit_transform()
            self.invoke_command()

            # Polygonal surfaces not supported for now, so we
            # triangulate
            grob = self.get_grob(self.request)
            if (grob.meta_class.is_a(OGF.MeshGrob) and
                grob.I.Editor.nb_facets != 0):
                grob.I.Surface.triangulate()
                        
            self.queued_execute_command = False
            
        if self.queued_close_command:
            self.reset_command()
            self.queued_close_command = False

            
    # the closure passed to set_command() may be in the
    # form grob.interface.method or simply grob.method.
    # This function gets the grob in both cases.
    def get_grob(self,request):
        object = request.object()
        if(hasattr(object,'grob')):
            return object.grob
        else:
            return object

    def get_menu_map(self, grob):
        if not grob.name in self.menu_maps:
            self.menu_maps[grob.name] = MenuMap(grob.meta_class)
        return self.menu_maps[grob.name]

    #===== Commands management ==============================================

    def set_command(self, request):
        """ Sets current Graphite command, edited in the GUI """
        self.request = request
        self.args = AutoGUI.init_command_args(request)

    def reset_command(self):
        """ Resets current Graphite command """
        self.request = None
        self.args = None

    def invoke_command(self):
        """ Invokes current Graphite command with the args entered in the GUI """
        self.request(**self.args) #**: expand dict as keywords func call
        
    #===== Other menus from metainformation =================================
                    
    def draw_object_commands_menus(self,o : OGF.Object):
        """ Draws menus for all commands associated with a Graphite object """
        # get all interfaces of the object
        for interface_name in dir(o.I):
            interface = getattr(o.I,interface_name)
            # keep only those that inherit OGF::Commands
            if interface.meta_class.is_a(OGF.Commands):
                if imgui.BeginMenu(interface_name):
                    self.draw_interface_menuitems(interface)
                    imgui.EndMenu()

    def draw_interface_menuitems(self, interface : OGF.Interface):
        """ Draw menu items for all slots of an interface """
        mclass = interface.meta_class
        for i in range(mclass.nb_slots()):
            mslot = mclass.ith_slot(i)
            if not hasattr(OGF.Interface,mslot.name):
                self.draw_request_menuitem(getattr(interface,mslot.name))

    def draw_request_menuitem(self, request : OGF.Request):
        """ Draw a menu item for a given request (that is, a closure) """
        if imgui.MenuItem(request.method().name.replace('_',' ')):
            self.set_command(request)
        if (
                imgui.IsItemHovered() and
                request.method().has_custom_attribute('help')
        ):
            imgui.SetTooltip(request.method().custom_attribute_value('help'))
        
#=====================================================
# Graphite application

graphite = GraphiteApp()

#=====================================================

class SceneGraphGraphiteCommands:
    """ The commands in the fist section of the File menu """

    def load(
            interface : OGF.Interface,
            method    : str,
            filename  : str
    ):
        """
        @brief loads a file
        @param[in] filename object file name or graphite scenegraph file
        """
        interface.grob.load_object(filename)

    def save_scene(
            interface       : OGF.Interface,
            method          : str,
            scene_filename  : str
    ):
        """
        @brief loads a file
        @param[in] scene_filename = scene.graphite graphite scenegraph file
        """
        interface.grob.save(scene_filename)
        
    def create_object(
            interface : OGF.Interface,
            method    : str,
            type : OGF.GrobClassName,
            name : str
    ):
        """
        @brief creates a new object 
        @param[in] type = OGF::MeshGrob type of the object to create
        @param[in] name = new_object name of the object to create
        """
        interface.grob.create_object(type, name)

    def clear_scenegraph(
            interface : OGF.Interface,
            method    : str,
    ):
        """ @brief deletes all objects in the scene-graph """
        interface.grob.clear()
        
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
        @param[in] axis one of FLIP_X,FLIP_Y,FLIP_Z,ROT_X,ROT_Y,ROT_Z,PERM_XYZ
        @param[in] center = True if set, xform is relative to object's center
        @menu /Mesh
        """
    
        grob = interface.grob
    
        if center:
            C = MeshGrobOps.get_object_center(grob)
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
