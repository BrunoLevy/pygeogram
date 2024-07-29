import polyscope.imgui as imgui
import os,string


class FileDialogImpl:
    """
    @brief   Internal implementation of file dialog
    @details Do not use directly, use API functions instead
             imgui_ext.OpenFileDialog() and imgui_ext.FileDialog()
    """
    def __init__(
            self,
            save_mode: bool = False,
            default_filename: str = ''
    ):
        self.visible = False
        self.save_mode = save_mode
        self.path = os.getcwd()
        self.directories = []
        self.files = []
        self.extensions = []
        self.show_hidden = False
        self.current_file = default_filename
        self.selected_file = ''
        self.scaling = 1.0 # scaling factor for GUI (depends on font size)
        self.footer_size = 35.0 * self.scaling
        self.pinned = False
        self.are_you_sure = False

    def draw(self):
        """ @brief Draws and handles the GUI """
        if not self.visible:
            return

        label = ('Save as...##' if self.save_mode else 'Load...##')
        label = label + str(hash(self)) # make sure label is unique

        imgui.SetNextWindowPos([700,10],imgui.ImGuiCond_Once)
        imgui.SetNextWindowSize([400,415],imgui.ImGuiCond_Once)
        _,self.visible = imgui.Begin(label, self.visible)
        self.draw_header()
        imgui.Separator()
        self.draw_files_and_directories()
        self.draw_footer()
        imgui.End()
        self.draw_are_you_sure()

    def draw_header(self):
        """
           @brief Draws the top part of the window, with
              the Parent/Home/Refresh/pin buttons and the
              clickable current path
        """
        if imgui.Button('Parent'):
            self.set_path('..')
        imgui.SameLine()
        if imgui.Button('Home'):
            self.set_path(os.path.expanduser('~'))
        imgui.SameLine()
        if imgui.Button('Refresh'):
            self.update_files()
        s = imgui.CalcTextSize('(-')
        imgui.SameLine()
        w = imgui.GetContentRegionAvail()[0] - s[0]*2.5
        imgui.Dummy([w, 1.0])
        imgui.SameLine()
        if not self.save_mode:
            if SimpleButton('O' if self.pinned else '(-'):
                self.pinned = not self.pinned
            if imgui.IsItemHovered():
                imgui.SetTooltip('pin dialog')
        self.draw_disk_drives()
        imgui.Separator()
        path = self.path.split(os.sep)
        for i,d in enumerate(self.path.split(os.sep)):
            if d == '':
                continue
            if (imgui.GetContentRegionAvail()[0] <
                imgui.CalcTextSize(d)[0] + 10.0 * self.scaling):
                imgui.NewLine()
            if SimpleButton( d + '##path' + str(i)):
                new_path = os.sep.join(path[0:i+1])
                if len(path[0]) < 2 or path[0][1] != ':':
                    new_path = os.sep + new_path
                self.set_path(new_path)
            imgui.SameLine()
            imgui.Text(os.sep)
            imgui.SameLine()

    def draw_disk_drives(self):
        """ @brief Draws buttons to select disk drives under Windows """
        if os.name != 'nt':
            return
        for drive in string.ascii_uppercase:
            if os.path.exists(os.path.join(drive, 'File.ID')):
                if imgui.Button(drive + ':'):
                    self.set_path(drive + ':')
                imgui.SameLine()
                if (imgui.GetContentRegionAvail()[0] <
                    imgui.CalcTextSize('X:')[0] + 10.0 * self.scaling):
                    imgui.NewLine()
        imgui.Text('')

    def draw_files_and_directories(self):
        """ @brief Draws two panels with the list of files and directories """
        panelsize = [
            imgui.GetWindowWidth()*0.5-10.0*self.scaling,
            -self.footer_size
        ]
        imgui.BeginChild('##directories', panelsize, True)
        for d in sorted(self.directories):
            _,sel = imgui.Selectable(d)
            if sel:
                self.set_path(d)
                break
        imgui.EndChild()
        imgui.SameLine()
        imgui.BeginChild('##files', panelsize, True)
        for f in sorted(self.files):
            sel,_ = imgui.Selectable(
                f, self.current_file == f,
                imgui.ImGuiSelectableFlags_AllowDoubleClick
            )
            if sel:
                self.current_file = f
                if imgui.IsMouseDoubleClicked(0):
                    self.file_selected()
        imgui.EndChild()

    def draw_footer(self):
        """ @brief draws footer with save/load btn and filename text entry """
        save_btn_label = 'Save' if self.save_mode else 'Load'
        save_btn_label = save_btn_label + '##' + str(hash(self))
        if imgui.Button(save_btn_label):
            self.file_selected()
        imgui.SameLine()
        imgui.PushItemWidth(
            -80.0*self.scaling if self.save_mode else -5.0 * self.scaling
        )
        sel,self.current_file = imgui.InputText(
            '##filename##' + str(hash(self)),
            self.current_file,
            imgui.ImGuiInputTextFlags_EnterReturnsTrue
        )
        if sel:
            self.file_selected()
        imgui.PopItemWidth()
        # Keep auto focus on the input box
        if imgui.IsItemHovered():
            # Auto focus previous widget
            imgui.SetKeyboardFocusHere(-1)

    def draw_are_you_sure(self):
        """ @brief draws a modal popup if file to save already exists """
        if self.are_you_sure:
            imgui.OpenPopup('File exists')
        if imgui.BeginPopupModal(
            "File exists", True, imgui.ImGuiWindowFlags_AlwaysAutoResize
        ):
            imgui.Text(
                'File ' + self.current_file +
                ' already exists\nDo you want to overwrite it ?'
            )
            imgui.Separator()
            if imgui.Button(
                'Overwrite',
                [-imgui.GetContentRegionAvail()[0]/2.0, 0.0]
            ):
                self.are_you_sure = False
                imgui.CloseCurrentPopup()
                self.file_selected(True)
            imgui.SameLine()
            if imgui.Button('Cancel', [-1.0, 0.0]):
                self.are_you_sure = False
                imgui.CloseCurrentPopup();
            imgui.EndPopup()

    def show(self):
        self.update_files()
        self.visible = True

    def hide(self):
        self.visible = False

    def set_path(self, path : str):
        self.path = os.path.normpath(os.path.join(self.path, path))
        self.update_files()

    def set_default_filename(self, filename : str):
        self.current_file = filename

    def get_and_reset_selected_file(self):
        """
          @brief Gets the selected file if any and resets it to the empty string
          @return the selected file if there is any or empty string otherwise.
        """
        result = self.selected_file
        self.selected_file = ''
        return result

    def set_extensions(self, extensions : list):
        """
         @brief Defines the file extensions managed by this FileDialogImpl.
         @param[in] extensions a list of extensions, without the dot '.'.
        """
        self.extensions = extensions

    def set_save_mode(self,save_mode : bool):
        """
          @brief Sets whether this file dialog is for
           saving file.
          @details If this file dialog is for saving file,
           then the user can enter the name of a non-existing
           file, else he can only select existing files.
          @param[in] x True if this file dialog is for
           saving files.
        """
        self.save_mode = save_mode

    def file_selected(self, overwrite=False):
        """ Called whenever a file is selected """
        path_file = os.path.join(self.path, self.current_file)
        if self.save_mode:
            if not overwrite and os.path.isfile(path_file):
                self.are_you_sure = True
                return
            else:
                self.selected_file = path_file
        else:
            self.selected_file = path_file
        if not self.pinned:
            self.hide()

    def update_files(self):
        self.files = []
        self.directories = ['..']
        for f in os.listdir(self.path):
            path_f = os.path.join(self.path, f)
            if os.path.isfile(path_f):
                if self.show_file(f):
                    self.files.append(f)
            elif os.path.isdir(path_f):
                if self.show_directory(f):
                    self.directories.append(f)

    def show_file(self, f : str) -> bool:
        """ Tests whether a give file should be shown in the dialog """
        if not self.show_hidden and f.startswith('.'):
            return False
        if len(self.extensions) == 0:
            return True
        _,ext = os.path.splitext(f)
        ext = ext.removeprefix('.')
        return ext.lower() in self.extensions

    def show_directory(self, d : str) -> bool:
        """ Tests whether a give directory should be shown in the dialog """
        return (self.show_hidden or not d.startswith('.'))


file_dialogs = dict()
ImGuiExtFileDialogFlags_Load = 1
ImGuiExtFileDialogFlags_Save = 2

def OpenFileDialog(
        label      : str,
        extensions : list,
        filename   : str,
        flags      : int
):
    """
    @brief Create or opens a file dialog
    @details One needs to call @see FileDialog() to display it afterwards
    @param[in] label a unique label associated with the dialog
    @param[in] extensions the list of valid file extensions, without '.'
    @param[in] filename default filename used for Save dialogs, or ''
    @param[in] flags one of ImGuiExtFileDialogFlags_Load,
                            ImGuiExtFileDialogFlags_Save
    """
    if label in file_dialogs:
        dlg = file_dialogs[label]
    else:
        dlg = FileDialogImpl()
        file_dialogs[label] = dlg
    dlg.set_extensions(extensions)
    if flags == ImGuiExtFileDialogFlags_Save:
        dlg.set_save_mode(True)
        dlg.set_default_filename(filename)
    else:
        dlg.set_save_mode(False)
    dlg.show()

def FileDialog(label : str) -> (str, bool):
    """
    @brief Draws and handles a file dialog
    @param[in] label the unique label associated with the dialog. If
               OpenFileDialog() was called before in the same frame,
               it will be displayed and handled, else it is ignored.
    @retval (selected filename,True) if a file was selected
    @retval ('', False) otherwise
    """
    if not label in file_dialogs:
        return ('',False)
    dlg = file_dialogs[label]
    dlg.draw()
    result = dlg.get_and_reset_selected_file()
    return result, (result != '')

def SimpleButton(label: str) -> bool:
    """
    @brief Draws a button without any frame
    @param[in] label the text drawn of the button, what follows '##' is not
               displayed and used to have a unique ID
    @retval True if the button was pushed
    @retval False otherwise
    """
    txt = label
    off = label.find('##')
    if off != -1:
        txt = txt[0:off]
    label_size = imgui.CalcTextSize(txt, None, True)
    _,sel=imgui.Selectable(label, False, 0, label_size)
    return sel
