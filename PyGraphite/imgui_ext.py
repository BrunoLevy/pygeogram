import polyscope.imgui as imgui
import os,string


class FileDialog:
    """ A simple file dialog using imgui and os """
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
        self.current_file = None
        self.scaling = 1.0     # scaling factor for GUI (depends on font size)
        self.footer_size = 35.0 * self.scaling
        self.pinned = False

    def draw(self):
        if not self.visible:
            return

        label = ('Save as...##' if self.save_mode else 'Load...##')
        label = label + str(hash(self))

        imgui.SetNextWindowPos([700,10],imgui.ImGuiCond_Once)
        imgui.SetNextWindowSize([400,415],imgui.ImGuiCond_Once)
        _,self.visible = imgui.Begin(label, self.visible)
        self.draw_header()
        imgui.Separator()
        self.draw_files_and_directories()
        self.draw_footer()
        imgui.End()

    def draw_header(self):
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
            if imgui.Button('O' if self.pinned else '(-'):
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
            if imgui_ext.SimpleButton( d + '##path' + str(i)):
                new_path = os.sep.join(path[0:i+1])
                if len(path[0]) < 2 or path[0][1] != ':':
                    new_path = os.sep + new_path
                self.set_path(new_path)
            imgui.SameLine()
            imgui.Text(os.sep)
            imgui.SameLine()

    def draw_disk_drives(self):
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
            _,sel = imgui.Selectable(f, self.current_file == f)
            if sel:
                self.current_file = f
        imgui.EndChild()

    def draw_footer(self):
        None

    def show(self):
        self.update_files()
        self.visible = True

    def set_path(self, path : str):
        self.path = os.path.normpath(os.path.join(self.path, path))
        self.update_files()

    def set_extensions(self, extensions : list):
        self.extensions = extensions

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
        if not self.show_hidden and f.startswith('.'):
            return False
        if len(self.extensions) == 0:
            return True
        _,ext = os.path.splitext(f)
        ext = ext.removeprefix('.')
        return ext.lower() in self.extensions

    def show_directory(self, d : str) -> bool:
        return (self.show_hidden or not d.startswith('.'))


class imgui_ext:
    """
    @brief Functions to extend Dear Imgui
    """

    def SimpleButton(label: str) -> bool:
        txt = label
        off = label.find('##')
        if off != -1:
            txt = txt[0:off]
        label_size = imgui.CalcTextSize(txt, None, True)
        _,sel=imgui.Selectable(label, False, 0, label_size)
        return sel
