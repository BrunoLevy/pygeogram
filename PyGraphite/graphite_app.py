import polyscope as ps, polyscope.imgui as imgui, numpy as np
import time
import gompy.gom as gom, gompy.types.OGF as OGF

from auto_gui import MenuMap, ArgList, AutoGUI, PyAutoGUI
from polyscope_views import SceneGraphView
from mesh_grob_ops import MeshGrobOps
from terminal import Terminal
from rlcompleter import Completer
import imgui_ext

#=========================================================================

class GraphiteApp:
    """ @brief the Graphite Application class """

    #===== Application logic, callbacks ========================================

    def redraw(self):
        if self.drawing:
            return
        self.drawing = True
        ps.frame_tick()
        self.drawing = False

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
            self.redraw()

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
            self.redraw()

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
            self.redraw()

    # ============= constructor ==========================================

    def __init__(self):
        """ @brief GraphiteApp constructor """
        # In debug mode, all messages are displayed in standard output
        # rather than in-app terminal. This helps debugging when a problem
        # comes from a refresh triggered by a message display.
        self.debug_mode = False

        self.running = False

        self.menu_maps = {}
        self.reset_command()
        self.queued_execute_command = False # command execution is queued, for
        self.queued_close_command   = False # making it happen out off ps CB

        self.scene_graph = OGF.SceneGraph()

        # create a Graphite ApplicationBase. It has the printing and
        # progress callbacks, that are redirected here to some functions
        # (ending with _CB).
        application = OGF.ApplicationBase()
        self.scene_graph.application = application

        # terminal
        self.terminal = Terminal(self)

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

        # Load/Save
        self.scene_file_to_load = ''
        self.scene_file_to_save = ''
        self.object_file_to_save = ''
        self.object_to_save = None

        # Draw
        self.drawing = False

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

        ps.set_open_imgui_window_for_user_callback(False) # we draw our own win
        ps.set_user_callback(self.draw_GUI)
        self.running = True
        quiet_frames = 0
        self.scene_graph.application.start()

        while self.running:
            self.redraw()

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
                    imgui.GetIO().MouseDown[2] or
                    imgui.IsKeyPressed(imgui.ImGuiKey_Tab) or
                    imgui.IsKeyPressed(imgui.ImGuiKey_UpArrow) or
                    imgui.IsKeyPressed(imgui.ImGuiKey_DownArrow) or
                    imgui.IsKeyPressed(imgui.ImGuiKey_RightArrow) or
                    imgui.IsKeyPressed(imgui.ImGuiKey_LeftArrow)
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
            [300,ps.get_window_size()[1]-20], imgui.ImGuiCond_Once
        )
        unfolded,_ = imgui.Begin(
            'Graphite',True,imgui.ImGuiWindowFlags_MenuBar
        )
        if unfolded:
            self.draw_menubar()
            self.draw_scenegraph_GUI()
            self.draw_command()
        imgui.End()
        self.terminal.draw()
        self.draw_progressbar_window()
        self.draw_dialogs()

    #====== Main elements of GUI ==========================================

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
                if imgui.MenuItem('Load...'):
                    exts = gom.get_environment_value(
                        'grob_read_extensions'
                    ).split(';')
                    exts = [ ext.removeprefix('*.') for ext in exts if ext != '']
                    imgui_ext.OpenFileDialog(
                        'Load...',
                        exts,
                        '',
                        imgui_ext.ImGuiExtFileDialogFlags_Load
                    )
                if imgui.MenuItem('Save scene'):
                    imgui_ext.OpenFileDialog(
                        'Save scene',
                        ['graphite'],
                        'scene.graphite',
                        imgui_ext.ImGuiExtFileDialogFlags_Save
                    )
                imgui.Separator()
                # SceneGraphGraphiteCommands: Implemented in Python, atr
                # the end of this file, and registered in run()
                request = AutoGUI.draw_interface_menuitems(
                    self.scene_graph.I.Graphite
                )
                if request != None:
                    self.set_command(request)
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
                    'show terminal', None, self.terminal.visible
                ):
                    self.terminal.visible = not self.terminal.visible
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
            objects.append(self.scene_graph.ith_child(i))

        imgui.BeginListBox('##Objects',[-1,200])
        for object in objects:
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
                    old_params = self.scene_graph_view.get_view(
                        object
                    ).get_structure_params()
                    object.rename(self.rename_new)
                    self.scene_graph.current_object = object.name
                    # restore polyscope parameters
                    self.scene_graph_view.get_view(
                        object
                    ).set_structure_params(old_params)
                self.rename_old = None
                self.rename_new = None
        else: # standard operation (object is not being renamed)

            view = self.scene_graph_view.get_view(object)
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
                exts = gom.get_environment_value(
                    object.meta_class.name + '_write_extensions'
                ).split(';')
                exts = [ ext.removeprefix('*.') for ext in exts if ext != '' ]
                imgui_ext.OpenFileDialog(
                    'Save object...',
                    exts,
                    object.name + '.' + exts[0],
                    imgui_ext.ImGuiExtFileDialogFlags_Save
                )
                self.object_to_save = object

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
                    if v.grob.is_a(object.meta_class):
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
        imgui.PushStyleVar(imgui.ImGuiStyleVar_FramePadding, [2,0])
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
        if grob.is_a(OGF.SceneGraph):
            objname = 'scene_graph'
            if self.scene_graph.current() != None:
                objname = ( objname + ', current=' +
                            self.scene_graph.current().name )
            imgui.Text('Object: ' + objname)
        else:
            objname = grob.name
            # Ask the meta_class rather than calling is_a(),
            # else Graphite will complain that the Interface is
            # locked when calling is_a() !!!
            if (self.request.object().meta_class.is_subclass_of(OGF.Interface)):
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

    def draw_dialogs(self):
        self.scene_file_to_load,_ = imgui_ext.FileDialog('Load...')
        self.scene_file_to_save,_ = imgui_ext.FileDialog('Save scene')
        self.object_file_to_save,_ = imgui_ext.FileDialog('Save object...')

    def handle_queued_command(self):
        """
        @brief Executes the Graphite command if it was marked for execution
        @details Graphite command is not directly called when once pushes the
          button, because it needs to be called outside the PolyScope frame
          for the terminal and progress bars to work, since they trigger
          additional PolyScope frames (nesting PolyScope frames is forbidden)
        """
        if self.queued_execute_command:
            self.scene_graph_view.commit_transform() # Commit all xform guizmos
            self.invoke_command()
            self.queued_execute_command = False

        if self.queued_close_command:
            self.reset_command()
            self.queued_close_command = False

        if self.scene_file_to_load != '':
            self.scene_graph.load_object(self.scene_file_to_load)
            ps.reset_camera_to_home_view()
            self.scene_file_to_load = ''

        if self.scene_file_to_save != '':
            self.scene_graph_view.copy_polyscope_params_to_grob()
            self.scene_graph.save(self.scene_file_to_save)
            self.scene_file_to_save = ''

        if self.object_file_to_save != '' and self.object_to_save != None:
            view = self.scene_graph_view.get_view(self.object_to_save)
            view.copy_polyscope_params_to_grob()
            self.object_to_save.save(self.object_file_to_save)
            self.object_file_to_save = ''
            self.object_to_save = None

        self.terminal.handle_queued_command()

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


#============================================================================

class SceneGraphGraphiteCommands:
    """ The commands in the second section of the File menu """

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
            method    : str
    ):
        """ @brief deletes all objects in the scene-graph """
        interface.grob.clear()
        ps.reset_camera_to_home_view()

#============================================================================
