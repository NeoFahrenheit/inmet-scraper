import wx
import web_scraper

class Main(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetTitle('4waTT')
        self.CenterOnScreen()

        self.InitUI()
        self.InitWebScraper()
    
    def InitUI(self):
        master = wx.BoxSizer(wx.VERTICAL)        

        self.text = wx.StaticText(self, wx.ID_ANY, '', size=(200, 60))
        master.Add(self.text, flag=wx.TOP | wx.ALIGN_CENTER, border=25)

        self.SetSizer(master)

    def InitWebScraper(self):
        ''' Inicializa o web scrapper. '''

        scrapper = web_scraper.Scraper()
        self.text.SetLabel('''O web scrapper foi iniciado. '''
        '''Esta janela irá fechar quando todos os downloads forem concluídos.''')

        self.Destroy()

app = wx.App()
frame = Main(None)
frame.Show()
app.MainLoop()