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
#  - put GraphiteApp in separate file also

import polyscope as ps, polyscope.imgui as imgui, numpy as np
import math,sys,time,typing
import gompy # always import gompy *after* polyscope

gom = gompy.interpreter()
OGF = gom.meta_types.OGF

from auto_gui import MenuMap, ArgList, AutoGUI, PyAutoGUI
from polyscope_views import SceneGraphView
from mesh_grob_ops import MeshGrobOps

#=========================================================================

class GraphiteApp:
    """ @brief the Graphite Application class """

    #===== Application logic, callbacks ========================================

    def out_CB(self,msg:str):
        """
        @brief Message display callback
        @details Called whenever Graphite wants to display something. 
          It generates a new PolyScope frame. Since commands are invoked outside
          of a PolyScope frame, and since messages are triggered by commands
          only, (normally) there can't be nested PolyScope frames.
        @param[in] msg the message to be displayed
        """
        self.print(msg)
        while self.running and self.message_changed_frames > 0:
            ps.frame_tick() 

    def err_CB(self,msg:str):
        """
        @brief Error display callback
        @details Called whenever Graphite wants to display something. 
          It generates a new PolyScope frame. Since commands are invoked outside
          of a PolyScope frame, and since messages are triggered by commands
          only, (normally) there can't be nested PolyScope frames.
        @param[in] msg the error message to be displayed
        """
        self.show_terminal=True # make terminal appear if it was hidden
        self.print(msg)
        while self.running and self.message_changed_frames > 0:
            ps.frame_tick()
            
    def progress_begin_CB(self,taskname:str):
        """
        @brief Progress bar begin callback
        @details Called whenever Graphite wants to start a progress bar.
          It generates a new PolyScope frame. Since commands are invoked outside
          of a PolyScope frame, and since messages are triggered by commands
          only, (normally) there can't be nested PolyScope frames.
        @param[in] taskname the name of the task in the progress bar
        """
        self.progress_task = taskname
        self.progress_percent = 0
        if self.running:
            ps.frame_tick()

    def progress_CB(self,progress_percent:int):
        """
        @brief Progress bar progression callback
        @details Called whenever Graphite wants to update a progress bar.
          It generates a new PolyScope frame. Since commands are invoked outside
          of a PolyScope frame, and since messages are triggered by commands
          only, (normally) there can't be nested PolyScope frames.
        @param[in] progress_percent percentage of progression
        """
        self.progress_percent = progress_percent
        if self.running:
            ps.frame_tick()

    def progress_end_CB(self):
        """
        @brief Progress bar end callback
        @details Called whenever Graphite wants to terminate a progress bar.
          It generates a new PolyScope frame. Since commands are invoked outside
          of a PolyScope frame, and since messages are triggered by commands
          only, (normally) there can't be nested PolyScope frames.
        """
        self.progress_task = None
        if self.running:
            ps.frame_tick()

    # ============= constructor ==========================================
            
    def __init__(self):
        """ @brief GraphiteApp constructor """
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
        """ 
        @brief Main application loop
        @param[in] args command line arguments
        """

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

            # Unhighlight highlighted object based on elapsed time
            self.scene_graph_view.unhighlight_object()
            
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
        """ @brief Draws Graphite GUI """
        imgui.SetNextWindowPos([340,10],imgui.ImGuiCond_Once)
        imgui.SetNextWindowSize(
            [300,ps.get_window_size()[1]-20],imgui.ImGuiCond_Once
        )
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

    def print(self, msg: str):
        """ 
        @brief Prints a message to the terminal window in Graphite
        @details Triggers graphics update for 3 frames, for leaving the
          slider enough time to reach the last line in the terminal
        @param[in] msg the message to be printed
        """
        self.message = self.message + msg
        self.message_changed_frames = 3 # needs three frames for SetScrollY()
                                        # to do the job
        
    #====== Main elements of GUI ==========================================

    def draw_terminal_window(self):
        """
        @brief Draws the terminal window
        @details Handles scrolling to the last line each time a new message
          is printed
        @see out_CB(), err_CB()
        """
        if self.show_terminal: 
            imgui.SetNextWindowPos(
                [660,ps.get_window_size()[1]-260],imgui.ImGuiCond_Once
            )
            imgui.SetNextWindowSize([600,200],imgui.ImGuiCond_Once)
            _,self.show_terminal = imgui.Begin('Terminal',self.show_terminal)
            imgui.Text(self.message)
            if self.message_changed_frames > 0:
                imgui.SetScrollY(imgui.GetScrollMaxY())
                self.message_changed_frames = self.message_changed_frames - 1
            imgui.End()

    def draw_progressbar_window(self):
        """
        @brief Draws the progressbar window
        @see progress_begin_CB(), progress_CB(), progress_end_CB()
        """
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
        """
        @brief Draws Graphite's main menubar
        """
        if imgui.BeginMenuBar():
            if imgui.BeginMenu('File'):
                # SceneGraphGraphiteCommands: Implemented in Python, atr
                # the end of this file, and registered in run()
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
        """
        @brief Draws the GUI of the SceneGraph, with the editable list of objs
        """
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

    def draw_object_GUI(self, object: OGF.Grob):
        """
        @brief Draws the GUI for editing one Graphite object. 
        @details Handles visibility button, object menus, renaming, move up / 
          move down buttons and delete button. Used by draw_scenegraph_GUI()
        @param[in] object the Graphite object
        """
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
                    # backup polyscope parameters before renaming
                    # (because object will have a completely different
                    #  polyscope structure, and polyscope persistent
                    #  parameters mechanism is not aware that it is the
                    #  same object that was renamed)
                    old_params = self.scene_graph_view.view_map[
                        self.rename_old
                    ].get_structure_params()
                    object.rename(self.rename_new)
                    self.scene_graph.current_object = object.name
                    # restore polyscope parameters
                    self.scene_graph_view.view_map[
                        object.name
                    ].set_structure_params(old_params)                    
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
            if imgui.IsItemHovered():
                imgui.SetTooltip(
                    objname + ':' + object.meta_class.name.removeprefix('OGF::')
                )
            if sel:
                self.scene_graph.current_object = objname
                if imgui.IsMouseDoubleClicked(0):
                    self.scene_graph_view.show_only(object)
                self.scene_graph_view.highlight_object(object)

        self.draw_object_menu(object)

        if show_buttons:
            imgui.SameLine()
            self.draw_object_buttons(object)
        
    def draw_object_menu(self, object: OGF.Grob):
        """ 
        @brief Draws the contextual menu associated with an object
        @details Handles general commands, implemented here, and commands
          from Graphite Object models, using the MenuMap. Used by
          draw_object_GUI().
        """

        if imgui.BeginPopupContextItem(object.name+'##ops'):
            if imgui.MenuItem('rename'):
                self.rename_old = object.name
                self.rename_new = object.name

            if imgui.MenuItem('duplicate'):
                self.scene_graph.current_object = object.name
                sgv = self.scene_graph_view
                old_view = self.scene_graph_view.get_view(
                    self.scene_graph.current()
                )
                params = old_view.get_structure_params()
                new_object = self.scene_graph.duplicate_current()
                self.scene_graph.current_object = new_object.name
                new_view = self.scene_graph_view.get_view(new_object)
                new_view.set_structure_params(params)
                self.rename_old = new_object.name
                self.rename_new = new_object.name
                
            if imgui.MenuItem('save object'):
                view = self.scene_graph_view.get_view(object)
                view.copy_polyscope_params_to_grob()
                self.set_command(object.save)

            if imgui.MenuItem('commit transform'):
                self.scene_graph_view.get_view(object).commit_transform()
            if imgui.IsItemHovered():
                imgui.SetTooltip(
                   'transforms vertices according to Polyscope transform guizmo'
                )

            if imgui.MenuItem('copy style to all'):
                object_view = self.scene_graph_view.get_view(object)
                params = object_view.get_structure_params()
                for v in self.scene_graph_view.get_views():
                    if v.grob.meta_class.is_a(object.meta_class):
                        v.set_structure_params(params)
            if imgui.IsItemHovered():
                imgui.SetTooltip(
                    'copy graphic style to all objects of same type'
                )
                
            imgui.Separator() 
            request = self.get_menu_map(object).draw_menus(object)
            if request != None:
                self.set_command(request)
            imgui.EndPopup()

    def draw_object_buttons(self, object: OGF.Grob):
        """
        @brief Draws and handles the buttons associated with an object
        @param[in] object the object
        @details Draws the move up, move down and delete buttons. Used
          by draw_object_GUI()
        """
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
        """ @brief Draws the GUI for the current Graphite command """
        if self.request == None:
            return
        
        imgui.Text('Command: ' + self.request.method().name.replace('_',' '))
        if (imgui.IsItemHovered() and
           self.request.method().has_custom_attribute('help')):
           imgui.SetTooltip(
               self.request.method().custom_attribute_value('help')
           )
        grob = self.get_grob(self.request)
        if grob.meta_class.is_a(OGF.SceneGraph):
            objname = 'scene_graph'
            if self.scene_graph.current() != None:
                objname = ( objname + ', current=' +
                            self.scene_graph.current().name )
            imgui.Text('Object: ' + objname)
        else:
            objname = grob.name
            if (self.request.object().meta_class.is_a(OGF.Interface)):
                objnames = gom.get_environment_value(
                    grob.meta_class.name + '_instances'
                )
                imgui.Text('Object:')
                imgui.SameLine()
                _,objname = AutoGUI.combo_box('##Target',objnames,objname)
                self.request.object().grob = getattr(
                    self.scene_graph.objects,objname
                )
            else:
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

    def handle_queued_command(self):
        """
        @brief Executes the Graphite command if it was marked for execution
        @details Graphite command is not directly called when once pushes the
          button, because it needs to be called outside the PolyScope frame
          for the terminal and progress bars to work, since they trigger 
          additional PolyScope frames (nesting PolyScope frames is forbidden)
        """
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

            
    def get_grob(self,request: OGF.Request) -> OGF.Grob:
        """
        @brief Gets the Graphite object from a Request
        @details The Request passed to set_command() may be in the
         form grob.interface.method or simply grob.method.
         This function gets the grob in both cases.
        @return the Grob associated with the Request
        """
        object = request.object()
        if(hasattr(object,'grob')):
            return object.grob
        else:
            return object

    def get_menu_map(self, grob: OGF.Grob):
        """
        @brief Gets the MenuMap associated with a grob
        @param grob the Graphite object
        @details The MenuMap is constructed the first time the function is
          called for a Grob class, then stored in a dictionary for the next
          times
        @return the MenuMap associated with the graphite object
        """
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
        """ Invokes current Graphite command with the args from the GUI """
        self.request(**self.args) #**: expand dict as keywords func call
        
    #===== Other menus from metainformation =================================
                    
    def draw_object_commands_menus(self,o : OGF.Object):
        """ 
        @brief Draws menus for all commands associated with a Graphite object 
        @param[in] o the Graphite object
        """
        # get all interfaces of the object
        for interface_name in dir(o.I):
            interface = getattr(o.I,interface_name)
            # keep only those that inherit OGF::Commands
            if interface.meta_class.is_a(OGF.Commands):
                if imgui.BeginMenu(interface_name):
                    self.draw_interface_menuitems(interface)
                    imgui.EndMenu()

    def draw_interface_menuitems(self, interface : OGF.Interface):
        """ 
        @brief Draws menu items for all slots of an interface 
        @param[in] interface the interface, for instance, meshgrob.I.Shapes
        """
        mclass = interface.meta_class
        for i in range(mclass.nb_slots()):
            mslot = mclass.ith_slot(i)
            if not hasattr(OGF.Interface,mslot.name):
                self.draw_request_menuitem(getattr(interface,mslot.name))

    def draw_request_menuitem(self, request : OGF.Request):
        """ 
        @brief Draws a menu item for a given Request (that is, a closure) 
        @param[in] request the Request
        """
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
        ps.reset_camera_to_home_view()

    def save_scene(
            interface       : OGF.Interface,
            method          : str,
            scene_filename  : str
    ):
        """
        @brief saves a file
        @param[in] scene_filename = scene.graphite graphite scenegraph file
        """
        graphite.scene_graph_view.copy_polyscope_params_to_grob()
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
        @param[in] axis = PERM_XYZ rotation axis or permutation
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
