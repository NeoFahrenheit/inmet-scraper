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
        self.SetSize(1100, 680)
        self.init_ui()
        self.update_combos()
        
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
        pub.subscribe(self.on_clear_progress, 'clean-progress')
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
        self.stationsCtrl = wx.ListCtrl(panel, -1, style=wx.LC_REPORT)
        self.stationsCtrl.InsertColumn(0, 'Estação', wx.LIST_FORMAT_CENTRE)
        self.stationsCtrl.InsertColumn(1, 'Concatenado', wx.LIST_FORMAT_CENTRE)
        self.stationsCtrl.InsertColumn(2, 'Atualizado', wx.LIST_FORMAT_CENTRE)

        self.stationsCtrl.SetColumnWidth(0, 120)
        self.stationsCtrl.SetColumnWidth(1, 120)
        self.stationsCtrl.SetColumnWidth(2, 120)

        # Criando o sizer de seleção / pesquisa.
        comboSizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Adicionar estações')

        # Campo de seleção de estado.
        stateSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.state = wx.ComboBox(panel, -1, 'Acre', choices=[], style=wx.CB_READONLY | wx.CB_SORT)
        self.state.Bind(wx.EVT_COMBOBOX, self._on_state)
        stateSizer.Add(wx.StaticText(panel, -1, 'Estado', size=(60, 23)), flag=wx.TOP, border=3)
        stateSizer.Add(self.state, proportion=1, flag=wx.EXPAND)
        
        # Campo de seleção de cidade.
        citySizer = wx.BoxSizer(wx.HORIZONTAL)
        self.city = wx.ComboBox(panel, -1, 'Acre', choices=[], style=wx.CB_READONLY | wx.CB_SORT)
        self.city.Bind(wx.EVT_COMBOBOX, self._on_city)
        citySizer.Add(wx.StaticText(panel, -1, 'Cidade', size=(60, 23)), flag=wx.TOP, border=3)
        citySizer.Add(self.city, proportion=1, flag=wx.EXPAND)

        # Botão de adicionar.
        addBtn = wx.Button(panel, -1, 'Adicionar')
        self.Bind(wx.EVT_BUTTON, self._on_add_station)

        comboSizer.Add(stateSizer, flag=wx.ALL | wx.EXPAND, border=5)
        comboSizer.Add(citySizer, flag=wx.ALL | wx.EXPAND, border=5)
        comboSizer.Add(addBtn, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando o sizer de procurar por estações.
        searchSizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Procurar por estação')

        searchCtrl = wx.SearchCtrl(panel, -1)
        self.Bind(wx.EVT_SEARCH, self._on_search)
        self.searchBox = wx.ListBox(panel, -1)
        self.Bind(wx.EVT_LISTBOX, self._on_list_box)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self._on_dclicked_list_box)

        searchSizer.Add(searchCtrl, flag=wx.ALL | wx.EXPAND, border=5)
        searchSizer.Add(self.searchBox, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando o sizer de informações da estação.
        detailsSizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Detalhes da estação')
        self.detailsList = wx.ListCtrl(panel, -1, size=(220, 200), style=wx.LC_REPORT)
        self.detailsList.InsertColumn(0, 'Parâmetro', wx.LIST_FORMAT_CENTRE)
        self.detailsList.InsertColumn(1, 'Valor', wx.LIST_FORMAT_LEFT)

        self.detailsList.SetColumnWidth(0, 100)
        self.detailsList.SetColumnWidth(1, 250)

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
        self.progress_sizer.ShowItems(False)

        # Adionando os sizers ao master.
        station_ctrl_sizer.Add(self.stationsCtrl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        station_sizer.Add(comboSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(searchSizer, proportion=3, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(detailsSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        master_sizer.Add(station_ctrl_sizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        master_sizer.Add(station_sizer, proportion=2, flag=wx.ALL, border=5)
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
                'saved': {},
                'stations': {},
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.app_data, f, indent=4)

    def save_file(self):
        """ Salva `self.app_data` no arquivo de configuração. """

        path = os.path.join(self.appdata_folder, '.4waTT.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.app_data, f, indent=4)

    def update_combos(self):
        """ Atualiza os wx.ComboBox de Estados e Cidades usando `self.app_data['stations']`. """

        if not self.app_data['stations']:
            return

        self.state.Clear()
        out_list = []

        for dic in self.app_data['stations'].values():
            if dic['UF:'] not in out_list:
                out_list.append(dic['UF:'])

        out_list.sort()
        for uf in out_list:
            self.state.Append(uf)

        self.state.SetValue(out_list[0])
        self._on_state(None)

    def _on_city_selected(self, key: str):
        """ Atualiza o valor das informações da estação usando a `key`. """
        
        dic = self.app_data['stations'][key]
        self.detailsList.SetItem(0, 1, dic['REGIAO:'])
        self.detailsList.SetItem(1, 1, dic['UF:'])
        self.detailsList.SetItem(2, 1, dic['ESTACAO:'])
        self.detailsList.SetItem(3, 1, dic['CODIGO (WMO):'])
        self.detailsList.SetItem(4, 1, dic['LATITUDE:'])
        self.detailsList.SetItem(5, 1, dic['LONGITUDE:'])
        self.detailsList.SetItem(6, 1, dic['ALTITUDE:'])
        self.detailsList.SetItem(7, 1, dic['DATA DE FUNDACAO:'])

    def _on_search(self, event):
        """ Chamada quando o usuário usa o campo de Pesquisasr. """

        if not self.app_data['stations']:
            return

        self.searchBox.Clear()        
        text = event.GetString().lower()
        out_list = []

        for station in self.app_data['stations'].values():
            if station['name'].lower().find(text) > -1:
                self.searchBox.Append(station['name'])

    def _on_list_box(self, event):
        """ Chamada quando o usuário clica em um item na wx.ListBox (resultado da pesquisa). """

        index = self.searchBox.GetSelection()
        station = self.searchBox.GetString(index)
        key = station.split()[0]

        self._on_city_selected(key)
        
    def _on_dclicked_list_box(self, event):
        """ Chamada quando o usuário dá clique duplo em um item na wx.ListBox (resultado da pesquisa). """

        index = self.searchBox.GetSelection()
        station = self.searchBox.GetString(index).split()[0]
        self.add_stations_ctrl(station)

    def on_timer(self, event):
        """ Chamada a cada segundo. Chama `pub.sendMessage('ping-timer')`. """

        pub.sendMessage('ping-timer')

    def on_reset(self, event):
        """ Apaga todos os arquivos do programa e reconstrói a base de dados. """

        dlg = wx.MessageDialog(self, 'Você tem certeza que deseja reconstruir a base de dados?',
        'Reconstruir a base de dados', wx.YES_NO | wx.ICON_WARNING)
        response = dlg.ShowModal()

        if response == wx.ID_YES:
            self.is_processing_being_done = True
            self.file_manager.clean_all(False)
            self.file_manager.check_folders()
            func = self.file_manager.get_stations_list

            web_scraper.Scraper(self, self.app_data, func)

    def _on_state(self, event):
        """ Chamada quando o valor na ComboBox de estado é mudado. """

        UF = self.state.GetValue()
        self.city.Clear()
        out_list = []

        for station in self.app_data['stations'].values():
            if station['UF:'] == UF:
                out_list.append(station['name'])

        out_list.sort()
        for name in out_list:
            self.city.Append(name)

        self.city.SetValue(out_list[0])

    def _on_city(self, event):
        """ Chamada quando o valor na ComboBox da cidade é mudado. """

        value = self.city.GetValue()
        key = value.split()[0]
        self._on_city_selected(key)


    def _on_add_station(self, event):
        """ Chamada quando o usuário clica no botão `Adicionar`. """

        station = self.city.GetValue().split()[0]
        self.add_stations_ctrl(station)

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

    def add_stations_ctrl(self, station: str):
        """ Insere uma estação ao `self.stationsCtrl`. """

        size = self.stationsCtrl.GetItemCount()
        found = False
        for i in range(0, size):
            item = self.stationsCtrl.GetItemText(i)
            if item == station:
                found = True

        if not found:
            self.stationsCtrl.Append([station, "Não", "Não"])

    def on_clear_progress(self):
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
        """ Seta o valor de `self.is_processing_being_done`. Como o download / processamento 
        provavelmente já acabou, esconde o sizer do progresso. """

        self.is_processing_being_done = value

        self.on_clear_progress()
        self.progress_sizer.ShowItems(False)
        self.info_sizer.Layout()

    def on_quit(self, event):
        ''' Chamada quando o usuário clica no botão para fechar o programa. '''

        if self.is_processing_being_done:
            dlg = wx.MessageDialog(self, 'Ainda há processos em andamento. Tem certeza que deseja cancelar e sair?',
            'Processos em andamento', wx.ICON_INFORMATION | wx.YES_NO)
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