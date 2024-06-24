import polyscope as ps
import numpy as np
import gompy
import math,sys

class GraphiteCommand:
    """ Handles user interface for Graphite commands """
    def __init__(self):
        self.reset()

    """ Sets current Graphite command, edited in the GUI """
    def set(self, request):
        self.request = request
        self.args = {}
        mmethod = self.request.method()
        for i in range(mmethod.nb_args()):
            val = ''
            if mmethod.ith_arg_has_default_value(i):
                val = mmethod.ith_arg_default_value_as_string(i)
            self.args[mmethod.ith_arg_name(i)] = val

    """ Resets current Graphite command """
    def reset(self):
        self.request = None
        self.args = None

    """ Invokes current Graphite command with the args entered in the GUI """
    def invoke(self):
        self.request(**self.args) #**: expand dict as keywords func call

    """ Draws the GUI for the current Graphite command """
    def draw(self):
        if self.request != None:
            grob = self.request.object().grob
            if grob.meta_class.name == 'OGF::SceneGraph':
                objname = 'scene_graph'
                if scene_graph.current() != None:
                    objname = objname + ', current=' + scene_graph.current().name
            else:                
                objname = grob.name
                
            ps.imgui.Text('Object: '  + objname)
            ps.imgui.Text('Command: ' + self.request.method().name.replace('_',' '))
            if ps.imgui.IsItemHovered() and self.request.method().has_custom_attribute('help'):
                ps.imgui.SetTooltip(self.request.method().custom_attribute_value('help'))
            mmethod = self.request.method()
            if mmethod.nb_args() != 0:
                ps.imgui.BeginListBox('##Command',[-1,150])
                has_advanced_args = False
                for i in range(mmethod.nb_args()):
                    tooltip = None
                    if mmethod.ith_arg_has_custom_attribute(i,'advanced'):
                        has_advanced_args = True
                    else:
                        if mmethod.ith_arg_has_custom_attribute(i,'help'):
                            tooltip = mmethod.ith_arg_custom_attribute_value(i,'help')
                            self.arg_handler(
                               mmethod.ith_arg_name(i), mmethod.ith_arg_type(i), tooltip
                            )
                if has_advanced_args:
                    if ps.imgui.TreeNode('Advanced'+'##'+objname+'.'+mmethod.name):
                        ps.imgui.TreePop()
                        for i in range(mmethod.nb_args()):
                            tooltip = None
                            if mmethod.ith_arg_has_custom_attribute(i,'advanced'):
                                if mmethod.ith_arg_has_custom_attribute(i,'help'):
                                    tooltip = mmethod.ith_arg_custom_attribute_value(i,'help')
                                    self.arg_handler(
                                       mmethod.ith_arg_name(i), mmethod.ith_arg_type(i), tooltip
                                    )
                ps.imgui.EndListBox()
            if ps.imgui.Button('OK'):
                grob = self.request.object().grob                
                unregister_graphite_objects()
                self.invoke()
                if grob.meta_class.is_a(gom.meta_types.OGF.MeshGrob):
                    self.request.object().grob.I.Surface.triangulate()
                register_graphite_objects()
                command.reset()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Apply and close command')
            ps.imgui.SameLine()
            if ps.imgui.Button('Apply'):
                grob = self.request.object().grob                
                unregister_graphite_objects()
                self.invoke()
                if grob.meta_class.is_a(gom.meta_types.OGF.MeshGrob):
                    self.request.object().grob.I.Surface.triangulate()
                register_graphite_objects()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Apply and keep command open')
            ps.imgui.SameLine()
            if ps.imgui.Button('Cancel'):
                command.reset()
            if ps.imgui.IsItemHovered():
                ps.imgui.SetTooltip('Close command')

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
        self.label(property_name, tooltip)
        ps.imgui.SameLine()
        ps.imgui.PushItemWidth(-20)
        val = self.args[property_name]
        val = (val == 'true')
        _,val = ps.imgui.Checkbox(
            '##properties##' + property_name, val
        )
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

    def OGF__MeshGrobName_handler(self, property_name, mtype, tooltip):
        values = gom.get_environment_value('OGF::MeshGrob_instances')
        self.combo_box(property_name, values, tooltip)

    def OGF__GrobClassName_handler(self, property_name, mtype, tooltip):
        values = gom.get_environment_value('grob_types')
        self.combo_box(property_name, values, tooltip)

    def enum_handler(self, property_name, menum, tooltip):
        values = ''
        for i in range(menum.nb_values()):
            if i != 0:
                values = values + ';'
            values = values + menum.ith_name(i)
        self.combo_box(property_name, values, tooltip)
            
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
        _,new_index = ps.imgui.Combo('##properties##'+property_name, old_index, values)
        ps.imgui.PopItemWidth()
        self.args[property_name] = values[new_index]

    def label(self, property_name, tooltip):
        ps.imgui.Text(property_name.replace('_',' '))
        if tooltip != None and ps.imgui.IsItemHovered():
            ps.imgui.SetTooltip(tooltip)
        
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
            self.set(request)
        if ps.imgui.IsItemHovered() and request.method().has_custom_attribute('help'):
            ps.imgui.SetTooltip(request.method().custom_attribute_value('help'))
            
running = True
command = GraphiteCommand()
       
def draw_graphite_gui():
    global running, scene_graph, command
    ps.imgui.SetNextWindowPos([350,10])
    ps.imgui.SetNextWindowSize([300,ps.get_window_size()[1]-20])
    ps.imgui.Begin('Graphite',True,ps.imgui.ImGuiWindowFlags_MenuBar)
    if ps.imgui.BeginMenuBar():
       if ps.imgui.BeginMenu('File'):
           command.draw_request_menuitem(getattr(scene_graph.I.Scene,'create_object'))
           command.draw_request_menuitem(getattr(scene_graph.I.Scene,'delete_all'))
           ps.imgui.Separator()
           if ps.imgui.MenuItem('show all'):
                for objname in dir(scene_graph.objects):
                    ps.get_surface_mesh(objname).set_enabled(True)
           if ps.imgui.MenuItem('hide all'):
                for objname in dir(scene_graph.objects):
                    ps.get_surface_mesh(objname).set_enabled(False)
           ps.imgui.Separator()
           if ps.imgui.MenuItem('quit'):
               running = False
           ps.imgui.EndMenu()
       ps.imgui.EndMenuBar()
    C = scene_graph.current()
    if C != None:
        nv = C.I.Editor.nb_vertices
        nf = C.I.Editor.nb_facets
        ps.imgui.Text(C.name)
        ps.imgui.Text('   vertices: ' + str(nv))
        ps.imgui.Text('   facets: ' + str(nf))

    objects = dir(scene_graph.objects)
    ps.imgui.BeginListBox('##Objects',[-1,200])
    #ps.imgui.Selectable('SceneGraph',False)
    #if ps.imgui.BeginPopupContextItem('SceneGraph##ops'):
    #    command.draw_request_menuitem(getattr(scene_graph.I.Scene,'create_object'))
    #    command.draw_request_menuitem(getattr(scene_graph.I.Scene,'delete_all'))
    #    # command.draw_object_commands_menus(scene_graph)
    #    ps.imgui.EndPopup()	      
    for objname in objects:
        sel,_=ps.imgui.Selectable(
            objname, (objname == scene_graph.current().name),
            ps.imgui.ImGuiSelectableFlags_AllowDoubleClick
        )
        if sel:
            scene_graph.current_object = objname
            if ps.imgui.IsMouseDoubleClicked(0):
                for objname2 in dir(scene_graph.objects):
                    ps.get_surface_mesh(objname2).set_enabled(objname2 == objname)
            
        if ps.imgui.BeginPopupContextItem(objname+'##ops'):
            if ps.imgui.MenuItem('delete object'):
                scene_graph.current_object = objname
                command.set(scene_graph.I.Scene.delete_current)
                
            if ps.imgui.MenuItem('rename object'):
                scene_graph.current_object = objname
                command.set(scene_graph.I.Scene.rename_current)

            if ps.imgui.MenuItem('duplicate object'):
                scene_graph.current_object = objname
                command.set(scene_graph.I.Scene.duplicate_current)

            if ps.imgui.MenuItem('transform object'):
                print(dir(ps.get_surface_mesh(objname)))

            if ps.imgui.MenuItem('commit transform'):
                surface_mesh = ps.get_surface_mesh(objname)
                xform = surface_mesh.get_transform()
                object = getattr(scene_graph.objects,objname)
                object_vertices = np.asarray(object.I.Editor.get_points())
                vertices = np.c_[object_vertices, np.ones(object_vertices.shape[0])] # add a column of 1
                vertices = np.matmul(vertices,np.transpose(xform))    # transform all the vertices
                weights = vertices[:,-1]                              # get 4th column
                vertices = vertices[:,:-1]                            # get the rest
                vertices = vertices/weights[:,None]                   # divide by the weights
                np.copyto(object_vertices,vertices)                   # inject new vertices into mesh
                surface_mesh.reset_transform()                        # reset polyscope xform to identity
                surface_mesh.update_vertex_positions(object_vertices) # tell polyscope that vertices have changed
                
            ps.imgui.Separator() 
            command.draw_object_commands_menus(getattr(scene_graph.objects,objname))
            ps.imgui.EndPopup()	      
    ps.imgui.EndListBox()
    command.draw()
    ps.imgui.End()
    
def register_graphite_object(O):
   pts = np.asarray(O.I.Editor.get_points())
   tri = np.asarray(O.I.Editor.get_triangles())
   structure = ps.register_surface_mesh(O.name,pts,tri)
   structure.set_transform([[1, 0, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0],[0, 0, 0, 1]])

def register_graphite_objects():
   for i in dir(scene_graph.objects):
       register_graphite_object(scene_graph.resolve(i))

def unregister_graphite_objects():
   for i in dir(scene_graph.objects):
       ps.remove_surface_mesh(i)

scene_graph = gom.meta_types.OGF.SceneGraph.create()
for f in sys.argv[1:]:
    scene_graph.load_object(f)

ps.init()
ps.set_open_imgui_window_for_user_callback(False)
ps.set_user_callback(draw_graphite_gui)
register_graphite_objects()

while running:
    ps.frame_tick()
