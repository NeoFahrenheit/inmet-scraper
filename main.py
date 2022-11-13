import os
import wx
import wx.richtext as rt
import json
from pathlib import Path
from pubsub import pub

import data_processing
import web_scraper
import file_manager

class Main(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, style=wx.DEFAULT_FRAME_STYLE)

        self.app_folder = os.path.join(Path.home(), '4waTT')
        self.appdata_folder = Path.home()
        self.is_processing_being_done = False
        
        self.app_data = {}
        self.load_file()
        self.file_manager = file_manager.Files(self.app_data)

        self.SetTitle('DNC 4waTT')
        self.SetSize(1000, 680)
        self.init_ui()
        
        self.make_subscriptions()
        self.CenterOnScreen()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(1000)

    def make_subscriptions(self):
        """ Faz os `pub.subscribe` necessários para essa classe. """

        pub.subscribe(self.save_file, 'save-file')
        pub.subscribe(self.update_combos, 'update-combos')
        pub.subscribe(self.add_log, 'log')
        pub.subscribe(self.set_processing_being_done, 'set-processing-being-done')

        # wx.Gauge e wx.StaticTex de progresso.
        pub.subscribe(self.on_clean_progress, 'clean-progress')
        pub.subscribe(self.update_current_gauge, 'update-current-gauge')
        pub.subscribe(self.update_overall_gauge, 'update-overall-gauge')
        pub.subscribe(self.update_current_gauge_range, 'update-current-gauge-range')
        pub.subscribe(self.update_file_text, 'update-file-text')
        pub.subscribe(self.update_overall_text, 'update-overall-text')
        pub.subscribe(self.update_size_text, 'update-size-text')
        pub.subscribe(self.update_speed_text, 'update-speed-text')
    
    def init_ui(self):
        """ Inicializa a UI e seus widgets. """

        self.init_menu()

        master_sizer = wx.BoxSizer(wx.HORIZONTAL)
        station_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        station_sizer = wx.BoxSizer(wx.VERTICAL)
        self.info_sizer = wx.BoxSizer(wx.VERTICAL)

        panel = wx.Panel(self)
        self.status_bar = self.CreateStatusBar()

        # Criando o wx.ListCtrl.
        self.estacaoList = wx.ListCtrl(panel, -1, style=wx.LC_REPORT)
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
        comboSizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Adicionar estações')

        # Campo de seleção de estado.
        stateSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.state = wx.ComboBox(panel, -1, 'Acre', choices=[], style=wx.CB_READONLY | wx.CB_SORT)
        stateSizer.Add(wx.StaticText(panel, -1, 'Estado', size=(60, 23)), flag=wx.TOP, border=3)
        stateSizer.Add(self.state, proportion=1, flag=wx.EXPAND)
        
        # Campo de seleção de cidade.
        citySizer = wx.BoxSizer(wx.HORIZONTAL)
        self.city = wx.ComboBox(panel, -1, 'Acre', choices=[], style=wx.CB_READONLY | wx.CB_SORT)
        citySizer.Add(wx.StaticText(panel, -1, 'Cidade', size=(60, 23)), flag=wx.TOP, border=3)
        citySizer.Add(self.city, proportion=1, flag=wx.EXPAND)

        # Botão de adicionar.
        addBtn = wx.Button(panel, -1, 'Adicionar')

        comboSizer.Add(stateSizer, flag=wx.ALL | wx.EXPAND, border=5)
        comboSizer.Add(citySizer, flag=wx.ALL | wx.EXPAND, border=5)
        comboSizer.Add(addBtn, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando o sizer de procurar por estações.
        searchSizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Procurar por estação')

        searchCtrl = wx.SearchCtrl(panel, -1)
        self.searchBox = wx.ListBox(panel, -1)

        searchSizer.Add(searchCtrl, flag=wx.ALL | wx.EXPAND, border=5)
        searchSizer.Add(self.searchBox, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando o sizer de informações da estação.
        detailsSizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Detalhes da estação')
        self.detailsList = wx.ListCtrl(panel, -1, size=(220, 180), style=wx.LC_REPORT)
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
        self.detailsList.InsertItem(6, 'Altitude')
        self.detailsList.InsertItem(7, 'Fundação')
        detailsSizer.Add(self.detailsList, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando a caixa de texto do logger.
        self.rt = rt.RichTextCtrl(panel, -1, style=rt.RE_READONLY)
        self.info_sizer.Add(self.rt, proportion=1, flag=wx.EXPAND | wx.TOP, border=5)

        # Criando o sizer de progresso de downloads / processamento.
        self.progress_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Progresso')

        self.overall_gauge = wx.Gauge(panel, -1)
        self.current_gauge = wx.Gauge(panel, -1)
        self.overall_text = wx.StaticText(panel, -1, 'Overall Info')
        self.file_text = wx.StaticText(panel, -1, 'File information')
        self.size_text = wx.StaticText(panel, -1, 'Size')
        self.speed_text = wx.StaticText(panel, -1, 'Speed')

        self.progress_sizer.Add(self.overall_text, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=10)
        self.progress_sizer.Add(self.overall_gauge, flag=wx.EXPAND | wx.ALL, border=10)
        self.progress_sizer.Add(self.current_gauge, flag=wx.EXPAND | wx.ALL, border=10)
        self.progress_sizer.Add(self.file_text, flag=wx.EXPAND | wx.LEFT | wx.BOTTOM, border=10)
        self.progress_sizer.Add(self.size_text, flag=wx.EXPAND | wx.LEFT | wx.BOTTOM, border=10)
        self.progress_sizer.Add(self.speed_text, flag=wx.EXPAND | wx.LEFT, border=10)
        self.info_sizer.Add(self.progress_sizer, flag=wx.EXPAND | wx.TOP, border=5)

        # Adionando os sizers ao master.
        station_ctrl_sizer.Add(self.estacaoList, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        station_sizer.Add(comboSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(searchSizer, proportion=3, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(detailsSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        master_sizer.Add(station_ctrl_sizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        master_sizer.Add(station_sizer, proportion=1, flag=wx.ALL, border=5)
        master_sizer.Add(self.info_sizer, proportion=3, flag=wx.EXPAND | wx.ALL, border=10)

        panel.SetSizerAndFit(master_sizer)

    def init_menu(self):
        """ Inicializa o menu. """

        menu = wx.MenuBar()
        file = wx.Menu()
        update = wx.Menu()
        about = wx.Menu()

        menu.Append(file, 'Arquivo')
        menu.Append(update, 'Atualizar')
        menu.Append(about, 'Sobre')

        reset = update.Append(-1, 'Reconstruir a base de dados', 'Apaga toda a base de dados e a re-constrói.')

        self.Bind(wx.EVT_MENU, self.on_reset, reset)

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
                'keep_scrolling': True,
                'last_zip_date': '',    # Data dos últimos dados no último zip.
                'estacoes': {},
                'uf_station': {}
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.app_data, f, indent=4)

    def save_file(self):
        """ Salva `self.app_data` no arquivo de configuração. """

        path = os.path.join(self.appdata_folder, '.4waTT.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.app_data, f, indent=4)

    def update_combos(self):
        """ Atualiza os wx.ComboBox de Estados e Cidades usando `self.app_data['uf_station']`. """

        self.state.Clear()

        for key in self.app_data['uf_station'].keys():
            self.state.Append(key)

    def on_timer(self, event):
        """ Chamada a cada segundo. Chama `pub.sendMessage('ping-timer')`. """

        pub.sendMessage('ping-timer')

    def on_reset(self, event):
        """ Apaga todos os arquivos do programa e reconstrói a base de dados. """

        self.is_processing_being_done = True
        # file_manager.Files().clean_all(False)
        # file_manager.Files().check_folders()

        data = data_processing.DataProcessing(self.app_data).concat_dados_historicos

        web_scraper.Scraper(self, self.app_data, [data])

    def add_log(self, text: str, isError: bool = False):
        """ Adiciona `text` ao log. `isError` define a cor do texto. """

        if isError:
            self.rt.BeginTextColour(wx.RED)
        else:
            self.rt.BeginTextColour(wx.BLACK)

        self.rt.WriteText(text)
        self.rt.Newline()
        self.rt.EndTextColour()

        if self.app_data['keep_scrolling']:
            self.rt.ShowPosition(self.rt.GetLastPosition())
    
    def on_clean_progress(self):
        """ Limpa e reseta todos os campos de progresso de download. """

        self.overall_gauge.SetValue(0)
        self.current_gauge.SetValue(0)
        self.overall_text.SetLabel('')
        self.file_text.SetLabel('')
        self.size_text.SetLabel('')
        self.speed_text.SetLabel('')

    def update_current_gauge(self, value: int):
        """ Atualuza o valor de `self.current_gauge`. """

        self.current_gauge.SetValue(value)    

    def update_overall_gauge(self, value: int):
        """ Atualuza o valor de `self.overall_gauge`. """

        self.overall_gauge.SetValue(value)

    def update_current_gauge_range(self, value: int):
        """ Atualuza o range, valor máximo, de `self.current_gauge`. """

        self.current_gauge.SetRange(value)

    def update_file_text(self, text: str):
        """ Atualuza o valor de `self.file_text`. """

        self.file_text.SetLabel(text)

    def update_overall_text(self, text: str):
        """ Atualuza o valor de `self.overall_text`. """

        self.overall_text.SetLabel(text)

    def update_size_text(self, text: str):
        """ Atualuza o valor de `self.size_text`. """

        self.size_text.SetLabel(text)

    def update_speed_text(self, text: str):
        """ Atualuza o valor de `self.speed_text`. """

        self.speed_text.SetLabel(text)

    def set_processing_being_done(self, value: bool):
        """ Seta o valor de `self.is_processing_being_done`. """

        self.is_processing_being_done = value

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