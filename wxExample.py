  
#!/usr/bin/env python
#
# A simple terminal application with wxPython.
#
# (C) 2001-2015 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause

import codecs
import serial
import threading
import wx
import wxSerialConfigDialog

# ----------------------------------------------------------------------
# Create an own event type, so that GUI updates can be delegated
# this is required as on some platforms only the main thread can
# access the GUI without crashing. wxMutexGuiEnter/wxMutexGuiLeave
# could be used too, but an event is more elegant.

import pyte
# import vt102

from myServer import Server

serversocket = None

SERIALRX = wx.NewEventType()
# bind to serial data receive events
EVT_SERIALRX = wx.PyEventBinder(SERIALRX, 0)


class SerialRxEvent(wx.PyCommandEvent):
    eventType = SERIALRX

    def __init__(self, windowID, data):
        wx.PyCommandEvent.__init__(self, self.eventType, windowID)
        self.data = data

    def Clone(self):
        # self.__class__(self.GetId(), self.data)
        return self.__class__(self.GetId(), self.data)

# ----------------------------------------------------------------------

ID_CLEAR = wx.NewId()
ID_SAVEAS = wx.NewId()
ID_SESSIONLOG = wx.NewId()
ID_SETTINGS = wx.NewId()
ID_TERM = wx.NewId()
ID_EXIT = wx.NewId()
ID_RTS = wx.NewId()
ID_DTR = wx.NewId()
# ext
ID_X1 = wx.NewId()
ID_X1SETTING = wx.NewId()

NEWLINE_CR = 0
NEWLINE_LF = 1
NEWLINE_CRLF = 2

class TerminalSetup:
    """
    Placeholder for various terminal settings. Used to pass the
    options to the TerminalSettingsDialog.
    """
    def __init__(self):
        self.echo = False
        self.unprintable = False
        self.newline = NEWLINE_CRLF


class TerminalSettingsDialog(wx.Dialog):
    """Simple dialog with common terminal settings like echo, newline mode."""

    def __init__(self, *args, **kwds):
        self.settings = kwds['settings']
        del kwds['settings']
        # begin wxGlade: TerminalSettingsDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.checkbox_echo = wx.CheckBox(self, -1, "Local Echo")
        self.checkbox_unprintable = wx.CheckBox(self, -1, "Show unprintable characters")
        self.radio_box_newline = wx.RadioBox(self, -1, "Newline Handling", choices=["CR only", "LF only", "CR+LF"], majorDimension=0, style=wx.RA_SPECIFY_ROWS)
        self.sizer_4_staticbox = wx.StaticBox(self, -1, "Input/Output")
        self.button_ok = wx.Button(self, wx.ID_OK, "")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.__attach_events()
        self.checkbox_echo.SetValue(self.settings.echo)
        self.checkbox_unprintable.SetValue(self.settings.unprintable)
        self.radio_box_newline.SetSelection(self.settings.newline)


    def __set_properties(self):
        # begin wxGlade: TerminalSettingsDialog.__set_properties
        self.SetTitle("Terminal Settings")
        self.radio_box_newline.SetSelection(0)
        self.button_ok.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: TerminalSettingsDialog.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_4_staticbox.Lower()
        sizer_4 = wx.StaticBoxSizer(self.sizer_4_staticbox, wx.VERTICAL)
        sizer_4.Add(self.checkbox_echo, 0, wx.ALL, 4)
        sizer_4.Add(self.checkbox_unprintable, 0, wx.ALL, 4)
        sizer_4.Add(self.radio_box_newline, 0, 0, 0)
        sizer_2.Add(sizer_4, 0, wx.EXPAND, 0)
        sizer_3.Add(self.button_ok, 0, 0, 0)
        sizer_3.Add(self.button_cancel, 0, 0, 0)
        sizer_2.Add(sizer_3, 0, wx.ALL | wx.ALIGN_RIGHT, 4)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        self.Layout()
        # end wxGlade

    def __attach_events(self):
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.button_ok.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=self.button_cancel.GetId())

    def OnOK(self, events):
        """Update data wil new values and close dialog."""
        self.settings.echo = self.checkbox_echo.GetValue()
        self.settings.unprintable = self.checkbox_unprintable.GetValue()
        self.settings.newline = self.radio_box_newline.GetSelection()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, events):
        """Do not update data but close dialog."""
        self.EndModal(wx.ID_CANCEL)

# end of class TerminalSettingsDialog


class TerminalFrame(wx.Frame):
    """Simple terminal program for wxPython"""

    def __init__(self, *args, **kwds):
        self.serial = serial.Serial()
        self.serial.timeout = 0.5   # make sure that the alive event can be checked from time to time
        self.settings = TerminalSetup()  # placeholder for the settings
        self.thread = None
        self.alive = threading.Event()
        self.recordFlag = False
        # begin wxGlade: TerminalFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # Menu Bar
        self.frame_terminal_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(ID_CLEAR, "&Clear", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.Append(ID_SESSIONLOG, "&Record Text To...", "", wx.ITEM_CHECK)
        wxglade_tmp_menu.Append(ID_SAVEAS, "&Save Text As...", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.AppendSeparator()
        wxglade_tmp_menu.Append(ID_TERM, "&Terminal Settings...", "", wx.ITEM_NORMAL)
        wxglade_tmp_menu.AppendSeparator()
        wxglade_tmp_menu.Append(ID_EXIT, "&Exit", "", wx.ITEM_NORMAL)
        self.frame_terminal_menubar.Append(wxglade_tmp_menu, "&File")
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(ID_RTS, "RTS", "", wx.ITEM_CHECK)
        wxglade_tmp_menu.Append(ID_DTR, "&DTR", "", wx.ITEM_CHECK)
        wxglade_tmp_menu.Append(ID_SETTINGS, "&Port Settings...", "", wx.ITEM_NORMAL)
        self.frame_terminal_menubar.Append(wxglade_tmp_menu, "Serial Port")
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(ID_X1, "&Check GS_Process", "", wx.ITEM_CHECK)
        wxglade_tmp_menu.Append(ID_X1SETTING, "&GS_Process Setting", "", wx.ITEM_NORMAL)
        self.frame_terminal_menubar.Append(wxglade_tmp_menu, "Test Function")
        self.SetMenuBar(self.frame_terminal_menubar)
        # Menu Bar end
        self.text_ctrl_output = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE | wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_MENU, self.OnClear, id=ID_CLEAR)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, id=ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnRecordOn, id=ID_SESSIONLOG)
        self.Bind(wx.EVT_MENU, self.OnTermSettings, id=ID_TERM)
        self.Bind(wx.EVT_MENU, self.OnExit, id=ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnRTS, id=ID_RTS)
        self.Bind(wx.EVT_MENU, self.OnDTR, id=ID_DTR)
        self.Bind(wx.EVT_MENU, self.OnPortSettings, id=ID_SETTINGS)
        # 
        self.Bind(wx.EVT_MENU, self.OnX1FuncEnable, id=ID_X1)
        self.Bind(wx.EVT_MENU, self.OnExtSetting, id=ID_X1SETTING)
        #
        self.seekTermKeyword = False
        # end wxGlade
        self.__attach_events()          # register events
        self.OnPortSettings(None)       # call setup dialog on startup, opens port
        if not self.alive.isSet():
            self.Close()

        # seek string
        self.temp_string = ""
        self.clean_flag = False
        self.find_flag = False
        self.server = Server(7777)
        self.recordname = "" # save as 

    def StartThread(self):
        """Start the receiver thread"""
        self.thread = threading.Thread(target=self.ComPortThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        self.serial.rts = True
        self.serial.dtr = True
        self.frame_terminal_menubar.Check(ID_RTS, self.serial.rts)
        self.frame_terminal_menubar.Check(ID_DTR, self.serial.dtr)

    def StopThread(self):
        """Stop the receiver thread, wait until it's finished."""
        if self.thread is not None:
            self.alive.clear()          # clear alive event for thread
            self.thread.join()          # wait until thread has finished
            self.thread = None

    def __set_properties(self):
        # begin wxGlade: TerminalFrame.__set_properties
        self.SetTitle("Serial Terminal")
        self.SetSize((546, 383))
        self.text_ctrl_output.SetFont(wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, ""))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: TerminalFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.text_ctrl_output, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def __attach_events(self):
        # register events at the controls
        self.Bind(wx.EVT_MENU, self.OnClear, id=ID_CLEAR)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, id=ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnExit, id=ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnPortSettings, id=ID_SETTINGS)
        self.Bind(wx.EVT_MENU, self.OnTermSettings, id=ID_TERM)
        self.text_ctrl_output.Bind(wx.EVT_CHAR, self.OnKey)
        self.Bind(EVT_SERIALRX, self.OnSerialRead)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnExit(self, event):  # wxGlade: TerminalFrame.<event_handler>
        """Menu point Exit"""
        self.Close()

    def OnClose(self, event):
        """Called on application shutdown."""
        self.StopThread()               # stop reader thread
        self.serial.close()             # cleanup
        self.Destroy()                  # close windows, exit app

    def OnSaveAs(self, event):  # wxGlade: TerminalFrame.<event_handler>
        """Save contents of output window."""
        with wx.FileDialog(
                None,
                "Save Text As...",
                ".",
                "",
                "Text File|*.txt|All Files|*",
                wx.FD_SAVE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                with codecs.open(filename, 'w', encoding='utf-8') as f:
                    text = self.text_ctrl_output.GetValue()
                    screen_len = text.count( "\n", 0, len(text) )
                    # stream = vt102.stream()
                    # screen = vt102.screen((screen_len + 2, 80))
                    # screen.attach(stream)
                    # stream.process(self.text_ctrl_output.GetValue())
                    # todo: get window size
                    wxwinsize = wx.Frame.GetSize(self)
                    screen = pyte.Screen(int(wxwinsize[0]/2), int(wxwinsize[1]/2))
                    stream = pyte.Stream(screen)
                    stream.feed(text)
                    self.writeScreenToFile(f, screen.display)

    def writeScreenToFile(self, fp, srceen_list):
        """Using VT102 Clean the vt100 Format"""
        if fp != None and len(srceen_list) > 0:
            for idx, line in enumerate(srceen_list, 0):
                fp.writelines(line.strip())
        # Remember to close pointer

    def OnClear(self, event):  # wxGlade: TerminalFrame.<event_handler>
        """Clear contents of output window."""
        self.text_ctrl_output.Clear()

    def OnPortSettings(self, event):  # wxGlade: TerminalFrame.<event_handler>
        """
        Show the port settings dialog. The reader thread is stopped for the
        settings change.
        """
        if event is not None:           # will be none when called on startup
            self.StopThread()
            self.serial.close()
        ok = False
        while not ok:
            with wxSerialConfigDialog.SerialConfigDialog(
                    self,
                    -1,
                    "",
                    show=wxSerialConfigDialog.SHOW_BAUDRATE | wxSerialConfigDialog.SHOW_FORMAT | wxSerialConfigDialog.SHOW_FLOW,
                    serial=self.serial) as dialog_serial_cfg:
                dialog_serial_cfg.CenterOnParent()
                result = dialog_serial_cfg.ShowModal()
            # open port if not called on startup, open it on startup and OK too
            if result == wx.ID_OK or event is not None:
                try:
                    self.serial.open()
                except serial.SerialException as e:
                    with wx.MessageDialog(self, str(e), "Serial Port Error", wx.OK | wx.ICON_ERROR)as dlg:
                        dlg.ShowModal()
                else:
                    self.StartThread()
                    self.SetTitle("Serial Terminal on {} [{},{},{},{}{}{}]".format(
                        self.serial.portstr,
                        self.serial.baudrate,
                        self.serial.bytesize,
                        self.serial.parity,
                        self.serial.stopbits,
                        ' RTS/CTS' if self.serial.rtscts else '',
                        ' Xon/Xoff' if self.serial.xonxoff else '',
                        ))
                    ok = True
            else:
                # on startup, dialog aborted
                self.alive.clear()
                ok = True

    def OnTermSettings(self, event):  # wxGlade: TerminalFrame.<event_handler>
        """\
        Menu point Terminal Settings. Show the settings dialog
        with the current terminal settings.
        """
        with TerminalSettingsDialog(self, -1, "", settings=self.settings) as dialog:
            dialog.CenterOnParent()
            dialog.ShowModal()

    def OnExtSetting(self, event):
        with KeywordDialog(self, -1, "", settings=self.settings) as dialog:
            dialog.CenterOnParent()
            dialog.ShowModal()

    def OnKey(self, event):
        """\
        Key event handler. If the key is in the ASCII range, write it to the
        serial port. Newline handling and local echo is also done here.
        """
        code = event.GetUnicodeKey()
        if code < 256:   # XXX bug in some versions of wx returning only capital letters
            code = event.GetKeyCode()
        if code == 13:                      # is it a newline? (check for CR which is the RETURN key)
            if self.settings.echo:          # do echo if needed
                self.text_ctrl_output.AppendText('\n')
            if self.settings.newline == NEWLINE_CR:
                self.serial.write(b'\r')     # send CR
            elif self.settings.newline == NEWLINE_LF:
                self.serial.write(b'\n')     # send LF
            elif self.settings.newline == NEWLINE_CRLF:
                self.serial.write(b'\r\n')   # send CR+LF
        else:
            char = chr(code)
            if self.settings.echo:          # do echo if needed
                self.WriteMyText(char)
            self.serial.write(char.encode('UTF-8', 'replace'))         # send the character

    def WriteMyText(self, text):
        if self.settings.unprintable:
            text = ''.join([c if (c >= ' ' and c != '\x7f') else chr(0x2400 + ord(c)) for c in text])
        self.text_ctrl_output.AppendText(text)

    def WriteText(self, text):
        if self.recordFlag:
            fp = open(self.recordname, "a+")
        if self.settings.unprintable:
            text = ''.join([c if (c >= ' ' and c != '\x7f') else chr(0x2400 + ord(c)) for c in text])
        self.text_ctrl_output.AppendText(text)

        if self.recordFlag:
            fp.write(text)
        if self.seekTermKeyword:
            self.SeekEightBitSubString(text)
        if self.recordFlag:
            fp.close()

    def OnSerialRead(self, event):
        """Handle input from the serial port."""
        self.WriteText(event.data.decode('UTF-8', 'replace'))

    def ComPortThread(self):
        """\
        Thread that handles the incoming traffic. Does the basic input
        transformation (newlines) and generates an SerialRxEvent
        """
        while self.alive.isSet():
            b = self.serial.read(self.serial.in_waiting or 1)
            if b:
                # newline transformation
                if self.settings.newline == NEWLINE_CR:
                    b = b.replace(b'\r', b'\n')
                elif self.settings.newline == NEWLINE_LF:
                    pass
                elif self.settings.newline == NEWLINE_CRLF:
                    b = b.replace(b'\r\n', b'\n')
                event = SerialRxEvent(self.GetId(), b)
                self.GetEventHandler().AddPendingEvent(event)

    def OnRTS(self, event):  # wxGlade: TerminalFrame.<event_handler>
        self.serial.rts = event.IsChecked()

    def OnDTR(self, event):  # wxGlade: TerminalFrame.<event_handler>
        self.serial.dtr = event.IsChecked()

    def OnRecordOn(self, event):
        if event.IsChecked():
            self.recordFlag = True
            with wx.FileDialog(
                None,
                "Save Text As...",
                ".",
                "",
                "Text File|*.txt|All Files|*",
                wx.FD_SAVE) as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    self.recordname = dlg.GetPath()
                    
        else:
            self.recordFlag = False

    def OnX1FuncEnable(self, event):
        if event.IsChecked():
            self.seekTermKeyword = True
        else:
            self.seekTermKeyword = False

    def SeekEightBitSubString(self, newstr):
        search_list = self.ReadConfigFile()
        if newstr.find("\n") != -1:
            temp = newstr.split("\n", 1)
            self.temp_string = self.temp_string + temp[0]
            for item in search_list:
                if self.temp_string.find(item) != -1:
                    self.find_flag = True
                    break
            self.temp_string = ""
            self.temp_string = self.temp_string + temp[1]
        else:
            self.temp_string = self.temp_string + newstr

        for item in search_list:
            if self.temp_string.find(item) != -1:
                self.find_flag = True
                break

        if self.find_flag:
            print("find")
            self.lauchServer("ringing")

    def ReadConfigFile(self) -> list:
        f = None
        temp = []
        try:
            f = open('config.txt', 'r')
            for line in f.readlines():
                line = line.strip()
                temp.append(line)
        finally:
            if f:
                f.close()
            return temp

    def lauchServer(self, msg):
        self.server.announce(msg.encode("utf-8"), ("192.168.92.210", 7777))
# end of class TerminalFrame

ID_ADDKEY = wx.NewId()
class KeywordDialog(wx.Dialog):

    def __init__(self, *args, **kwds):
        self.settings = kwds['settings']
        del kwds['settings']
        # begin wxGlade: TerminalSettingsDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )
        gSizer1 = wx.GridSizer( 3, 3, 0, 0 )

        self.m_staticText1 = wx.StaticText( self, wx.ID_ANY, u"Add New Keyword", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText1.Wrap( -1 )

        gSizer1.Add( self.m_staticText1, 0, wx.ALL, 5 )

        self.m_textCtrl1 = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_textCtrl1.SetInsertionPoint(0)
        gSizer1.Add( self.m_textCtrl1, 0, wx.ALL, 5 )

        self.m_button1 = wx.Button( self, ID_ADDKEY, u"Add", wx.DefaultPosition, wx.DefaultSize, 0 )
        gSizer1.Add( self.m_button1, 0, wx.ALL, 5 )

        self.list1 = []
        self.ReadConfigFile()
        self.m_lbox1 = wx.ListBox(self, -1, choices=self.list1, style=wx.LB_SINGLE)
        gSizer1.Add( self.m_lbox1, 0, wx.ALL, 5 )

        self.SetSizer( gSizer1 )
        self.Layout()
        self.Centre( wx.BOTH )

        self.Bind( wx.EVT_BUTTON, self.OnAddButtonClicked, self.m_button1 )  

    def OnAddButtonClicked(self, event):
        source_id = event
        print( self.m_textCtrl1.GetValue() )
        self.WriteConfigFile(self.m_textCtrl1.GetValue())

    def ReadConfigFile(self):
        f = None
        try:
            f = open('config.txt', 'a+')
            for line in f.readlines():
                line = line.strip()
                self.list1.append(line)
        finally:
            if f:
                f.close()

    def WriteConfigFile(self, new_str):
        try:
            fw = open('config.txt', 'a+')
            self.list1.append(new_str)
            self.m_lbox1.Append(new_str)
            for line in self.list1:
                fw.write(line + "\n")
        finally:
            if fw:
                fw.close()

class MyApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        frame_terminal = TerminalFrame(None, -1, "")
        self.SetTopWindow(frame_terminal)
        frame_terminal.Show(True)
        return 1

# end of class MyApp

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()