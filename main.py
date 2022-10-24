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
        self.LoadSaveFiles()
    
    def InitUI(self):
        master = wx.BoxSizer(wx.HORIZONTAL)
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        rightSizer = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self, -1)
        self.rt = rt.RichTextCtrl(self.panel, -1, style=wx.TE_READONLY)
        self.rt.GetCaret().Hide()

        rightSizer.Add(self.rt, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        master.Add(leftSizer, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        master.Add(rightSizer, proportion=3, flag=wx.ALL | wx.EXPAND, border=5)

        self.status_t = wx.StaticText(self.panel, -1, 'Web Scraper de dados meteorológicos')
        self.page_t = wx.StaticText(self.panel, -1, '') # Nome da página de download atual
        self.filename_t = wx.StaticText(self.panel, -1, '', style=wx.ALIGN_LEFT) # Nome do arquivo.
        self.fileSize_t = wx.StaticText(self.panel, -1, '', style=wx.ALIGN_LEFT)  # Status de download
        self.fileSpeed_t = wx.StaticText(self.panel, -1, '', style=wx.ALIGN_LEFT)  # Status de download
        self.topGauge = wx.Gauge(self.panel, -1, style=wx.GA_SMOOTH, size=(300, 30))
        self.curGauge = wx.Gauge(self.panel, -1, size=(300, 30))
        self.startBtn = wx.Button(self.panel, -1, 'Iniciar coleta de dados')
        # self.updateBtn = wx.Button(self.panel, -1, 'Atualizar arquivos...')
        self.warning_t = wx.StaticText(self.panel, -1, "Se precisar modificar os arquivos salvos na pasta Documentos,\n"
        "faça uma cópia. Deixe os originais intactos.", style=wx.ALIGN_CENTER)

        self.startBtn.Bind(wx.EVT_BUTTON, self.OnStartDownloads)
        # self.updateBtn.Bind(wx.EVT_BUTTON, self.OnUpdateFiles)
        self.filename_t.Wrap(100)

        geralSizer = wx.BoxSizer(wx.VERTICAL)
        currentSizer = wx.BoxSizer(wx.VERTICAL)
        
        currentSizer.Add(self.curGauge, flag=wx.ALL | wx.EXPAND, border=5)
        currentSizer.Add(self.filename_t, flag=wx.LEFT | wx.EXPAND, border=5)
        currentSizer.Add(self.fileSize_t, flag=wx.LEFT | wx.EXPAND, border=5)
        currentSizer.Add(self.fileSpeed_t, flag=wx.LEFT | wx.EXPAND, border=5)

        geralSizer.Add(self.topGauge, flag=wx.ALL | wx.EXPAND, border=5)
        geralSizer.Add(self.page_t, flag=wx.ALL | wx.EXPAND, border=5)

        leftSizer.Add(self.status_t, flag=wx.TOP | wx.ALIGN_CENTER, border=5)
        leftSizer.Add(geralSizer, flag=wx.TOP | wx.EXPAND, border=25)
        leftSizer.Add(currentSizer, flag=wx.TOP | wx.EXPAND, border=75)
        leftSizer.Add(self.startBtn, flag=wx.TOP | wx.ALIGN_CENTER, border=50)
        # leftSizer.Add(self.updateBtn, flag=wx.TOP | wx.ALIGN_CENTER, border=25)
        leftSizer.Add(self.warning_t, flag=wx.TOP | wx.ALIGN_CENTER, border=50)

        pub.subscribe(self.OnUpdateOverallGauge, 'update-overall-gauge')
        pub.subscribe(self.OnUpdateOverallGaugeMaxValue, 'update-overall-gauge-maximum-value')
        pub.subscribe(self.OnUpdateCurrentGaugeMaxValue, 'update-current-gauge-maximum-value')
        pub.subscribe(self.OnUpdateCurrentGauge, 'update-current-gauge')
        pub.subscribe(self.OnUpdatePageInfo, 'update-page-info')
        pub.subscribe(self.OnUpdateTransferSpeed,'update-transfer-status')
        pub.subscribe(self.OnUpdateFilename,'update-filename')
        pub.subscribe(self.OnAddToLog, 'log-text')
        pub.subscribe(self.SaveFile, 'save-file')

        self.timer = wx.Timer(self)

        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)
        
        self.panel.SetSizer(master)

    def LoadSaveFiles(self):
        ''' Carrega dos arquivos salvos do programa. '''

        home = os.path.expanduser('~')

        if not os.path.isfile(f'{home}/.4watt.json'):
            self.appData['is_historial_concluded'] = False

            with open(f'{home}/.4watt.json', 'w') as f:
                json.dump(self.appData, f, indent=4)

        else:
            with open(f'{home}/.4watt.json', 'r', encoding='utf-8') as f:
                text = f.read()
                self.appData = json.loads(text)

    def SaveFile(self):
        ''' Salva `self.appData` no disco. '''

        home = os.path.expanduser('~')
        with open(f'{home}/.4watt.json', 'w') as f:
            json.dump(self.appData, f, indent=4)

    def OnUpdateOverallGauge(self, value):
        ''' Atualiza a barra de progresso que mostra o estado de todos os downloads da página. '''
        self.topGauge.SetValue(value)

    def OnUpdateOverallGaugeMaxValue(self, value):
        ''' Atualiza o número de "clicks" máximo que a barra de progresso geral tem. '''
        self.topGauge.SetRange(value)

    def OnUpdateCurrentGauge(self, value):
        ''' Atualiza a barra de progresso do download corrente. '''
        self.curGauge.SetValue(value)

    def OnUpdateCurrentGaugeMaxValue(self, value):
        ''' Atualiza o valor máximo da barra de download corrente. '''
        self.curGauge.SetRange(value)

    def OnUpdatePageInfo(self, text):
        ''' Atualiza o texto que traz informações sobre a página onde está sendo feito o download. '''
        self.page_t.SetLabel(text)
        self.page_t.Wrap(300)

    def OnUpdateTransferSpeed(self, text: list):
        ''' Atualiza o texto que mostra as informações de download e velocidade do arquivo atualmente sendo baixado. 
        Recebe uma lista com duas strings. '''
        self.fileSize_t.SetLabel(text[0])
        self.fileSpeed_t.SetLabel(text[1])

    def OnUpdateFilename(self, text):
        ''' Atualiza o texto que mostra o nome do arquivo que está sendo baixado. '''
        self.filename_t.SetLabel(text)

    def OnTimer(self, event):
        ''' Usada pra "ativar" as funções que usam do timer. Chamada a cada 1 segundo. '''
        pub.sendMessage('ping-timer')

    def OnAddToLog(self, text, isError=False):
        ''' Adiciona um texto a janela de log. '''

        if isError:
            self.rt.BeginTextColour(wx.RED)
        else:
            self.rt.BeginTextColour(wx.BLACK)

        self.rt.WriteText(f"{text}\n")
        self.rt.EndTextColour()

        self.rt.ShowPosition(self.rt.GetLastPosition())

    def InitWebScraper(self):
        ''' Inicializa o web scrapper. '''

        temp_path = f"{tempfile.gettempdir()}/4watt"
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

        self.scraper_thread = web_scraper.Scraper(self.appData)
        self.scraper_thread.start()
        self.timer.Start(1000)  

    def OnEndThreads(self):
        ''' Usada para terminar todas as threads de donwloads ativas, se existirem. '''

        pub.sendMessage('kill-thread')

    def OnStartDownloads(self, event):
        """ Inicia a coleta de dados. """

        self.startBtn.Disable()
        # self.updateBtn.Disable()

        self.InitWebScraper()

    def OnUpdateFiles(self, event):
        """ Chamada quando o botão de atualizar os arquivos é pressionado. 
        Se os dados históricos já estiverem baixados e concatenados, atualiza-os. """

        self.startBtn.Disable()
        # self.updateBtn.Disable()

        temp_path = f"{tempfile.gettempdir()}/4watt"
        dp = data_processing.DataProcessing(temp_path, self.appData)
        dp.update_estacoes()

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