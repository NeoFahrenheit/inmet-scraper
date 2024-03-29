import os
import wx
import wx.richtext as rt
import json
from pathlib import Path
from pubsub import pub
import datetime
import shutil

from id import ID
import about
import web_scraper
import file_manager
import data_processing

class Main(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, style=wx.DEFAULT_FRAME_STYLE)

        self.version = 0.1
        self.app_folder = os.path.join(Path.home(), 'inmet')
        self.userdata_folder = Path.home()
        self.is_processing_being_done = False
        
        self.app_data = {}
        self.load_file()
        self.file_manager = file_manager.Files(self.app_data)

        self.SetTitle('INMET Scrapper')
        self.SetSize(1000, 680)
        self.init_ui()
        self.update_combos()
        
        self.make_subscriptions()

        self.CenterOnScreen()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(1000)

        # TODO Na inicializao, precisamos ver se a data do zip parcial continua igual.

    def make_subscriptions(self):
        """ Faz os `pub.subscribe` necessários para essa classe. """

        pub.subscribe(self.save_file, 'save-file')
        pub.subscribe(self.update_combos, 'update-combos')
        pub.subscribe(self.add_log, 'log')
        pub.subscribe(self.set_processing_being_done, 'set-processing-being-done')

        # wx.Gauge e wx.StaticTex de progresso.
        pub.subscribe(self.on_clear_progress, 'clean-progress')
        pub.subscribe(self.update_overall_gauge_range, 'update-overall-gauge-range')
        pub.subscribe(self.update_current_gauge_range, 'update-current-gauge-range')
        pub.subscribe(self.update_current_gauge, 'update-current-gauge')
        pub.subscribe(self.update_overall_gauge, 'update-overall-gauge')
        pub.subscribe(self.update_overall_text, 'update-overall-text')
        pub.subscribe(self.update_file_text, 'update-file-text')
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
        self.stationsCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_station_click)
        self.stationsCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._on_station_rclick)
        self.stationsCtrl.InsertColumn(0, 'Estação', wx.LIST_FORMAT_CENTRE)
        self.stationsCtrl.InsertColumn(1, 'Concatenado', wx.LIST_FORMAT_CENTRE)
        self.stationsCtrl.InsertColumn(2, 'Limpo', wx.LIST_FORMAT_CENTRE)

        self.stationsCtrl.SetColumnWidth(0, 100)
        self.stationsCtrl.SetColumnWidth(1, 100)
        self.stationsCtrl.SetColumnWidth(2, 100)

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

        self.searchCtrl = wx.SearchCtrl(panel, -1)
        self.Bind(wx.EVT_SEARCH, self._on_search)
        self.searchBox = wx.ListBox(panel, ID.LISTBOX)
        self.Bind(wx.EVT_LISTBOX, self._on_list_box)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self._on_dclicked_list_box)

        searchSizer.Add(self.searchCtrl, flag=wx.ALL | wx.EXPAND, border=5)
        searchSizer.Add(self.searchBox, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando o sizer de informações da estação.
        detailsSizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Detalhes da estação')
        self.detailsCtrl = wx.ListCtrl(panel, -1, size=(220, 200), style=wx.LC_REPORT)
        self.detailsCtrl.InsertColumn(0, 'Parâmetro', wx.LIST_FORMAT_CENTRE)
        self.detailsCtrl.InsertColumn(1, 'Valor', wx.LIST_FORMAT_LEFT)

        self.detailsCtrl.SetColumnWidth(0, 100)
        self.detailsCtrl.SetColumnWidth(1, 250)

        self.detailsCtrl.InsertItem(0, 'Região')
        self.detailsCtrl.InsertItem(1, 'UF')
        self.detailsCtrl.InsertItem(2, 'Estação')
        self.detailsCtrl.InsertItem(3, 'Código')
        self.detailsCtrl.InsertItem(4, 'Latitude')
        self.detailsCtrl.InsertItem(5, 'Longitude')
        self.detailsCtrl.InsertItem(6, 'Altitude')
        self.detailsCtrl.InsertItem(7, 'Fundação')
        detailsSizer.Add(self.detailsCtrl, flag=wx.ALL | wx.EXPAND, border=5)

        # Criando a caixa de texto do logger.
        self.rt = rt.RichTextCtrl(panel, -1, style=rt.RE_READONLY)
        self.info_sizer.Add(self.rt, proportion=1, flag=wx.EXPAND | wx.TOP, border=5)

        # Criando o sizer de progresso de downloads / processamento.
        self.progress_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Progresso')

        self.overall_gauge = wx.Gauge(panel, -1)
        self.current_gauge = wx.Gauge(panel, -1)
        self.overall_text = wx.StaticText(panel, -1, '')
        self.file_text = wx.StaticText(panel, -1, '')
        self.size_text = wx.StaticText(panel, -1, '')
        self.speed_text = wx.StaticText(panel, -1, '')

        self.progress_sizer.Add(self.overall_text, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=10)
        self.progress_sizer.Add(self.overall_gauge, flag=wx.EXPAND | wx.ALL, border=10)
        self.progress_sizer.Add(self.current_gauge, flag=wx.EXPAND | wx.ALL, border=10)
        self.progress_sizer.Add(self.file_text, flag=wx.EXPAND | wx.LEFT | wx.BOTTOM, border=10)
        self.progress_sizer.Add(self.size_text, flag=wx.EXPAND | wx.LEFT | wx.BOTTOM, border=10)
        self.progress_sizer.Add(self.speed_text, flag=wx.EXPAND | wx.LEFT, border=10)
        self.info_sizer.Add(self.progress_sizer, flag=wx.EXPAND | wx.TOP, border=5)

        # Adionando os sizers ao master.
        station_ctrl_sizer.Add(self.stationsCtrl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        station_sizer.Add(comboSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(searchSizer, proportion=3, flag=wx.ALL | wx.EXPAND, border=5)
        station_sizer.Add(detailsSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        master_sizer.Add(station_ctrl_sizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        master_sizer.Add(station_sizer, proportion=2, flag=wx.ALL, border=5)
        master_sizer.Add(self.info_sizer, proportion=3, flag=wx.EXPAND | wx.ALL, border=10)

        self.load_stations_saved_data()

        panel.SetSizerAndFit(master_sizer)

    def init_menu(self):
        """ Inicializa o menu. """

        menu = wx.MenuBar()
        file = wx.Menu()
        edit = wx.Menu()
        models = wx.Menu()
        log = wx.Menu()
        help = wx.Menu()

        menu.Append(file, 'Arquivo')
        menu.Append(edit, 'Editar')
        menu.Append(models, 'Modelos')
        menu.Append(log, 'Log')
        menu.Append(help, 'Ajuda')

        make = file.Append(-1, 'Construir base de dados', 'Constrói a base de dados.')
        reset = file.Append(-1, 'Resetar a base de dados', 'Apaga toda a base de dados e a constrói novamente. Pode demorar vários minutos.')
        file.AppendSeparator()
        exit = file.Append(-1, 'Sair', 'Fecha o programa')
        self.Bind(wx.EVT_MENU, self._on_populate, make)
        self.Bind(wx.EVT_MENU, self._on_reset, reset)
        self.Bind(wx.EVT_MENU, self.on_quit, exit)

        concat = edit.Append(-1, 'Concatenar estações', 'Concatena todas as estações cadastradas.')
        clean = edit.Append(-1, 'Limpar estações', 'Limpa todas as estações cadastradas.')
        edit.AppendSeparator()
        delete = edit.Append(-1, 'Remover estações', 'Remove todos os dados das estações selecionadas.')
        self.Bind(wx.EVT_MENU, self._concat_stations, concat)
        self.Bind(wx.EVT_MENU, self._clean_stations, clean)
        self.Bind(wx.EVT_MENU, self._delete_stations, delete)
        
        models.Append(-1, 'Ainda por vir...')

        log_scroll = log.Append(ID.MENU_SCROLL, 'Manter log sempre abaixo', 'Mantém a janela de log sempre abaixo quando novas mensagens são inseridas.', kind=wx.ITEM_CHECK)
        log_clear = log.Append(-1, 'Limpar log', 'Limpa a janela de log.')
        log_save = log.Append(-1, 'Salvar log', 'Salva o conteúdo da janela de log para um arquivo txt.')
        self.Bind(wx.EVT_MENU, self._on_log_scroll, log_scroll)
        self.Bind(wx.EVT_MENU, self._on_log_clear, log_clear)
        self.Bind(wx.EVT_MENU, self._on_log_save, log_save)

        about = help.Append(-1, 'Sobre', 'Exibe informações sobre este programa.')
        self.Bind(wx.EVT_MENU, self._on_about, about)
        
        menu.Check(ID.MENU_SCROLL, self.app_data['keep_scrolling'])
        self.SetMenuBar(menu)

    def load_file(self):
        """ Carrega o arquivo de configuração para `self.app_data`. Se ele não existir,
        será criado com as configurações padrão. """

        path = os.path.join(self.userdata_folder, '.inmet.json')
        file_exists = os.path.isfile(path)

        if file_exists:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
                self.app_data = json.loads(text)
        else:
            self.app_data.clear()
            self.app_data['keep_scrolling'] = True
            self.app_data['last_date'] = '' # Data do último dia dos arquivos baixados.
            self.app_data['saved'] = {}
            self.app_data['stations'] = {}
            
            self.save_file()

    def save_file(self):
        """ Salva `self.app_data` no arquivo de configuração. """

        path = os.path.join(self.userdata_folder, '.inmet.json')
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

    def load_stations_saved_data(self):
        """ Carrega do arquivo de configuração as estações salvas e exibe em `self.stationsCtrl`. """

        if self.app_data['saved']:
            for station, dic in self.app_data['saved'].items():
                concat = 'Sim' if dic['is_concat'] else 'Não'          

                clean = 'Sim' if dic['is_clean'] else 'Não'
                self.stationsCtrl.Append([station, concat, clean])

    def _on_city_selected(self, key: str):
        """ Atualiza o valor das informações da estação usando a `key`. """
        
        dic = self.app_data['stations'][key]
        self.detailsCtrl.SetItem(0, 1, dic['REGIAO:'])
        self.detailsCtrl.SetItem(1, 1, dic['UF:'])
        self.detailsCtrl.SetItem(2, 1, dic['ESTACAO:'])
        self.detailsCtrl.SetItem(3, 1, dic['CODIGO (WMO):'])
        self.detailsCtrl.SetItem(4, 1, dic['LATITUDE:'])
        self.detailsCtrl.SetItem(5, 1, dic['LONGITUDE:'])
        self.detailsCtrl.SetItem(6, 1, dic['ALTITUDE:'])
        self.detailsCtrl.SetItem(7, 1, dic['DATA DE FUNDACAO:'])

    def clear_station_info(self):
        """ Limpa a wx.ListCtrl que mostra os dados das estações. """
        
        self.detailsCtrl.SetItem(0, 1, '')
        self.detailsCtrl.SetItem(1, 1, '')
        self.detailsCtrl.SetItem(2, 1, '')
        self.detailsCtrl.SetItem(3, 1, '')
        self.detailsCtrl.SetItem(4, 1, '')
        self.detailsCtrl.SetItem(5, 1, '')
        self.detailsCtrl.SetItem(6, 1, '')
        self.detailsCtrl.SetItem(7, 1, '')

    def _on_search(self, event):
        """ Chamada quando o usuário usa o campo de Pesquisasr. """

        if not self.app_data['stations']:
            return

        self.searchBox.Clear()        
        text = event.GetString().lower()

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
        self._add_stations_ctrl(station)

    def on_timer(self, event):
        """ Chamada a cada segundo. Chama `pub.sendMessage('ping-timer')`. """

        pub.sendMessage('ping-timer')

    def _on_populate(self, event):
        """ Constrói a base de dados para o programa. """

        if self.is_processing_being_done:
            wx.MessageBox('Por favor, espere todas as outras tarefas terminarem antes de iniciar essa.')
            return

        self.is_processing_being_done = True

        func = self.file_manager.get_stations_list
        web_scraper.Scraper(self, self.app_data, func)

        self.is_processing_being_done = False
        self.on_clear_progress()

    def _on_reset(self, event):
        """ Apaga todos os arquivos do programa e reconstrói a base de dados. """

        if self.is_processing_being_done:
            wx.MessageBox('Por favor, espere todas as outras tarefas terminarem antes de iniciar essa.')
            return

        dlg = wx.MessageDialog(self, 'Você tem certeza que deseja reconstruir a base de dados? Isto deleterá todos os arquivos do programa!',
        'Reconstruir a base de dados', wx.YES_NO | wx.ICON_WARNING)
        response = dlg.ShowModal()

        if response == wx.ID_YES:
            self.is_processing_being_done = True

            self.state.Clear()
            self.city.Clear()
            self.searchCtrl.Clear()
            self.stationsCtrl.DeleteAllItems()
            self.clear_station_info()

            self.file_manager.clean_all()
            self.file_manager.check_folders()
            
            self.load_file()
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
        self._add_stations_ctrl(station)

    def add_log(self, text: str, isError: bool = False):
        """ Adiciona `text` ao log. `isError` define a cor do texto. """

        if isError:
            self.rt.BeginTextColour(wx.RED)
        else:
            self.rt.BeginTextColour(wx.BLACK)

        time = datetime.datetime.now().strftime("%H:%M:%S")
        self.rt.WriteText(f"{time}: {text}")
        self.rt.Newline()
        self.rt.EndTextColour()

        if self.app_data['keep_scrolling']:
            self.rt.ShowPosition(self.rt.GetLastPosition())

    def _add_stations_ctrl(self, station: str):
        """ Insere uma estação ao `self.stationsCtrl`. """

        size = self.stationsCtrl.GetItemCount()
        found = False
        for i in range(0, size):
            item = self.stationsCtrl.GetItemText(i)
            if item == station:
                found = True

        if not found:
            self.stationsCtrl.Append([station, 'Não', 'Não'])
            self.app_data['saved'][station] = {'is_concat': False, 'is_clean': False, 'last_updated': ''}

            # Criando um arquivo vazio no disco. Será sobescrito quando concatenado.
            path = os.path.join(self.app_folder, f'{station}.csv')
            file = open(path, 'w')
            file.close()

            self.save_file()

    def on_clear_progress(self):
        """ Limpa e reseta todos os campos de progresso de download. """

        self.overall_gauge.SetValue(0)
        self.current_gauge.SetValue(0)
        self.overall_text.SetLabel('Processamento / download concluído.')
        self.file_text.SetLabel('')
        self.size_text.SetLabel('')
        self.speed_text.SetLabel('')

    def _on_station_click(self, event):
        """ Chamada quando o usuário clica num item em `self.stationsCtrl`. """

        item = self.stationsCtrl.GetFirstSelected()
        data = self.stationsCtrl.GetItem(item)
        key = data.Text

        self._on_city_selected(key)

    def _on_station_rclick(self, event):
        """ Chamada quando o usuário clica com o botão direito em `self.stationsCtrl`. """

        count = self.stationsCtrl.GetSelectedItemCount()
        item = self.stationsCtrl.GetFirstSelected()
        stations = []

        while item != -1:
            data = self.stationsCtrl.GetItem(item)
            item = self.stationsCtrl.GetNextSelected(item)
            stations.append(data.Text)

        scr = wx.GetMousePosition()
        rel = self.ScreenToClient(scr)
        
        menu = self._crate_popup_menu(stations)
        self.PopupMenu(menu, rel)

    def _crate_popup_menu(self, stations: list):
        """ Cria um menu com base nos itens selecionados em `self.stationsCtrl`. """

        menu = wx.Menu()
        concat = menu.Append(ID.POPUP_CONCAT, 'Concatenar estações selecionadas', 'Concatena todas as estações que estão selecionadas.')
        clean = menu.Append(ID.POPUP_CLEAN, 'Limpar estações selecionadas', 'Limpa todas as estações que estão selecionadas.')
        remove = menu.Append(ID.POPUP_DELETE, 'Remover estações selecionadas', 'Remove todas as estações que estão selecionadas.')
        menu.AppendSeparator()
        save = menu.Append(ID.POPUP_SAVE, 'Salvar estações selecionadas', 'Salva todas as estações que estão selecionadas para um lugar de sua escolha.')

        self.Bind(wx.EVT_MENU, self._concat_stations, concat)
        self.Bind(wx.EVT_MENU, self._clean_stations, clean)
        self.Bind(wx.EVT_MENU, self._delete_stations, remove)
        self.Bind(wx.EVT_MENU, self._save_stations, save)

        return menu

    def _get_selected_stations(self) -> list:
        """ Retorna uma lista com as estações selecionadas em `self.stationsCtrl`. """

        item = self.stationsCtrl.GetFirstSelected()
        stations = []
        while item != -1:
            data = self.stationsCtrl.GetItem(item)
            stations.append(data.Text)
            item = self.stationsCtrl.GetNextSelected(item)

        return stations

    def get_concat_ready_stations(self) -> list:
        """ Retorna uma lista das estações inseridas em `self.stationsCtrl` elegíveis para concatenação. """

        count = self.stationsCtrl.GetItemCount()
        out = []

        for i in range(0, count):
            station = self.stationsCtrl.GetItemText(i)
            concat = self.stationsCtrl.GetItemText(i, 1)

            if concat != 'Sim':
                out.append(station)

        return out

    def get_clean_ready_stations(self) -> list:
        """ Retorna uma lista das estações inseridas em `self.stationsCtrl` elegíveis para a limpeza. """

        count = self.stationsCtrl.GetItemCount()
        out = []

        for i in range(0, count):
            station = self.stationsCtrl.GetItemText(i)
            concat = self.stationsCtrl.GetItemText(i, 1)

            if concat == 'Sim':
                out.append(station)

        return out

    def get_save_ready_stations(self) -> list:
        """ Retorna uma lista das estações que podem ser salvas em disco. """

        count = self.stationsCtrl.GetItemCount()
        out = []

        for i in range(0, count):
            station = self.stationsCtrl.GetItemText(i)
            concat = self.stationsCtrl.GetItemText(i, 1)

            if concat == 'Sim':
                out.append(station)

        return out

    def _concat_stations(self, event):
        """ Pega as estações selecionadas em `self.stationsCtrl` e as concatena. """

        if self.is_processing_being_done:
            wx.MessageBox('Por favor, espere todas as outras tarefas terminarem antes de iniciar essa.')
            return
        
        concat_ready = self.get_concat_ready_stations()

        # IDs dos menus de Popup são maiores que 2000.
        if event.GetId() > 2000:
            selected = self._get_selected_stations()
            stations = [x for x in selected if x in concat_ready]   # Interseção
        else:
            stations = concat_ready

        if not stations:
            wx.MessageBox('Nenhuma estação precisa ser concatenada.')
            return

        self.is_processing_being_done = True
        data_processing.DataProcessing(self.app_data).concat_dados_historicos(stations)

        for station in stations:
            self.app_data['saved'][station]['is_concat'] = True

        self.update_station_ctrl()
        self.is_processing_being_done = False
        wx.CallAfter(self.on_clear_progress)
        self.save_file()

    def _clean_stations(self, event):
        """ Faz a limpeza de todas as estações elegíveis em `self.stationsCtrl.` Para uma estação ser elegível, 
        ela deve estar, no mínimo, concatenada. """

        if self.is_processing_being_done:
            wx.MessageBox('Por favor, espere todas as outras tarefas terminarem antes de iniciar essa.')
            return

        clean_ready = self.get_clean_ready_stations()

        # IDs dos menus de Popup são maiores que 2000.
        if event.GetId() > 2000:
            selected = self._get_selected_stations()
            stations = [x for x in selected if x in clean_ready]   # Interseção
        else:
            stations = clean_ready

        if not stations:
            wx.MessageBox('Nenhuma estação elegível para ser limpa.\nLembre-se: A estação precisa'
            ' estar concatenada primeiro.')
            return

        self.is_processing_being_done = True
        data_processing.DataProcessing(self.app_data).do_data_cleaning(stations)

        for station in stations:
            self.app_data['saved'][station]['is_clean'] = True

        self.update_station_ctrl()
        self.is_processing_being_done = False
        wx.CallAfter(self.on_clear_progress)
        self.save_file()

    def _delete_stations(self, station: str):
        """ Delete `station` em `self.stationsCtrl`, através do popup menu. """

        if self.is_processing_being_done:
            wx.MessageBox('Por favor, espere todas as outras tarefas terminarem antes de iniciar essa.')
            return

        # Indetifica os itens selecionados e armazena em stations.
        stations = self._get_selected_stations()

        if len(stations) == 0:
            wx.MessageBox('Não há estações selecionadas.')
            return

        dlg = wx.MessageDialog(self, "Você tem certeza que deseja deletar as estações selecionadas?",
        "Deletar estações", wx.YES_NO | wx.ICON_WARNING)
        response = dlg.ShowModal()
        if response == wx.ID_YES:
            for station in stations:
                for i in range (0, self.stationsCtrl.GetItemCount()):
                    if self.stationsCtrl.GetItemText(i, 0) == station:
                        self.stationsCtrl.DeleteItem(i)

                        # Deletando a estação no arquivo de configuração.
                        del self.app_data['saved'][station]

                        # Agora, vamos deletá-lo do disco.
                        app_path = os.path.join(self.app_folder, f"{station}.csv")
                        if os.path.isfile(app_path):
                            os.remove(app_path)
                            
                        break   # Sai apenas deste for interior.

            self.save_file()

    def _save_stations(self, event):
        """ Salva as estações selecionadas em uma pasta do disco. """

        if self.is_processing_being_done:
            wx.MessageBox('Por favor, espere todas as outras tarefas terminarem antes de iniciar essa.')
            return

        save_ready = self.get_save_ready_stations()
        selected = self._get_selected_stations()
        stations = [x for x in selected if x in save_ready]   # Interseção

        if not stations:
            wx.MessageBox("Nenhuma estação pronta para ser salva em disco.\nLembre-se: A estação precisa estar "
            " concatenada para ser salva no disco.")
            return

        dlg = wx.DirDialog(self, 'Selecione uma pasta para salvar os arquivos')
        if dlg.ShowModal() == wx.ID_OK:
            dst_path = dlg.GetPath()
        else:
            return

        for station in stations:
            src_path = os.path.join(self.app_folder, f"{station}.csv")
            shutil.copy2(src_path, dst_path)
        
        wx.MessageBox('Arquivos salvos com sucesso.', 'Sucesso', wx.ICON_INFORMATION)

    def update_station_ctrl(self):
        """ Atualiza `self.stationsCtrl` para refletir mudanças em `self.app_data['saved']`. """

        if not self.app_data['saved']:
            return
        
        i = 0
        # Estamos assumindo que os items estejam na mesma posição em stationsCtrl e no arquivo.
        for dic in self.app_data['saved'].values():
            concat = 'Sim' if dic['is_concat'] else 'Não'
            clean = 'Sim' if dic['is_clean'] else 'Não'
            self.stationsCtrl.SetItem(i, 1, concat)
            self.stationsCtrl.SetItem(i, 2, clean)

            i += 1

    def _on_log_scroll(self, event):
        """ Chamada quando o usuário muda a CheckBox de scroll do log. """

        try:
            obj = event.GetEventObject()
            value = obj.IsChecked(ID.MENU_SCROLL)
            self.app_data['keep_scrolling'] = value
            pub.sendMessage('save-file')
        except:
            pass

    def _on_log_clear(self, event):
        """ Limpa a janela de log. """

        self.rt.Clear()

    def _on_log_save(self, event):
        """ Salva o log para um arquivo .txt. """

        dlg = wx.FileDialog(self, 'Seleciona um local e nome para salvar', wildcard="txt (*.txt)|*.txt",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.rt.SaveFile(path)

            wx.MessageBox('Arquivo salvo com sucesso.', 'Sucesso', parent=self)

    def _on_about(self, event):
        """ Abre a janela de sobre. """

        win = about.About(self)
        win.ShowModal()

    def update_current_gauge(self, value: int):
        """ Atualuza o valor de `self.current_gauge`. """

        self.current_gauge.SetValue(value)    

    def update_overall_gauge(self, value: int):
        """ Atualuza o valor de `self.overall_gauge`. """

        self.overall_gauge.SetValue(value)

    def update_overall_gauge_range(self, value: int):
        """ Atualuza o range, valor máximo, de `self.current_gauge`. """

        self.overall_gauge.SetRange(value)

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

    def on_quit(self, event):
        ''' Chamada quando o usuário clica no botão para fechar o programa. '''

        if self.is_processing_being_done:
            dlg = wx.MessageDialog(self, 'Ainda há processos em andamento. Tem certeza que deseja cancelar e sair?',
            'Processos em andamento', wx.ICON_INFORMATION | wx.YES_NO)
            res = dlg.ShowModal()
            if res == wx.ID_YES:
                self.Destroy()
        else:
            self.Destroy()


app = wx.App()
frame = Main(None)
frame.Show()
app.MainLoop()