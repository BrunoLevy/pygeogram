from rlcompleter import Completer
import polyscope as ps, polyscope.imgui as imgui
import sys
import gompy

gom = gompy.interpreter()

#=========================================================================

class GraphiteStream:
    def __init__(self, func):
        self.func = func
    def write(self, string):
        if string != '\n':
            self.func(string)
    def flush(self):
        return

#=========================================================================

def longestCommonPrefix(a):
    size = len(a)
    if (size == 0):
        return ''

    if (size == 1):
        return a[0]

    a.sort()
    end = min(len(a[0]), len(a[size - 1]))
    i = 0
    while (i < end and
           a[0][i] == a[size - 1][i]):
        i += 1

    pre = a[0][0: i]
    return pre

#=========================================================================

class Terminal:

    def __init__(self, app):
        self.visible = True
        self.command = ''
        self.queued_execute_command = False
        self.command_widget_id = 0
        self.completer = Completer()
        self.message = ''
        self.update_frames = 0
        self.focus = False
        self.app = app
        self.debug_mode = self.app.debug_mode
        application = self.app.scene_graph.application
        gom.connect(application.out, self.out_CB)
        gom.connect(application.err, self.err_CB)
        sys.stdout = GraphiteStream(gom.out)
        sys.stderr = GraphiteStream(gom.err)
        sys.displayhook = gom.out

    def draw(self):
        if not self.visible:
            return
        imgui.SetNextWindowPos(
            [660,ps.get_window_size()[1]-260],imgui.ImGuiCond_Once
        )
        imgui.SetNextWindowSize([600,200],imgui.ImGuiCond_Once)
        _,self.visible = imgui.Begin('Terminal', self.visible)
        imgui.BeginChild('scrolling',[0.0,-25.0])
        imgui.Text(self.message)
        if self.update_frames > 0:
            imgui.SetScrollY(imgui.GetScrollMaxY())
            self.update_frames = self.update_frames - 1
        imgui.EndChild()
        imgui.Text('>')
        imgui.SameLine()
        imgui.PushItemWidth(-1)
        if self.focus:
            imgui.SetKeyboardFocusHere(0)
            self.focus = False
        sel,self.command = imgui.InputText(
            '##terminal##command##' + str(self.command_widget_id),
            self.command,
            imgui.ImGuiInputTextFlags_EnterReturnsTrue
        )
        if imgui.IsItemActive():
            if imgui.IsKeyPressed(imgui.ImGuiKey_Tab):
                self.shell_completion()
            if imgui.IsKeyPressed(imgui.ImGuiKey_UpArrow):
                self.shell_history_up()
            if imgui.IsKeyPressed(imgui.ImGuiKey_DownArrow):
                self.shell_history_down()
        if sel:
            self.queued_execute_command = True
        imgui.PopItemWidth()
        imgui.End()

    def print(self, msg: str):
        """
        @brief Prints a message to the terminal window in Graphite
        @details Triggers graphics update for 3 frames, for leaving the
          slider enough time to reach the last line in the terminal
        @param[in] msg the message to be printed
        """
        if(self.debug_mode): # see comment in constructor
            print(msg)
            self.update_frames = 0
        else:
            self.message = self.message + msg
            self.update_frames = 3 # needs three frames for SetScrollY()
                                   # to do the job

    def handle_queued_command(self):
        if self.queued_execute_command:
            try:
                exec(
                    self.command,
                    {'graphite' : self.app, 'imgui' : imgui}
                )
            except Exception as e:
                self.print('Error: ' + str(e) + '\n')
            self.queued_execute_command = False
            self.command = ''
            self.focus = True

    #==============================================================

    def shell_completion(self):
        """
        @brief autocompletion
        @details called whenever TAB is pressed
        """
        completions = [ ]
        i = 0
        while True:
            cmp = self.completer.complete(self.command,i)
            if cmp == None:
                break
            completions.append(cmp)
            i = i + 1
        if(len(completions) > 0):
            if(len(completions) > 1):
                self.print('\n')
                for i,comp in enumerate(completions):
                    self.print('['+str(i)+'] ' + comp + '\n')
            self.command = longestCommonPrefix(completions)
            self.command_widget_id += 1
            self.focus = True

    def shell_history_up(self):
        """
        @brief previous command in history
        @details called whenever UP key is pressed
        """
        None

    def shell_history_down(self):
        """
        @brief next command in history
        @details called whenever DOWN key is pressed
        """
        None

    #==============================================================

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
        while self.app.running and self.update_frames > 0:
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
        self.visible=True # make terminal appear if it was hidden
        self.print(msg)
        while self.app.running and self.update_frames > 0:
            ps.frame_tick()
