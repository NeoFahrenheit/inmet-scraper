import os
import wx
import requests
from pubsub import pub


class DownloadWindow(wx.Frame):
    """ 
    Um frame que apresenta uma tela de progresso de downloads ou qualquer outra coisa. 

    Parâmetros
    ----------
    `parent (wx.Frame):` A instância da clase chamante.
    `title (str):` O título da janela.
    `current (int):` O valor máximo do wx.Gauge de progresso geral. Se -1, estará preenchido.
    
    """
    def __init__(self, parent, title: str, overall=-1):
        super().__init__(parent, -1, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.MAXIMIZE_BOX ^ wx.RESIZE_BORDER)

        self.parent = parent
        self.overall_value = overall

        self.init_ui()
        self.SetSize(400, 160)

        self.CenterOnParent()

    def init_ui(self):
        """ Inicializa a UI. """

        sizer = wx.BoxSizer(wx.VERTICAL)
        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel = wx.Panel(self, -1)

        self.overall_gauge = wx.Gauge(panel, -1)
        self.current_gauge = wx.Gauge(panel, -1, range=100)
        self.file_text = wx.StaticText(panel, -1, 'File information', size=(200, 23))
        self.size_text = wx.StaticText(panel, -1, 'Size', size=(180, 23), style=wx.ALIGN_LEFT)
        self.speed_text = wx.StaticText(panel, -1, 'Speed', size=(180, 23), style=wx.ALIGN_RIGHT)

        sizer.Add(self.overall_gauge, flag=wx.EXPAND | wx.ALL, border=10)
        sizer.Add(self.current_gauge, flag=wx.EXPAND | wx.ALL, border=10)
        sizer.Add(self.file_text, flag=wx.EXPAND | wx.LEFT, border=10)

        info_sizer.Add(self.size_text)
        info_sizer.Add(self.speed_text)
        sizer.Add(info_sizer, flag=wx.EXPAND | wx.LEFT, border=10)

        if self.overall_value < 0:
            self.overall_gauge.SetRange(1)
            self.overall_gauge.SetValue(1)
        else:
            self.overall_gauge.SetRange(self.overall_value)

        panel.SetSizerAndFit(sizer)


app = wx.App()
DownloadWindow(None, 'testing', '', '').Show()
app.MainLoop()