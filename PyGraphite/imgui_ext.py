import polyscope.imgui as imgui
import os


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
        self.scaling = 1.0
        self.footer_size = 35 * self.scaling

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
        None

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
        self.path = os.path.join(self.path, path)
        self.update_files()

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
        return (self.show_hidden or not f.startswith('.'))

    def show_directory(self, d : str) -> bool:
        return (self.show_hidden or not d.startswith('.'))


class imgui_ext:
    """
    @brief Functions to extend Dear Imgui
    """
