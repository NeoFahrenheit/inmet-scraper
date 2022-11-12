import os
import wx
import wx.richtext as rt
import tempfile
import json
import web_scraper
from pubsub import pub
import data_processing

class Main(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.scraper_thread = None

        self.appData = {}

        self.SetTitle('DNC 4waTT')
        self.SetSize(800, 600)
        self.CenterOnScreen()

        self.InitUI()
    
    def InitUI(self):
        """ Inicializa a UI e seus widgets. """

        master = wx.BoxSizer(wx.HORIZONTAL)
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        rightSizer = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self)
        self.status_bar = self.CreateStatusBar()

        # Criando o wx.ListCtrl.
        self.list = wx.ListCtrl(self.panel, -1, style=wx.LC_REPORT)
        self.list.InsertColumn(0, 'Estação', wx.LIST_FORMAT_CENTRE)
        self.list.InsertColumn(1, 'Estado', wx.LIST_FORMAT_CENTRE)
        self.list.InsertColumn(2, 'Cidade', wx.LIST_FORMAT_CENTRE)
        self.list.InsertColumn(3, 'Concatenação', wx.LIST_FORMAT_CENTRE)
        self.list.InsertColumn(4, 'Atualização', wx.LIST_FORMAT_CENTRE)

        self.list.SetColumnWidth(0, 250)
        self.list.SetColumnWidth(1, 120)
        self.list.SetColumnWidth(2, 120)
        self.list.SetColumnWidth(3, 120)
        self.list.SetColumnWidth(4, 120)

        self.list.EnableCheckBoxes()

        # Criando o sizer de seleção / pesquisa.
        topRightSizer = wx.BoxSizer(wx.VERTICAL)

        size = (250, 34)
        text_size = (100, 23)

        # Campo pesquisar.
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        search = wx.SearchCtrl(self.panel, -1, size=size)
        searchSizer.Add(wx.StaticText(self.panel, -1, 'Pesquisar', size=text_size), flag=wx.RIGHT, border=5)
        searchSizer.Add(search)

        # Campo de seleção de estado.
        stateSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.state = wx.ComboBox(self.panel, -1, 'Acre', size=size, choices=[], style=wx.CB_READONLY)
        stateSizer.Add(wx.StaticText(self.panel, -1, 'Estado', size=text_size), flag=wx.TOP, border=7)
        stateSizer.Add(self.state)
        
        # Campo de seleção de cidade.
        citySizer = wx.BoxSizer(wx.HORIZONTAL)
        self.city = wx.ComboBox(self.panel, -1, 'Acre', size=size, choices=[], style=wx.CB_READONLY)
        citySizer.Add(wx.StaticText(self.panel, -1, 'Cidade', size=text_size), flag=wx.TOP, border=7)
        citySizer.Add(self.city)

        # Botão de adicionar.
        addBtn = wx.Button(self.panel, -1, 'Adicionar')

        topRightSizer.Add(searchSizer, flag=wx.ALL, border=5)
        topRightSizer.Add(stateSizer, flag=wx.ALL, border=5)
        topRightSizer.Add(citySizer, flag=wx.ALL, border=5)
        topRightSizer.Add(addBtn, flag=wx.ALL, border=5)
        
        rightSizer.Add(topRightSizer, flag=wx.EXPAND)


        leftSizer.Add(self.list)

        master.Add(leftSizer, proportion=1, flag=wx.EXPAND)
        master.Add(rightSizer, proportion=1, flag=wx.EXPAND)
        self.panel.SetSizerAndFit(master)

    def OnQuit(self, event):
        ''' Chamada quando o usuário clica no botão para fechar o programa. '''

        if self.scraper_thread and self.scraper_thread.isActive:
            dlg = wx.MessageDialog(self, 'Ainda há downloads em andamento. Tem certeza que deseja cancelar e sair?',
            'Downloads em andamento', wx.ICON_INFORMATION | wx.YES_NO)
            res = dlg.ShowModal()
            if res == wx.ID_YES:
                self.OnEndThreads()
                self.Destroy()
        else:
            self.OnEndThreads()
            self.Destroy()


app = wx.App()
frame = Main(None)
frame.Show()
app.MainLoop()