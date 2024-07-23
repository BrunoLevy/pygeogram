import typing
import polyscope.imgui as imgui
import gompy
gom = gompy.interpreter()
OGF = gom.meta_types.OGF

#===============================================================================

class MenuMap:
    """ @brief Handles the menu hierarchy associated with a grob """
    def __init__(self, grob_meta_class : gom.meta_types.OGF.MetaClass):
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

    def draw_menus(
            self, o : OGF.Object, menudict : dict = None
    ) -> OGF.Request:
        """
        @brief Draws the menus stored in a menumap 
        @param[in] o an object of the meta-class given to the constructor
        @param[in] optional menu dict (used internally, uses root if unspecified)
        @return a request if a menu item was selected 
        """
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


class ArgList(dict):
    """ 
    @brief A dictionary with attribute-like access 
    @details used by AutoGUI to set/get values in arglists or GOM objects
             with the same syntax
    """
    def __getattr__(self, key):
        return self[key]
    
    def __setattr__(self, key, value):
        self[key] = value

    def __dir__(self):
        return super().__dir__() + [str(k) for k in self.keys()]
    
#=========================================================================

class AutoGUI:
    """ 
    @brief Functions to generate the GUI from GOM meta-information 
    """
    
    #========= GUI handlers for commands =================================
    
    def draw_command(request : OGF.Request, args : ArgList):
        """ 
        @brief Handles the GUI for a Graphite command 
        @details Draws a dialog box to edit the arguments of a Request. A Request
          is a closure (object.function) where object is a Graphite object.
        @param[in] request the Request being edited
        @param[in,out] args the arguments of the Request
        """
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
                    AutoGUI.slot_arg_handler(args, mmethod, i)
            if has_advanced_args:
                if imgui.TreeNode(
                        'Advanced'+'##'+str(request.object())+'.'+mmethod.name
                ):
                    imgui.TreePop()
                    for i in range(mmethod.nb_args()):
                        if AutoGUI.ith_arg_is_advanced(mmethod,i):
                            AutoGUI.slot_arg_handler(args, mmethod, i)
            imgui.EndListBox()

    def init_command_args(request : OGF.Request) -> ArgList:
        """ 
        @brief Initializes an ArgList with command arguments 
        @param[in] request a Request, that is, object.function, where object is
           a Graphite object
        @return an ArgList with the default values of the Request arguments
        """
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

    def draw_object_commands_menus(o : OGF.Object) -> OGF.Request:
        """ 
        @brief Draws menus for all commands associated with a Graphite object 
        @param[in] o the Graphite object
        @return a Request with the selected item or None
        """
        result = None
        # get all interfaces of the object
        for interface_name in dir(o.I):
            interface = getattr(o.I,interface_name)
            # keep only those that inherit OGF::Commands
            if interface.meta_class.is_a(OGF.Commands):
                if imgui.BeginMenu(interface_name):
                    thisresult = AutoGUI.draw_interface_menuitems(interface)
                    if thisresult != None:
                        result = thisresult
                    imgui.EndMenu()
        return result
                    
    def draw_interface_menuitems(interface : OGF.Interface) -> OGF.Request:
        """ 
        @brief Draws menu items for all slots of an interface 
        @param[in] interface the interface, for instance, meshgrob.I.Shapes
        @return a Request with the selected item or None
        """
        result = None
        mclass = interface.meta_class
        for i in range(mclass.nb_slots()):
            mslot = mclass.ith_slot(i)
            if not hasattr(OGF.Interface,mslot.name):
                thisresult = AutoGUI.draw_request_menuitem(getattr(interface,mslot.name))
                if thisresult != None:
                    result = thisresult
        return result
                    
    def draw_request_menuitem(request : OGF.Request) -> OGF.Request:
        """ 
        @brief Draws a menu item for a given Request (that is, a closure) 
        @param[in] request the Request
        @return the request if it was selected or None
        """
        result = None
        if imgui.MenuItem(request.method().name.replace('_',' ')):
            result = request
        if (
                imgui.IsItemHovered() and
                request.method().has_custom_attribute('help')
        ):
            imgui.SetTooltip(request.method().custom_attribute_value('help'))
        return result

    #========================================================================
            
    def ith_arg_is_advanced(
            mmethod: OGF.MetaMethod, i: int
    ) -> bool:
        """ 
        @brief Tests whether an argument of a method is declared as advanced 
        @details Advanced arguments appear in a pulldown, hidden by default
           part of the dialog. They are all the arguments after the @advanced
           tag in the function documentation.
        @param[in] mmethod a meta-method
        @param[in] i the index of the argument
        @retval True of the i-th argument of mmethod is advanced
        @retval False otherwise
        """
        if not mmethod.ith_arg_has_custom_attribute(i,'advanced'):
           return False
        return (mmethod.ith_arg_custom_attribute_value(i,'advanced') == 'true')
    
    #========= GUI handlers for command args and properties ==============

    def slot_arg_handler(
            args: ArgList, mslot: OGF.MetaSlot, i: int
    ):
        """
        @brief Handles the GUI for a slot argument
        @param[in] args an ArgList
        @param[in] mslot the metaslot
        @param[in] i the index of the argument
        """
        tooltip = ''
        if mslot.ith_arg_has_custom_attribute(i,'help'):
            tooltip = mslot.ith_arg_custom_attribute_value(i,'help')
        handler = AutoGUI.arg_handler
        #if mslot.ith_arg_has_custom_attribute(i,'handler'):
        #    handler_name = mslot.ith_arg_custom_attribute_value(i,'handler')
        #    if not handler_name.endswith('_handler'):
        #        handler_name = handler_name + '_handler'
        #    handler = getattr(AutoGUI,handler_name)
        handler(
            args, mslot.ith_arg_name(i), mslot.ith_arg_type(i), tooltip
        )
    
    def arg_handler(
            o: object, property_name: str,
            mtype: OGF.MetaType, tooltip
    ):
        """ 
        @brief Handles the GUI for a property in an object
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] mtype the meta-type of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
        if tooltip == None:
            tooltip = ''
        # special case: property is an enum
        if mtype.meta_class.is_a(OGF.MetaEnum):
            AutoGUI.enum_handler(o, property_name, mtype, tooltip)
            return
        # general case: do we have a specialized handler ? 
        handler_name = mtype.name.replace(' ','_').replace(':','_') + '_handler'
        if hasattr(AutoGUI, handler_name):
            getattr(AutoGUI, handler_name)(o,property_name, mtype, tooltip)
            return
        # fallback: use a textbox to edit the property as a string
        AutoGUI.string_handler(o, property_name, mtype, tooltip)
        
    def string_handler(
            o: object, property_name: str,
            mtype: OGF.MetaType, tooltip: str
    ):
        """ 
        @brief Handles the GUI for a string property in an object, with a textbox
        @details This is also the default fallback handler
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
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
        """ 
        @brief Handles the GUI for a bool property in an object, with a checkbox
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
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
        """ 
        @brief Handles the GUI for an int property in an object
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
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
        """ 
        @brief Handles the GUI for an unsigned int property in an object
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
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

    def float_handler(
            o: object, property_name: str,
            mtype: OGF.MetaType, tooltip: str
    ):
        """ 
        @brief Handles the GUI for an unsigned int property in an object
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
        AutoGUI.label(property_name, tooltip)
        imgui.SameLine()
        imgui.PushItemWidth(-20)
        val = getattr(o, property_name)
        _,val = imgui.InputFloat(
            '##properties##' + property_name, val
        )
        imgui.PopItemWidth()
        setattr(o,property_name,val)
        
    def OGF__GrobName_handler(
            o: object, property_name: str,
            mtype: OGF.GrobName, tooltip: str
    ):
        """ 
        @brief Handles the GUI for a GrobName property in an object
        @details Displays a pulldown with names of Grobs in SceneGraph
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
        values = gom.get_environment_value('grob_instances')
        AutoGUI.combo_box_handler(o, property_name, values, tooltip)
        
    def OGF__MeshGrobName_handler(
            o: object, property_name: str,
            mtype: OGF.MeshGrobName, tooltip: str
    ):
        """ 
        @brief Handles the GUI for a MeshGrobName property in an object
        @details Displays a pulldown with names of MeshGrobs in SceneGraph
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
        values = gom.get_environment_value('OGF::MeshGrob_instances')
        AutoGUI.combo_box_handler(o, property_name, values, tooltip)

    def OGF__VoxelGrobName_handler(
            o: object, property_name: str,
            mtype: OGF.VoxelGrobName, tooltip: str
    ):
        """ 
        @brief Handles the GUI for a VoxelGrobName property in an object
        @details Displays a pulldown with names of VoxelGrobs in SceneGraph
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
        values = gom.get_environment_value('OGF::VoxelGrob_instances')
        AutoGUI.combo_box_handler(o, property_name, values, tooltip)
        
    def OGF__GrobClassName_handler(
            o: object, property_name: str,
            mtype: OGF.GrobClassName, tooltip: str
    ):
        """ 
        @brief Handles the GUI for a GrobClassName property in an object
        @details Displays a pulldown with all possible class names for a Grob
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] an optional tooltip to be displayed
        """
        values = gom.get_environment_value('grob_types')
        AutoGUI.combo_box_handler(o, property_name, values, tooltip)

    def enum_handler(
            o: object, property_name: str,
            menum: OGF.MetaEnum, tooltip: str
    ):
        """ 
        @brief Handles the GUI for an enum property in an object
        @details Displays a pulldown with all possible class names for the enum
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] menum the meta-type of the enum
        @param[in] an optional tooltip to be displayed
        """
        values = ''
        for i in range(menum.nb_values()):
            if i != 0:
                values = values + ';'
            values = values + menum.ith_name(i)
        AutoGUI.combo_box_handler(o, property_name, values, tooltip)

    def combo_box_handler(
            o: object, property_name: str,
            values: str, tooltip: str
    ):
        """ 
        @brief Handles the GUI for a property in an object, using a combobox
        @param[in,out] o the object 
        @param[in] property_name the name of the property to be edited
        @param[in] values a ';'-separated string with all enum values
        @param[in] an optional tooltip to be displayed
        """
        AutoGUI.label(property_name, tooltip)
        imgui.SameLine()
        imgui.PushItemWidth(-20)
        old_value = getattr(o,property_name)
        _,new_value = AutoGUI.combo_box(
            '##properties##'+property_name, values, old_value
        )
        imgui.PopItemWidth()
        setattr(o,property_name,new_value)

    def combo_box(label: str, values: str, old_value: str) -> tuple:
        """
        @brief Draws and handles the GUI for a combo-box
        @param[in] label the ImGui label of te combo-box
        @param[in] values a ';'-separated string with all values
        @param[in] old_value the previous value of the combo-box
        @return selected flag and new value of the combo-box
        """
        if values=='':
            return false,-1
        if values[0] == ';':
            values = values[1:]
        values = values.split(';')

        found = True
        try:
            old_index = values.index(old_value)
        except:
            found = False
            old_index = 0
        sel,new_index = imgui.Combo(label, old_index, values)
        return sel,values[new_index]
        
    def label(property_name: str, tooltip: str):
        """ 
        @brief Draws the label of a property
        @param[in] property_name the name of the property, the underscores are
          replaced with spaces when displayed
        @param[in] tooltip an optional tooltip to be displayed when the user
          hovers the label with the mouse pointer, or ''
        """
        imgui.Text(property_name.replace('_',' '))
        if tooltip != '' and imgui.IsItemHovered():
            imgui.SetTooltip(tooltip)

#=========================================================================

class PyAutoGUI:
    """ 
    @brief Python-AutoGUI interop 
    @details Functions to inject Python classes and types into the Graphite
      object model so that they are visible from the GUI and scripting as if
      they have always been there in C++.
    """

    def register_enum(name: str, values: list):
        """
        @brief Declares a new enum type in the Graphite object model
        @param[in] str the name of the enum, for instance, 'OGF::MyEnumType'. 
           Then it is accessible using OGF.MyEnumType
        @param[in] values a list with all the symbolic names of the enum values
        @return the created meta-type for the enum
        """
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
        """
        @brief Declares a new commands class in the Graphite object model
        @param[in] scene_graph the SceneGraph
        @param[in] grobclass the Grob meta-class to which the new commands
          will be associated. Its name should be something like 
          MeshGrobXXXCommands or VoxelGrobYYYCommands
        @param[in] methodsclass the Python class with the commands. Each command
          takes as an argument an interface, the name of the method, then the
          method arguments. It needs to have type hints in order to generate
          the right GUI elements for the arguments. It can have a docstring
          in the doxygen format to generate the tooltips. See the end of this
          file for an example.
        """
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
        """
        @brief adds a new command in a meta-class, implemented by a Python
          function. Used internally by register_commands()
        @param[in] mclass the meta-class, previously created by calling
          create_subclass() in an existing GOM meta-class
        @param[in] pyfunc a Python function or callable. It takes as an 
          argument an interface, the name of the method, then the
          method arguments. It needs to have type hints in order to generate
          the right GUI elements for the arguments. It can have a docstring
          in the doxygen format to generate the tooltips. See the end of this
          file for an example.
        """
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
        """ 
        @brief parses the docstring of a python function or callable 
            and uses it to document a GOM MetaSlot , used internally by
            register_command()
        @param[in] mslot the meta-slot
        @param[in] pyfunc the Python function or callable
        """
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

#===============================================================================
            
