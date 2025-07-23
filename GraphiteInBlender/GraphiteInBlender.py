import bpy
import gompy, gompy.types.OGF as OGF, gompy.gom as gom
import numpy as np
import random

## TODO
# [x] add menu to Blender
# [x] draw command GUI in Blender
# [x] invoke command from Blender GUI
# [x] get all commands in menu, interpret MenuMap as Blender menu
# [x] cleaner handling of arg types
#   [ ] pulldown menu for MeshGrobName
#   [ ] pulldown menu for enums
# [ ] Scene submenu with
#   [ ] load scene / save scene
#   [ ] load object
#   [ ] clear scene
#   [ ] create object / shapes
#   [ ] show all / hide all
# [x] Error boxes anb messages
# [ ] Progressbar
# [ ] Logger
# [ ] Graphite commands in context menu

## https://docs.blender.org/api/current/bpy.types.Operator.html#dialog-box
## https://blender.stackexchange.com/questions/102446/how-to-generate-temporary-operators-with-dynamic-properties

# ------------------------------------------------------

# Change color mode... Only works if 3D view is active when invoking script
# (works in 'Scripting mode', does not work in '<shift><F4>' mode with only
# a Python console)
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.color_type = 'OBJECT'

# Converts a Graphite object to a Blender object
def send_object_to_blender(obj):
   verts = np.asarray(obj.I.Editor.get_points())
   faces = np.asarray(obj.I.Editor.get_triangles())
   print('New mesh: ', verts.shape[0], faces.shape[0])
   try:
      bmesh = bpy.data.meshes['GI.' + obj.name + '.mesh']
   except:
      bmesh = bpy.data.meshes.new('GI.' + obj.name + '.mesh')
   try:
      bobj  = bpy.data.objects['GI.' + obj.name]
   except:
      bobj  = bpy.data.objects.new('GI.' + obj.name, bmesh)
   bmesh.clear_geometry()
   bmesh.from_pydata(verts, [], faces)
   bmesh.update(calc_edges=True)
   if bpy.context.collection.objects.find(bobj.name) == -1:
      bpy.context.collection.objects.link(bobj)
   bpy.data.objects[bobj.name].color = [ # or use 'random color' mode in viewer
      random.uniform(0,1),
      random.uniform(0,1),
      random.uniform(0,1),
      1
   ]

# Sends all Graphite objects to Blender
def send_objects_to_blender(prefix = ''):
   for obj in sg.objects:
      if prefix == '' or obj.name.startswith(prefix):
         send_object_to_blender(obj)

# Removes from a Blender collection all objects not present in Graphite
# (including the default 'Cube')
def clean_blender_collection(collection):
    to_remove = [
        obj for obj in collection if
            obj.name == 'Cube' or (obj.name.startswith('GI.') and not \
               sg.is_bound(obj.name.removeprefix('GI.').removesuffix('.mesh')))
    ]
    for obj in to_remove:
        collection.remove(obj)

# Removes from all blender collections objects that are not present in Graphite
def clean_blender():
    clean_blender_collection(bpy.data.meshes)
    clean_blender_collection(bpy.data.objects)
    clean_blender_collection(bpy.context.collection.objects)

# ------------------------------------------------------

# Create SceneGraph if not already created (we may want
# to run script several times)
# Create a couple of objets to play with
sg = OGF.SceneGraph.instance
if sg == None:
    clean_blender()
    sg = OGF.SceneGraph()
    S = OGF.MeshGrob(sg,'S')
    S.I.Shapes.create_sphere([0, 0, 0], 1.2)
    C = OGF.MeshGrob(sg,'C')
    C.I.Shapes.create_box([-1, -1, -1],[1, 1, 1])
    C.I.Surface.triangulate()
    send_objects_to_blender()

# ------------------------------------------------------

class AutoGUI:

    """ Creates Blender property editor for command arguments
        based on their types and dialog boxes for Graphite commands """

    def editor_for_arg(name: str, mtype: OGF.MetaType, val: str, help: str):
        help = name if help == None else help
        editor_name = mtype.name.replace(' ','_').replace(':','_') + '_editor'
        if hasattr(AutoGUI, editor_name):
            return getattr(AutoGUI, editor_name)(name, mtype, val, help)
        return AutoGUI.string_editor(name, mtype, val, help)

    def string_editor(name, mtype, val, help):
        if val == None:
            return bpy.props.StringProperty(name=name, description=help)
        else:
            return bpy.props.StringProperty(
                name=name, default=val, description=help
            )

    def int_editor(name, mtype, val, help):
        if val == None:
            return bpy.props.IntProperty(name=name, description=help)
        else:
            return bpy.props.IntProperty(
                name=name, default=int(val), description=help
            )

    def unsigned_int_editor(name, mtype, val, help):
        if val == None:
            return bpy.props.IntProperty(name=name, description=help, min=0)
        else:
            return bpy.props.IntProperty(
                name=name, default=int(val), description=help, min=0
            )

    def float_editor(name, mtype, val, help):
        if val == None:
            return bpy.props.FloatProperty(name=name, description=help)
        else:
            return bpy.props.FloatProperty(
                name=name, default=float(val), description=help
            )

    double_editor = float_editor

    def bool_editor(name, mtype, val, help):
        if val == None:
            return bpy.props.BoolProperty(name=name, description=help)
        else:
            return bpy.props.BoolProperty(
                name=name, default=(val == 'true'), description=help
            )

    def operator_id(mmethod: OGF.MetaMethod):
        return 'wm.gi_operator_' + mmethod.name.lower()

    def menu_id(path: str):
        return 'OBJECT_MT_GI_' + \
            path.replace('/','_').replace(' ','_').replace('-','_') + '_menu'

    def create_operator_for_method(mmethod_in: OGF.MetaMethod):
        """ Creates a Blender operator class from an OGF MetaSlot """

        # This is a locally defined class, creates a different class
        # at each invokation of this function ! (I love Python for that)
        class GIDynamicOperator(bpy.types.Operator):
            mmethod = mmethod_in
            bl_idname = AutoGUI.operator_id(mmethod)
            bl_label = mmethod.name.replace('_',' ')
            if mmethod.has_custom_attribute('help'):
                bl_description = mmethod.custom_attribute_value('help')

            def get_target(self,context):
                """ Gets target of the Graphite command from Blender context"""
                names = [ obj.name.removeprefix('GI.') \
                  for obj in context.selected_objects \
                  if sg.is_bound(obj.name.removeprefix('GI.')) \
                ]
                cmd = GIDynamicOperator.bl_label
                if len(names) == 0:
                    self.report({'ERROR'}, cmd + ": No object selected")
                    return None
                if len(names) > 1:
                    self.report({'ERROR'}, cmd + ": Too many objects selected")
                    return None
                return sg.resolve(names[0])

            def execute(self,context):
                """ Invoked when the OK button of the dialog is pressed"""
                target = self.get_target(context)
                if target == None:
                    return {'FINISHED'}
                args = {}
                for i in range(mmethod.nb_args()):
                    arg_name = mmethod.ith_arg_name(i)
                    arg_val = getattr(self,arg_name)
                    args[arg_name] = arg_val
                request = OGF.Request(
                    target.query_interface(
                        self.mmethod.container_meta_class().name
                    ),
                    self.mmethod
                )
                request(**args) #**: expand dict as keywords func call
                send_objects_to_blender()
                clean_blender()
                return {'FINISHED'}

            def invoke(self, context, event):
                """ Invoked when the menu entry is selected. Opens the dialog."""
                wm = context.window_manager
                return wm.invoke_props_dialog(self)

            def __init__(self):
                mmethod = GIDynamicOperator.mmethod

        # Create the editors for all arguments using AutoGUI.editor_for_arg()
        # Store the editors in the *annotations* ! (this is where Blender's
        # function invoke_props_dialog() expects to find them !!!)
        mmethod = GIDynamicOperator.mmethod
        for i in range(mmethod.nb_args()):
            real_arg_name = mmethod.ith_arg_name(i)
            arg_name = real_arg_name.replace('_',' ')
            arg_type = mmethod.ith_arg_type(i)
            arg_val = None
            arg_desc = arg_name
            if mmethod.ith_arg_has_default_value(i):
                arg_val = mmethod.ith_arg_default_value_as_string(i)
            if mmethod.ith_arg_has_custom_attribute(i, 'help'):
                arg_desc = mmethod.ith_arg_custom_attribute_value(i, 'help')
            GIDynamicOperator.__annotations__[real_arg_name] = \
                AutoGUI.editor_for_arg(arg_name, arg_type, arg_val, arg_desc)

        bpy.utils.register_class(GIDynamicOperator)
        return GIDynamicOperator

# ------------------------------------------------------

class MenuMap:
    """ @brief Handles the menu hierarchy associated with a grob """
    def __init__(self, grob_meta_class : OGF.MetaClass):
        """
        @brief MenuMap constructor
        @param[in] grob_meta_class the GOM meta-class of a Graphite object
        """
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

    def insert(
            self,
            menu_dict : dict, menu_name : str,
            mslot : OGF.MetaSlot
    ) :
        """
        @brief Inserts an entry in the menumap (used internally)
        @param[in] menu_dict a menu dictionary
        @param[in] menu_name the name of the menu to be inserted, with slashes
        @param[in] mslot the meta-slot of the method corresponding to the menu
        """
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


    def create_menu_class(self, path : str = None, menudict : dict = None) :
        if path == None:
            path = 'Alloy'

        if menudict == None:
            menudict = self.root

        # This is a locally defined class, creates a different class
        # at each invokation of this function ! (I love Python for that)
        class GIDynamicMenu(bpy.types.Menu):
            bl_label = path.rsplit('/',1)[-1].replace('_',' ')
            bl_idname = AutoGUI.menu_id(path)

            def __init__(self):
                self.menudict = menudict

            def draw(self, context):
                layout = self.layout
                for k,v in self.menudict.items():
                    if isinstance(v,dict):
                        layout.menu(AutoGUI.menu_id(path + '/' + k))
                    else:
                        layout.operator(AutoGUI.operator_id(v))

            def draw_item(self, context):
                layout = self.layout
                layout.menu(GIDynamicMenu.bl_idname)

        # Now we need to recursively create all the classes for the
        # submenus and the referenced operators
        for k,v in menudict.items():
            if isinstance(v,dict):
                self.create_menu_class(path + '/' + k, v)
            else:
                AutoGUI.create_operator_for_method(v)

        bpy.utils.register_class(GIDynamicMenu)
        return GIDynamicMenu


# --------------------------------------------------------------------------

mesh_grob_menu = MenuMap(OGF.MeshGrob)
GIMeshGrobMenu = mesh_grob_menu.create_menu_class()

if __name__ == "__main__":
     bpy.types.TOPBAR_MT_editor_menus.append(GIMeshGrobMenu.draw_item)
