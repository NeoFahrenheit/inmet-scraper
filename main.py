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
        super().__init__(parent, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        self.scraper_thread = None

        self.appData = {}

        self.SetTitle('DNC 4waTT')
        self.SetSize(690, 600)
        self.InitUI()
        
        self.CenterOnScreen()

    
    def InitUI(self):
        """ Inicializa a UI e seus widgets. """

        self.InitMenu()

        master = wx.BoxSizer(wx.HORIZONTAL)
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        rightSizer = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self)
        self.status_bar = self.CreateStatusBar()

        # Criando o wx.ListCtrl.
        self.estacaoList = wx.ListCtrl(self.panel, -1, style=wx.LC_REPORT)
        self.estacaoList.InsertColumn(0, 'Estação', wx.LIST_FORMAT_CENTRE)
        self.estacaoList.InsertColumn(1, 'Concatenação', wx.LIST_FORMAT_CENTRE)
        self.estacaoList.InsertColumn(2, 'Atualização', wx.LIST_FORMAT_CENTRE)

        self.estacaoList.SetColumnWidth(0, 120)
        self.estacaoList.SetColumnWidth(1, 120)
        self.estacaoList.SetColumnWidth(2, 120)

        self.estacaoList.InsertItem(0, 'teste')
        self.estacaoList.SetItem(0, 1, 'Concatenado')
        self.estacaoList.SetItem(0, 2, 'Desatualizado')

        # Criando o sizer de seleção / pesquisa.
        comboSizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, 'Adicionar estações')

        # Campo de seleção de estado.
        stateSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.state = wx.ComboBox(self.panel, -1, 'Acre', choices=[], style=wx.CB_READONLY)
        stateSizer.Add(wx.StaticText(self.panel, -1, 'Estado', size=(60, 23)), flag=wx.TOP, border=3)
        stateSizer.Add(self.state, proportion=1, flag=wx.EXPAND)
        
        # Campo de seleção de cidade.
        citySizer = wx.BoxSizer(wx.HORIZONTAL)
        self.city = wx.ComboBox(self.panel, -1, 'Acre', choices=[], style=wx.CB_READONLY)
        citySizer.Add(wx.StaticText(self.panel, -1, 'Cidade', size=(60, 23)), flag=wx.TOP, border=3)
        citySizer.Add(self.city, proportion=1, flag=wx.EXPAND)

        # Botão de adicionar.
        addBtn = wx.Button(self.panel, -1, 'Adicionar')

        comboSizer.Add(stateSizer, flag=wx.ALL | wx.EXPAND, border=5)
        comboSizer.Add(citySizer, flag=wx.ALL | wx.EXPAND, border=5)
        comboSizer.Add(addBtn, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando o sizer de procurar por estações.
        searchSizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, 'Procurar por estação')

        searchCtrl = wx.SearchCtrl(self.panel, -1)
        self.searchBox = wx.ListBox(self.panel, -1)

        searchSizer.Add(searchCtrl, flag=wx.ALL | wx.EXPAND, border=5)
        searchSizer.Add(self.searchBox, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando o sizer de informações da estação.
        detailsSizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, 'Detalhes da estação')
        self.detailsList = wx.ListCtrl(self.panel, -1, size=(220, 160), style=wx.LC_REPORT)
        self.detailsList.InsertColumn(0, 'Parâmetro', wx.LIST_FORMAT_CENTRE)
        self.detailsList.InsertColumn(1, 'Valor', wx.LIST_FORMAT_CENTRE)

        self.detailsList.SetColumnWidth(0, 100)
        self.detailsList.SetColumnWidth(1, 150)

        self.detailsList.InsertItem(0, 'Região')
        self.detailsList.InsertItem(1, 'UF')
        self.detailsList.InsertItem(2, 'Estação')
        self.detailsList.InsertItem(3, 'Código')
        self.detailsList.InsertItem(4, 'Latitude')
        self.detailsList.InsertItem(5, 'Longitude')
        self.detailsList.InsertItem(6, 'Fundação')
        detailsSizer.Add(self.detailsList, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        # Adionando os sizers ao master.
        leftSizer.Add(self.estacaoList, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        rightSizer.Add(comboSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        rightSizer.Add(searchSizer, proportion=3, flag=wx.ALL | wx.EXPAND, border=5)
        rightSizer.Add(detailsSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        master.Add(leftSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        master.Add(rightSizer, proportion=3, flag=wx.ALL, border=5)

        self.panel.SetSizerAndFit(master)

    def InitMenu(self):
        """ Inicializa o menu. """

        menu = wx.MenuBar()
        file = wx.Menu()
        actions = wx.Menu()
        about = wx.Menu()

        menu.Append(file, 'Arquivo')
        menu.Append(actions, 'Fazer')
        menu.Append(about, 'Sobre')

        self.SetMenuBar(menu)

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