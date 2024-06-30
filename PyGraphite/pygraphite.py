import polyscope as ps
import numpy as np
import gompy
import math,sys,time

global graphite


class GraphiteApp:

    #===== Application logic =============================================

    # Callback for printing, redirected to terminal and for progress,
    # redirecting to progress bar
    # Since commands are queued and called outside PolyScope rendering function,
    # they can draw an additional frame in need be (by calling PolyScope.frame_tick)
    
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
        
        self.menu_map = {}            # dictionary tree that represents menus
        self.reset_command()
        self.queued_execute_command = False # command execution is queued, for 
        self.queued_close_command   = False #   making it happen out off polyscope CB
        
        self.structure_map = {} # graphite object name -> polyscope structure
        self.scene_graph = gom.meta_types.OGF.SceneGraph.create()
        
        # create a Graphite ApplicationBase. It has the printing and progress callbacks,
        # that are redirected here to some functions (ending with _CB).
        application = gom.meta_types.OGF.ApplicationBase.create()
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

    #====== Main application loop ==========================================
    
    def run(self,args):
        self.menu_map = self.menu_map_build(gom.meta_types.OGF.MeshGrob)
        for f in args[1:]:
            self.scene_graph.load_object(f)

        for objname in dir(self.scene_graph.objects):
            grob = self.scene_graph.resolve(objname)
            if (grob.meta_class.is_a(gom.meta_types.OGF.MeshGrob) and
                grob.I.Editor.nb_facets != 0):
                grob.I.Surface.triangulate()

            
        self.register_graphite_objects()
        ps.set_open_imgui_window_for_user_callback(False) # we draw our own window
        ps.set_user_callback(self.draw_GUI)
        self.running = True
        quiet_frames = 0
        self.scene_graph.application.start()
        while self.running:
            ps.frame_tick()
            
            # Handle command out of frame tick so that CBs can redraw GUI by calling
            # frame tick again.
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
                    ps.imgui.GetIO().MouseDown[0] or
                    ps.imgui.GetIO().MouseDown[1] or
                    ps.imgui.GetIO().MouseDown[2]
            ):
                quiet_frames = 0
            else:
                quiet_frames = quiet_frames + 1
            if quiet_frames > 2200:
                time.sleep(0.5)  # gros dodo: 1/2 second (after 2000 + 200*1/20th second)
            elif quiet_frames > 2000:
                time.sleep(0.05) # petit dodo: 1/20th second
            else:
                time.sleep(0.01) # micro-sieste: 1/100th second
        self.unregister_graphite_objects()
        self.scene_graph.clear()
        self.scene_graph.application.stop()
                
    def draw_GUI(self):
        ps.imgui.SetNextWindowPos([340,10])
        ps.imgui.SetNextWindowSize([300,ps.get_window_size()[1]-20])
        unfolded,_ = ps.imgui.Begin('Graphite',True,ps.imgui.ImGuiWindowFlags_MenuBar)
        if unfolded:
            self.draw_menubar()
            self.draw_scenegraph_GUI()
            self.draw_command()
        ps.imgui.End()
        self.draw_terminal_window()
        self.draw_progressbar_window()

    def print(self, str):
        self.message = self.message + str
        self.message_changed_frames = 3 # needs two frames forSetScrollY() to do the job
        
    #====== Main elements of GUI ==========================================

    def draw_terminal_window(self):
        if self.show_terminal: # TODO: find a way of making 'x' close the wndow
            height = 160
            if self.progress_task == None:
                height = height + 40
            ps.imgui.SetNextWindowPos([660,ps.get_window_size()[1]-210])
            ps.imgui.SetNextWindowSize([600,height])
            _,self.show_terminal = ps.imgui.Begin('Terminal',self.show_terminal)
            ps.imgui.Text(self.message)
            if self.message_changed_frames > 0:
                ps.imgui.SetScrollY(ps.imgui.GetScrollMaxY())
                self.message_changed_frames = self.message_changed_frames - 1
            ps.imgui.End()

    def draw_progressbar_window(self):
        if self.progress_task != None:
            ps.imgui.SetNextWindowPos([660,ps.get_window_size()[1]-50])
            ps.imgui.SetNextWindowSize([600,40])
            ps.imgui.Begin('Progress',True,ps.imgui.ImGuiWindowFlags_NoTitleBar)
            if ps.imgui.Button('X'):
                self.scene_graph.application.progress_cancel()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Cancel task')
            ps.imgui.SameLine()
            ps.imgui.Text(self.progress_task)
            ps.imgui.SameLine()
            ps.imgui.ProgressBar(self.progress_percent/100.0, [-1,0])
            ps.imgui.End()
            
    def draw_menubar(self):
        if ps.imgui.BeginMenuBar():
            if ps.imgui.BeginMenu('File'):
                self.draw_request_menuitem(self.scene_graph.load_object)
                self.draw_request_menuitem(self.scene_graph.save)
                self.draw_object_commands_menus(self.scene_graph)
                ps.imgui.Separator()           
                if ps.imgui.MenuItem('show all'):
                    for objname in dir(self.scene_graph.objects):
                        self.structure_map[objname].set_enabled(True)
                if ps.imgui.MenuItem('hide all'):
                    for objname in dir(self.scene_graph.objects):
                        self.structure_map[objname].set_enabled(False)
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
                        self.structure_map[objname2].set_enabled(
                            objname2==objname
                        )
            
            if ps.imgui.BeginPopupContextItem(objname+'##ops'):
                if ps.imgui.MenuItem('delete object'):
                    self.scene_graph.current_object = objname
                    self.set_command(
                        self.scene_graph.I.Scene.delete_current
                    )
                
                if ps.imgui.MenuItem('rename object'):
                    self.scene_graph.current_object = objname
                    self.set_command(
                        self.scene_graph.I.Scene.rename_current
                    )

                if ps.imgui.MenuItem('duplicate object'):
                    self.scene_graph.current_object = objname
                    self.set_command(
                        self.scene_graph.I.Scene.duplicate_current
                    )

                if ps.imgui.MenuItem('save object'):
                    self.set_command(getattr(self.scene_graph.objects,objname).save)
                    
                ps.imgui.Separator() 
                self.draw_menumap(
                    self.menu_map,getattr(self.scene_graph.objects,objname)
                )
                ps.imgui.EndPopup()	      
        ps.imgui.EndListBox()

    """ Draws the GUI for the current Graphite command """
    def draw_command(self):
        if self.request != None:
            grob = self.get_grob(self.request)
            if grob.meta_class.name == 'OGF::SceneGraph':
                objname = 'scene_graph'
                if self.scene_graph.current() != None:
                    objname = ( objname + ', current=' +
                                self.scene_graph.current().name )
            else:
                objname = grob.name
                
            ps.imgui.Text('Object: ' + objname)
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
                height = nb_standard_args * 35
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
            if ps.imgui.Button('OK'):
                self.queued_execute_command = True
                self.queued_close_command = True
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Apply and close command')
            ps.imgui.SameLine()
            if ps.imgui.Button('Apply'):
                self.queued_execute_command = True
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Apply and keep command open')
            ps.imgui.SameLine()
            if ps.imgui.Button('Cancel'):
                self.reset_command()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Close command')

    # this function is called right after PolyScope has finished rendering
                
    def handle_queued_command(self):
        if self.queued_execute_command:
            grob = self.get_grob(self.request)
            mmethod = self.request.method()
            objects_before_command = dir(self.scene_graph.objects)
            visible_objects_before_command = []

            # Commit all transforms (note: does not cost much when
            # transforms are identity)
            for objname in dir(self.scene_graph.objects):
                obj = self.scene_graph.resolve(objname)
                self.commit_transform(obj)
            
            # Hide everything, so that we can work without smbdy
            # looking over our shoulder
            #if not mmethod.has_custom_attribute('keep_structures'):
            #    for objname in dir(self.scene_graph.objects):
            #        structure = self.structure_map[objname]
            #        if structure.is_enabled():
            #            visible_objects_before_command.append(objname)
            #            structure.set_enabled(False)
                        
            self.invoke_command()

            # Polygonal surfaces not supported for now, so we
            # triangulate
            if (grob.meta_class.is_a(gom.meta_types.OGF.MeshGrob) and
                grob.I.Editor.nb_facets != 0):
                grob.I.Surface.triangulate()

            # Unregister all objects that were previously there
            # Register all objects, and restore saved visible flag
            if not mmethod.has_custom_attribute('keep_structures'):
                for objname in objects_before_command:
                    self.unregister_graphite_object(objname)
                for objname in dir(self.scene_graph.objects):
                    structure = self.register_graphite_object(objname)
                    if objname in visible_objects_before_command:
                        structure.set_enabled(True)
                        
            self.queued_execute_command = False
        if self.queued_close_command:
            self.reset_command()
            self.queued_close_command = False
                
    # the closure passed to set_command() may be in the form grob.interface.method or
    # simply grob.method. This function gets the grob in both cases.
    def get_grob(self,request):
        object = request.object()
        if(hasattr(object,'grob')):
            return object.grob
        else:
            return object
                
    #===== Commands management ==============================================

    """ Sets current Graphite command, edited in the GUI """
    def set_command(self, request):
        self.request = request
        self.args = {}
        mmethod = self.request.method()
        # This additional arg makes the command display more information
        # in the terminal
        if not mmethod.meta_class.is_a(gom.meta_types.OGF.DynamicMetaSlot):
            self.args['invoked_from_gui'] = 'true'
        for i in range(mmethod.nb_args()):
            val = ''
            if mmethod.ith_arg_has_default_value(i):
                val = mmethod.ith_arg_default_value_as_string(i)
            self.args[mmethod.ith_arg_name(i)] = val

    """ Resets current Graphite command """
    def reset_command(self):
        self.request = None
        self.args = None

    """ Invokes current Graphite command with the args entered in the GUI """
    def invoke_command(self):
        self.request(**self.args) #**: expand dict as keywords func call

    #===== MenuMap ===========================================================

    # The structure of the object's menu is deduced from the declared
    # Commands classes and the potential "menu" attribute attached to
    # each individual command.
    # The function menu_map_build() traverses all Commands classes,
    # and creates a tree structure (stored in nested dictionaries).
    # It is called once at application startup.
    # The function draw_menu_map() draws the menu hierarchy, and
    # initializes a command when it is selected.
    
    """ Inserts an entry in a menumap """
    def menu_map_insert(self, menu_dict, menu_name, mslot):
        if menu_name == '':
            menu_dict[mslot.name] = mslot
        else:
            # get leading path component
            k = menu_name[0:(menu_name+'/').find('/')]
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
                    # Skip Object and Node functions, we don't want them to
                    # appear in the GUI
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

    def register_graphite_object(self,objname):
        o = self.scene_graph.resolve(objname)
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
            for attr in o.list_attributes('vertices','double',1).split(';'):
                if attr != '':
                    attrarray = np.asarray(E.find_attribute(attr))
                    structure.add_scalar_quantity(
                        attr.removeprefix('vertices.'),
                        attrarray
                    )
        return structure
        
    def register_graphite_objects(self):
        for objname in dir(self.scene_graph.objects):
            self.register_graphite_object(objname)

    def unregister_graphite_object(self,objname):
        self.structure_map[objname].remove()
        del self.structure_map[objname]
            
    def unregister_graphite_objects(self):
        for objname in dir(self.scene_graph.objects):
            self.unregister_graphite_object(objname)

    def commit_transform(self, o):
        structure = self.structure_map[o.name]
        xform = structure.get_transform()
        # if xform is identity, nothing to do
        if np.allclose(xform,np.eye(4)):
            return
        self.transform_object(o,xform)
        structure.reset_transform() # reset polyscope xform
        object_vertices = np.asarray(o.I.Editor.get_points())
        # tell polyscope that vertices have changed
        if hasattr(structure,'update_vertex_positions'):
            structure.update_vertex_positions(object_vertices)
        # for PolyScope pointsets it is a different function
        if hasattr(structure,'update_point_positions'):
            structure.update_point_positions(object_vertices)            

# ---- Some low-level manipulations of object points using NumPy primitives
            
    def get_object_bbox(self, o):
        vertices = np.asarray(o.I.Editor.get_points())
        pmin=np.array([np.min(vertices[:,0]),np.min(vertices[:,1]),np.min(vertices[:,2])])
        pmax=np.array([np.max(vertices[:,0]),np.max(vertices[:,1]),np.max(vertices[:,2])])
        return pmin, pmax

    def get_object_center(self, o):
        pmin,pmax = self.get_object_bbox(o)
        return 0.5*(pmin+pmax)
                
    def translate_object(self, o, T):
        vertices = np.asarray(o.I.Editor.get_points())
        vertices[:,0] = vertices[:,0] + T[0] 
        vertices[:,1] = vertices[:,1] + T[1] 
        vertices[:,2] = vertices[:,2] + T[2] 

    """ Apply a 4x4 homogeneous coord transform to object's vertices """
    def transform_object(self, o, xform):
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
        
#=====================================================
# Graphite application

graphite = GraphiteApp()

#=====================================================
# Add custom commands to Graphite Object Model, so that
# they appear in the menus, exactly like native Graphite
# commands written in C++

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
def extract_component(attr_name, component, interface, method):
    grob = interface.grob
    component = int(component) # all args to custom commands are passed as strings
    attr_array = np.asarray(
        grob.I.Editor.find_attribute('vertices.'+attr_name)
    )
    attr_array = attr_array[:,component]
    graphite.structure_map[grob.name].add_scalar_quantity(
        attr_name+'['+str(component)+']', attr_array
    )

# flips axes of a mesh
# note the in-place modification of object's coordinates
def flip_or_rotate(axis, center, interface, method):
    center = (center == 'true') # all args are strings
    grob = interface.grob
    
    if center:
        C = graphite.get_object_center(grob)
        graphite.translate_object(grob, -C)
        
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
        graphite.translate_object(grob, C)
        
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
# special flag, needed to avoid destroying the PolyScope structure
# that we just created, see GraphiteApp.handle_queued_command()
mslot.create_custom_attribute('keep_structures','true') 
mslot.create_custom_attribute('menu','/Attributes/Polyscope')
mslot.add_arg('attr_name', gom.meta_types.std.string)
mslot.add_arg('component', gom.meta_types.int, 0)

mslot = mclass.add_slot('flip_or_rotate',flip_or_rotate)
mslot.create_custom_attribute('help','flips axes of an object')
mslot.create_custom_attribute('menu','/Mesh')
mslot.add_arg('axis', gom.meta_types.FlipAxis, 'X')
mslot.add_arg('center', gom.meta_types.bool, 'true')

graphite.scene_graph.register_grob_commands(gom.meta_types.OGF.MeshGrob,mclass)

#=====================================================
# Initialize Polyscope and enter app main loop
ps.init()
ps.set_up_dir('z_up')
ps.set_front_dir('neg_y_front')
graphite.run(sys.argv)
