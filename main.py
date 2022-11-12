import os
import wx
import wx.richtext as rt
import json
from pathlib import Path
import web_scraper
from pubsub import pub
import data_processing

class Main(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, style=wx.DEFAULT_FRAME_STYLE)

        self.app_data = {}
        self.app_folder = os.path.join(Path.home(), '4waTT')
        self.appdata_folder = Path.home()

        self.SetTitle('DNC 4waTT')
        self.SetSize(1000, 680)
        self.init_ui()
        self.load_file()
        
        self.make_subscriptions()
        self.CenterOnScreen()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(1000)

    def make_subscriptions(self):
        """ Faz os `pub.subscribe` necessários para essa classe. """

        pub.subscribe(self.save_file, 'save-file')
    
    def init_ui(self):
        """ Inicializa a UI e seus widgets. """

        self.init_menu()

        master_sizer = wx.BoxSizer(wx.HORIZONTAL)
        station_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        station_sizer = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self)
        self.status_bar = self.CreateStatusBar()

        # Criando o wx.ListCtrl.
        self.estacaoList = wx.ListCtrl(self.panel, -1, style=wx.LC_REPORT)
        self.estacaoList.InsertColumn(0, 'Estação', wx.LIST_FORMAT_CENTRE)
        self.estacaoList.InsertColumn(1, 'Concatenado', wx.LIST_FORMAT_CENTRE)
        self.estacaoList.InsertColumn(2, 'Atualizado', wx.LIST_FORMAT_CENTRE)

        self.estacaoList.SetColumnWidth(0, 120)
        self.estacaoList.SetColumnWidth(1, 120)
        self.estacaoList.SetColumnWidth(2, 120)

        self.estacaoList.InsertItem(0, 'A807')
        self.estacaoList.SetItem(0, 1, 'Não')
        self.estacaoList.SetItem(0, 2, 'Não')

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
        self.detailsList.SetColumnWidth(1, 120)

        self.detailsList.InsertItem(0, 'Região')
        self.detailsList.InsertItem(1, 'UF')
        self.detailsList.InsertItem(2, 'Estação')
        self.detailsList.InsertItem(3, 'Código')
        self.detailsList.InsertItem(4, 'Latitude')
        self.detailsList.InsertItem(5, 'Longitude')
        self.detailsList.InsertItem(6, 'Fundação')
        detailsSizer.Add(self.detailsList, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando a caixa de texto do logger.
        self.rt = rt.RichTextCtrl(self.panel, -1, style=rt.RE_READONLY)

        # Adionando os sizers ao master.
        station_ctrl_sizer.Add(self.estacaoList, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        station_sizer.Add(comboSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(searchSizer, proportion=3, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(detailsSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        master_sizer.Add(station_ctrl_sizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        master_sizer.Add(station_sizer, proportion=1, flag=wx.ALL, border=5)
        master_sizer.Add(self.rt, proportion=3, flag=wx.EXPAND | wx.ALL, border=10)

        self.panel.SetSizerAndFit(master_sizer)

    def init_menu(self):
        """ Inicializa o menu. """

        menu = wx.MenuBar()
        file = wx.Menu()
        actions = wx.Menu()
        about = wx.Menu()

        menu.Append(file, 'Arquivo')
        menu.Append(actions, 'Fazer')
        menu.Append(about, 'Sobre')

        self.SetMenuBar(menu)

    def load_file(self):
        """ Carrega o arquivo de configuração para `self.app_data`. Se ele não existir,
        será criado com as configurações padrão. """

        path = os.path.join(self.appdata_folder, '.4waTT.json')
        file_exists = os.path.isfile(path)

        if file_exists:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
                self.app_data = json.loads(text)
        else:
            self.app_data = {
                'last_zip_date': '',    # Data dos últimos dados no último zip.
                'estacoes': {}
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.app_data, f, indent=4)

    def save_file(self):
        """ Salva `self.app_data` no arquivo de configuração. """

        path = os.path.join(self.appdata_folder, '.4waTT.json')
        with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.app_data, f, indent=4)

    def on_timer(self, event):
        """ Chamada a cada segundo. Chama `pub.sendMessage('ping-timer')`. """

        pub.sendMessage('ping-timer')

    def on_quit(self, event):
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