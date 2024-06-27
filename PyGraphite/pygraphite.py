import polyscope as ps
import numpy as np
import gompy
import math,sys,time

global graphite


class GraphiteApp:

    #===== Application logic =============================================

    # callback called whenever geogram prints something
    # rem: a 'static class method', because if I use a regular method
    # it crashes (don't know why for now, to be investigated...)
    def print_CB(str):
        GraphiteApp.instance.show_terminal=True
        GraphiteApp.instance.print(str)

    def __init__(self):
        GraphiteApp.instance = self
        self.reset_command()
        self.structure_map = {} # graphite object name -> polyscope structure
        self.menu_map = {}      # dictionary tree that represents menus
        self.running = False
        self.scene_graph = gom.meta_types.OGF.SceneGraph.create()
        self.message = ''
        self.show_terminal = False
        self.application = gom.meta_types.OGF.ApplicationBase.create()
        self.scene_graph.application = self.application
        gom.connect(self.application.out, GraphiteApp.print_CB)
        gom.connect(self.application.err, GraphiteApp.print_CB)        
        
    def run(self,args):
        self.menu_map = self.menu_map_build(gom.meta_types.OGF.MeshGrob)
        for f in args[1:]:
            self.scene_graph.load_object(f)
        self.register_graphite_objects()
        ps.set_open_imgui_window_for_user_callback(False)
        ps.set_user_callback(self.draw_GUI)
        self.running = True
        quiet_frames = 0
        self.scene_graph.I.Scene.set_parameter('log:verbose','true')
        self.scene_graph.I.Scene.set_parameter('log:pretty','false')
        self.application.start()
        while self.running:
            ps.frame_tick()
            # Mechanism to make it sleep a little bit
            # if no mouse click/mouse drag happened
            # since 2000 frames or more. This leaves
            # CPU power for other apps and/or lets the
            # CPU cool down
            if (
                    ps.imgui.GetIO().MouseDown[0] or
                    ps.imgui.GetIO().MouseDown[1] or
                    ps.imgui.GetIO().MouseDown[2]
            ):
                quiet_frames = 0
            else:
                quiet_frames = quiet_frames + 1
            if quiet_frames > 2000:
                time.sleep(0.05)

    def draw_GUI(self):
        ps.imgui.SetNextWindowPos([340,10])
        ps.imgui.SetNextWindowSize([300,ps.get_window_size()[1]-20])
        ps.imgui.Begin('Graphite',True,ps.imgui.ImGuiWindowFlags_MenuBar)
        self.draw_menubar()
        self.draw_scenegraph_GUI()
        self.draw_command()
        ps.imgui.End()
        self.draw_terminal_window()

    def print(self, str):
        self.message = self.message + str 
        
    #====== Main elements of GUI ==========================================

    def draw_terminal_window(self):
        if self.show_terminal: # TODO: find a way of making 'x' close the wndow
            ps.imgui.SetNextWindowPos([660,ps.get_window_size()[1]-200])
            ps.imgui.SetNextWindowSize([600,190])
            ps.imgui.Begin('Terminal',True,ps.imgui.ImGuiWindowFlags_NoTitleBar)
            ps.imgui.Text(self.message)
            ps.imgui.SetScrollY(ps.imgui.GetScrollMaxY())
            ps.imgui.End()

    def draw_menubar(self):
        if ps.imgui.BeginMenuBar():
            if ps.imgui.BeginMenu('File'):
                graphite.draw_object_commands_menus(self.scene_graph)
                ps.imgui.Separator()           
                if ps.imgui.MenuItem('show all'):
                    for objname in dir(self.scene_graph.objects):
                        graphite.structure_map[objname].set_enabled(True)
                if ps.imgui.MenuItem('hide all'):
                    for objname in dir(self.scene_graph.objects):
                        graphite.structure_map[objname].set_enabled(False)
                ps.imgui.Separator()
                if ps.imgui.MenuItem('quit'):
                    self.running = False
                ps.imgui.EndMenu()
            if ps.imgui.BeginMenu('Windows'):
                if ps.imgui.MenuItem(
                    'show terminal', None, self.show_terminal
                ):
                    self.show_terminal = not self.show_terminal
                ps.imgui.EndMenu()
            ps.imgui.EndMenuBar()


    def draw_scenegraph_GUI(self):
        C = self.scene_graph.current()
        if C != None:
            nv = C.I.Editor.nb_vertices
            nf = C.I.Editor.nb_facets
            ps.imgui.Text(C.name)
            ps.imgui.Text('   vertices: ' + str(nv))
            ps.imgui.Text('   facets: ' + str(nf))
        objects = dir(self.scene_graph.objects)
        ps.imgui.BeginListBox('##Objects',[-1,200])
        for objname in objects:
            sel,_=ps.imgui.Selectable(
                objname, (objname == self.scene_graph.current().name),
                ps.imgui.ImGuiSelectableFlags_AllowDoubleClick
            )
            if sel:
                self.scene_graph.current_object = objname
                if ps.imgui.IsMouseDoubleClicked(0):
                    for objname2 in dir(self.scene_graph.objects):
                        graphite.structure_map[objname2].set_enabled(
                            objname2==objname
                        )
            
            if ps.imgui.BeginPopupContextItem(objname+'##ops'):
                if ps.imgui.MenuItem('delete object'):
                    self.scene_graph.current_object = objname
                    graphite.set_command(
                        self.scene_graph.I.Scene.delete_current
                    )
                
                if ps.imgui.MenuItem('rename object'):
                    self.scene_graph.current_object = objname
                    graphite.set_command(
                        self.scene_graph.I.Scene.rename_current
                    )

                if ps.imgui.MenuItem('duplicate object'):
                    self.scene_graph.current_object = objname
                    graphite.set_command(
                        self.scene_graph.I.Scene.duplicate_current
                    )

                if ps.imgui.MenuItem('commit transform'):
                    self.commit_transform(
                        getattr(self.scene_graph.objects,objname)
                    )
                
                ps.imgui.Separator() 
                self.draw_menumap(
                    self.menu_map,getattr(self.scene_graph.objects,objname)
                )
                ps.imgui.EndPopup()	      
        ps.imgui.EndListBox()

    """ Draws the GUI for the current Graphite command """
    def draw_command(self):
        if self.request != None:
            grob = self.request.object().grob
            if grob.meta_class.name == 'OGF::SceneGraph':
                objname = 'scene_graph'
                if self.scene_graph.current() != None:
                    objname = ( objname + ', current=' +
                                self.scene_graph.current().name )
            else:                
                objname = grob.name
                
            ps.imgui.Text('Object: '  + objname)
            ps.imgui.Text(
                'Command: ' + self.request.method().name.replace('_',' ')
            )
            if (ps.imgui.IsItemHovered() and
                self.request.method().has_custom_attribute('help')):
                ps.imgui.SetTooltip(
                    self.request.method().custom_attribute_value('help')
                )
            mmethod = self.request.method()
            if mmethod.nb_args() != 0:
                nb_standard_args = 0
                has_advanced_args = False
                for i in range(mmethod.nb_args()):
                    if self.ith_arg_is_advanced(i):
                        has_advanced_args = True
                    else:
                        nb_standard_args = nb_standard_args + 1
                height = nb_standard_args * 32
                if has_advanced_args:
                    height = height + 20
                ps.imgui.BeginListBox('##Command',[-1,height])
                for i in range(mmethod.nb_args()):
                    tooltip = None
                    if not self.ith_arg_is_advanced(i):
                        if mmethod.ith_arg_has_custom_attribute(i,'help'):
                            tooltip = \
                                 mmethod.ith_arg_custom_attribute_value(i,'help')
                        self.arg_handler(
                            mmethod.ith_arg_name(i),
                            mmethod.ith_arg_type(i), tooltip
                        )
                if has_advanced_args:
                    if ps.imgui.TreeNode(
                            'Advanced'+'##'+objname+'.'+mmethod.name
                    ):
                        ps.imgui.TreePop()
                        for i in range(mmethod.nb_args()):
                            tooltip = None
                            if self.ith_arg_is_advanced(i):
                                if mmethod.ith_arg_has_custom_attribute(
                                        i,'help'
                                ):
                                    tooltip = \
                                        mmethod.ith_arg_custom_attribute_value(
                                            i,'help'
                                        )
                                self.arg_handler(
                                    mmethod.ith_arg_name(i),
                                    mmethod.ith_arg_type(i), tooltip
                                )
                ps.imgui.EndListBox()
            meta_class = mmethod.container_meta_class()                
            if ps.imgui.Button('OK'):
                grob = self.request.object().grob
                if not mmethod.has_custom_attribute('keep_structures'):
                    self.unregister_graphite_objects()
                self.invoke_command()
                if (
                        grob.meta_class.is_a(gom.meta_types.OGF.MeshGrob) and
                        grob.I.Editor.nb_facets != 0
                ):
                    self.request.object().grob.I.Surface.triangulate()
                if not mmethod.has_custom_attribute('keep_structures'):
                    self.register_graphite_objects()
                graphite.reset_command()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Apply and close command')
            ps.imgui.SameLine()
            if ps.imgui.Button('Apply'):
                grob = self.request.object().grob
                if not mmethod.has_custom_attribute('keep_structures'):
                    self.unregister_graphite_objects()
                self.invoke_command()
                if grob.meta_class.is_a(gom.meta_types.OGF.MeshGrob):
                    self.request.object().grob.I.Surface.triangulate()
                if not mmethod.has_custom_attribute('keep_structures'):
                    self.register_graphite_objects()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Apply and keep command open')
            ps.imgui.SameLine()
            if ps.imgui.Button('Cancel'):
                graphite.reset_command()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Close command')

    #===== Commands management ==============================================

    """ Sets current Graphite command, edited in the GUI """
    def set_command(self, request):
        self.request = request
        self.args = {}
        mmethod = self.request.method()
        for i in range(mmethod.nb_args()):
            val = ''
            if mmethod.ith_arg_has_default_value(i):
                val = mmethod.ith_arg_default_value_as_string(i)
            self.args[mmethod.ith_arg_name(i)] = val

    """ Reset_Commands current Graphite command """
    def reset_command(self):
        self.request = None
        self.args = None

    """ Invokes current Graphite command with the args entered in the GUI """
    def invoke_command(self):
        self.request(**self.args) #**: expand dict as keywords func call

    #===== MenuMap ===========================================================

    """ Inserts an entry in a menumap """
    def menu_map_insert(self, menu_dict, menu_name, mslot):
        menu_path = menu_name.split('/')
        if menu_name == '':
            menu_dict[mslot.name] = mslot
        else:
            k = menu_path[0]
            menu_path = menu_path[1:]
            if k not in menu_dict:
                menu_dict[k] = dict()
            menu_name = menu_name.removeprefix(k)
            menu_name = menu_name.removeprefix('/')
            self.menu_map_insert(menu_dict[k], menu_name, mslot)

    """ Builds a menumap for a grob meta class """
    def menu_map_build(self,grob_meta_class):
        result = dict()
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
                    if (
                        gom.meta_types.OGF.Object.find_member(mslot.name)==None
                            and
                        gom.meta_types.OGF.Node.find_member(mslot.name)  ==None
                    ):
                        self.menu_map_insert(result, menu_name, mslot)   
        return result
    
    """ Draws and handles the menus stored in a menumap """
    def draw_menumap(self,menudict,o):
        for k,v in menudict.items():
            if isinstance(v,dict):
                if ps.imgui.BeginMenu(k.replace('_',' ')):
                    self.draw_menumap(v,o)
                    ps.imgui.EndMenu()
            else:
                mslot = v
                mclass = mslot.container_meta_class()
                if ps.imgui.MenuItem(k.replace('_',' ')):
                    self.set_command(
                        getattr(o.query_interface(mclass.name),mslot.name)
                    )
                if (ps.imgui.IsItemHovered() and
                    mslot.has_custom_attribute('help')):
                    ps.imgui.SetTooltip(mslot.custom_attribute_value('help'))

    #===== Other menus from metainformation =================================
                    
    """ Draws menus for all commands associated with a Graphite object """
    def draw_object_commands_menus(self,o):
        # get all interfaces of the object
        for interface_name in dir(o.I):
            interface = getattr(o.I,interface_name)
            # keep only those that inherit OGF::Commands
            if interface.meta_class.is_a(gom.meta_types.OGF.Commands):
                if ps.imgui.BeginMenu(interface_name):
                    self.draw_interface_menuitems(interface)
                    ps.imgui.EndMenu()

    """ Draw menu items for all slots of an interface """
    def draw_interface_menuitems(self,interface):
        mclass = interface.meta_class
        for i in range(mclass.nb_slots()):
            mslot = mclass.ith_slot(i)
            if not hasattr(gom.meta_types.OGF.Interface,mslot.name):
                self.draw_request_menuitem(getattr(interface,mslot.name))

    """ Draw a menu item for a given request (that is, a closure) """
    def draw_request_menuitem(self, request):
        if ps.imgui.MenuItem(request.method().name.replace('_',' ')):
            self.set_command(request)
        if (
                ps.imgui.IsItemHovered() and
                request.method().has_custom_attribute('help')
        ):
            ps.imgui.SetTooltip(request.method().custom_attribute_value('help'))
    

    #===== Low-level GUI, handlers for arguments based on type ==================
            
    def ith_arg_is_advanced(self, i):
        mmethod = self.request.method()
        if not mmethod.ith_arg_has_custom_attribute(i,'advanced'):
           return False
        return (mmethod.ith_arg_custom_attribute_value(i,'advanced') == 'true')
        
    """ Handles the GUI for a parameter """
    def arg_handler(self, property_name, mtype, tooltip):
        if mtype.meta_class.is_a(gom.meta_types.OGF.MetaEnum):
            self.enum_handler(property_name, mtype, tooltip)
            return
        handler_name = mtype.name.replace(' ','_').replace(':','_') + '_handler'
        if hasattr(self, handler_name):
            getattr(self, handler_name)(property_name, mtype, tooltip)
            return
        self.string_handler(property_name, mtype, tooltip)
        
    """ Handles the GUI for a string parameter """
    def string_handler(self, property_name, mtype, tooltip):
        self.label(property_name, tooltip)        
        ps.imgui.SameLine()
        ps.imgui.PushItemWidth(-20)
        val = self.args[property_name]
        _,val = ps.imgui.InputText(
            '##properties##' + property_name, val
        )
        ps.imgui.PopItemWidth()
        self.args[property_name] = val

    """ Handles the GUI for a boolean parameter """
    def bool_handler(self, property_name, mtype, tooltip):
        ps.imgui.PushItemWidth(-1)
        val = self.args[property_name]
        val = (val == 'true')
        _,val = ps.imgui.Checkbox(
            property_name.replace('_',' '), val
        )
        if tooltip != None and ps.imgui.IsItemHovered():
            ps.imgui.SetTooltip(tooltip)
        ps.imgui.PopItemWidth()
        if val:
            val = 'true'
        else:
            val = 'false'
        self.args[property_name] = val

    """ Handles the GUI for an integer parameter """
    def int_handler(self, property_name, mtype, tooltip):
        self.label(property_name, tooltip)
        ps.imgui.SameLine()
        ps.imgui.PushItemWidth(-20)
        val = self.args[property_name]
        val = int(val)
        _,val = ps.imgui.InputInt(
            '##properties##' + property_name, val, 1
        )
        ps.imgui.PopItemWidth()
        val = str(val)
        self.args[property_name] = val

    """ Handles the GUI for an unsigned integer parameter """
    def unsigned_int_handler(self, property_name, mtype, tooltip):
        self.label(property_name, tooltip)
        ps.imgui.SameLine()
        ps.imgui.PushItemWidth(-20)
        val = self.args[property_name]
        val = int(val)
        if val < 0:
            val = 0
        _,val = ps.imgui.InputInt(
            '##properties##' + property_name, val, 1
        )
        ps.imgui.PopItemWidth()
        val = str(val)
        self.args[property_name] = val

    """ Handles the GUI for a MeshGrobName parameter """
    def OGF__MeshGrobName_handler(self, property_name, mtype, tooltip):
        values = gom.get_environment_value('OGF::MeshGrob_instances')
        self.combo_box(property_name, values, tooltip)

    """ Handles the GUI for a GrobClassName parameter """
    def OGF__GrobClassName_handler(self, property_name, mtype, tooltip):
        values = gom.get_environment_value('grob_types')
        self.combo_box(property_name, values, tooltip)

    """ Handles the GUI for an enum parameter """
    def enum_handler(self, property_name, menum, tooltip):
        values = ''
        for i in range(menum.nb_values()):
            if i != 0:
                values = values + ';'
            values = values + menum.ith_name(i)
        self.combo_box(property_name, values, tooltip)

    """ Handles the GUI with a combobox, 
        given the possible values in a ';'-separated string """
    def combo_box(self, property_name, values, tooltip):
        self.label(property_name, tooltip)
        if values=='':
            return
        if values[0] == ';':
            values = values[1:]
        values = values.split(';')

        old_value = self.args[property_name]
        found = True
        try:
            old_index = values.index(old_value)
        except:
            found = False
            old_index = 0
        ps.imgui.SameLine()
        ps.imgui.PushItemWidth(-20)
        _,new_index = ps.imgui.Combo(
            '##properties##'+property_name, old_index, values
        )
        ps.imgui.PopItemWidth()
        self.args[property_name] = values[new_index]

    """ Draws the label of a parameter, 
        and a tooltip if help is available in meta info """
    def label(self, property_name, tooltip):
        ps.imgui.Text(property_name.replace('_',' '))
        if tooltip != None and ps.imgui.IsItemHovered():
            ps.imgui.SetTooltip(tooltip)

    # ===== Graphite - Polyscope interop =======================

    def register_graphite_object(self,o):
        E = o.I.Editor
        structure = None
        pts = np.asarray(E.get_points())
        if E.nb_facets == 0 and E.nb_cells == 0:
            structure = ps.register_point_cloud(o.name,pts)
        elif E.nb_cells == 0:
            structure = ps.register_surface_mesh(
                o.name, pts,
                np.asarray(o.I.Editor.get_triangles())
            )
        else:
            structure = ps.register_volume_mesh(
                o.name, pts,
                np.asarray(o.I.Editor.get_tetrahedra())
            )
        if structure != None:
            self.structure_map[o.name] = structure
            for attr in o.list_attributes('vertices','double','1').split(';'):
                if attr != '':
                    attrarray = np.asarray(E.find_attribute(attr))
                    structure.add_scalar_quantity(
                        attr.removeprefix('vertices.'),
                        attrarray
                    )
        
    def register_graphite_objects(self):
        for i in dir(self.scene_graph.objects):
            self.register_graphite_object(self.scene_graph.resolve(i))
                
    def unregister_graphite_objects(self):
        for i in dir(self.scene_graph.objects):
            self.structure_map[i].remove()
            del self.structure_map[i]

    def commit_transform(self, o):
        structure = self.structure_map[o.name]
        xform = structure.get_transform()
        object_vertices = np.asarray(o.I.Editor.get_points())
        vertices = np.c_[  # add a column of 1
            object_vertices, np.ones(object_vertices.shape[0])
        ]
        # transform all the vertices
        vertices = np.matmul(vertices,np.transpose(xform))
        weights = vertices[:,-1]            # get 4th column
        vertices = vertices[:,:-1]          # get the rest
        vertices = vertices/weights[:,None] # divice by w
        np.copyto(object_vertices,vertices) # inject into graphite object
        structure.reset_transform()      # reset polyscope xform
        # tell polyscope that vertices have changed
        structure.update_vertex_positions(object_vertices) 

        
#=====================================================
# Graphite application

graphite = GraphiteApp()


#=====================================================
# Add custom commands to Graphite Object Model

menum = gom.meta_types.OGF.MetaEnum.create('FlipAxis')
menum.add_value('FLIP_X',0)
menum.add_value('FLIP_Y',1)
menum.add_value('FLIP_Z',2)
menum.add_value('ROT_X',3)
menum.add_value('ROT_Y',4)
menum.add_value('ROT_Z',5)
menum.add_value('PERM_XYZ',6)
gom.bind_meta_type(menum)

# extracts a component from a vector attribute and
# displays it in Polyscope
def extract_component(attr_name, component, o, method):
    grob = o.grob
    component = int(component) # all args are passed as strings
    attr_array = np.asarray(
        grob.I.Editor.find_attribute('vertices.'+attr_name)
    )
    attr_array = attr_array[:,component]
    graphite.structure_map[grob.name].add_scalar_quantity(
        attr_name+'['+str(component)+']', attr_array
    )

# flips axes of a mesh
# note the in-place modification of object's coordinates
def flip(axis, o, method):
    grob = o.grob
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
    structure = graphite.structure_map[grob.name]
    structure.update_vertex_positions(pts_array) 

        
mclass = gom.meta_types.OGF.MeshGrobCommands.create_subclass(
    'OGF::MeshGrobPolyScopeCommands'
)
mclass.add_constructor()
mslot = mclass.add_slot('extract_component',extract_component)
mslot.create_custom_attribute(
    'help','sends component of a vector attribute to Polyscope'
)
mslot.create_custom_attribute('keep_structures','true')
mslot.create_custom_attribute('menu','/Attributes/Polyscope Display')
mslot.add_arg('attr_name', gom.meta_types.std.string)
mslot.add_arg('component', gom.meta_types.int, '0')

mslot = mclass.add_slot('flip',flip)
mslot.create_custom_attribute('help','flips axes of an object')
mslot.create_custom_attribute('keep_structures','true')
mslot.create_custom_attribute('menu','/Mesh')
mslot.add_arg('axis', gom.meta_types.FlipAxis, 'X')

graphite.scene_graph.register_grob_commands(gom.meta_types.OGF.MeshGrob,mclass)

#=====================================================
# Initialize Polyscope and enter app main loop
ps.init()
graphite.run(sys.argv)
