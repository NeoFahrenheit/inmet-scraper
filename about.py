import wx
import wx.richtext as rt
import platform
import webbrowser

class About(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.SetTitle('Sobre')
        self.SetSize((350, 400))
        self.CenterOnParent()

        self.initUI()

        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

    def initUI(self):
        ''' Inicializa a UI. '''

        master = wx.BoxSizer(wx.VERTICAL)

        logo = wx.StaticBitmap(self, -1, wx.Bitmap('media/logo.png'))
        name = wx.StaticText(self, -1, 'DNC 4waTT\n')
        ver = wx.StaticText(self, -1, f'Version: {self.parent.version}')
        pyVer = wx.StaticText(self, -1, f'Python: {platform.python_version()}')
        wxVer = wx.StaticText(self, -1, f'wxPython: {wx.__version__}')
        self.rt = rt.RichTextCtrl(self, -1, size=(300, 150), style=wx.TE_READONLY)
        self.rt.GetCaret().Hide()
        self.rt.Bind(wx.EVT_TEXT_URL, self.OnURL)

        self.rt.WriteText("Este software foi criado em uma parceira com a escola DNC e a empresa 4waTT, para o projeto final de curso. ")
        self.rt.WriteText("Este software foi programado por ")
        self.writeInURL('https://www.linkedin.com/in/leandro-monteiro-037bbb75/', 'Leandro Monteiro', False)
        self.rt.WriteText(" em conjunto com todos os membros da equipe:")
        self.rt.Newline()
        self.rt.Newline()

        self.writeInBold('Equipe:')
        self.rt.Newline()
        self.writeInURL('https://github.com/aaa', 'Nome 1')
        self.writeInURL('https://github.com/aaa', 'Nome 2')
        self.writeInURL('https://github.com/aaa', 'Nome 3')
        self.writeInURL('https://github.com/aaa', 'Nome 4')
        self.rt.Newline()

        self.writeInBold('Dependências:')
        self.rt.Newline()
        self.writeInURL('https://pypi.org/project/pandas/', 'pandas')
        self.writeInURL('https://www.wxpython.org/', 'wxPython')
        self.writeInURL('https://pypi.org/project/PyPubSub/', 'pypubsub')
        self.writeInURL('https://pypi.org/project/beautifulsoup4/', 'beautifulsoup4')
        self.rt.Newline()

        self.writeInBold('Contato:')
        self.rt.Newline()
        self.writeInURL('https://4watt.tech/', '4waTT')
        self.writeBlueUnderlined('contato@4watt.tech')

        master.Add(logo, flag=wx.ALL | wx.ALIGN_CENTER, border=10)
        master.Add(name, flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, border=10)
        master.Add(ver, flag=wx.ALIGN_CENTER)
        master.Add(pyVer, flag=wx.ALIGN_CENTER)
        master.Add(wxVer, flag=wx.ALIGN_CENTER)
        master.Add(self.rt, proportion=1, flag=wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER, border=15)

        self.SetSizer(master)

    def writeInBold(self, text):
        ''' Escreve `text` em self.rt em negrito e depois muda para o estilo padrão. '''

        self.rt.ApplyBoldToSelection()
        self.rt.WriteText(text)
        self.rt.SetDefaultStyle(wx.TextAttr())

    def writeInURL(self, url, text, appendNewLine=True):
        ''' Escreve `text` em self.rt no estilo URL e depois muda para o estilo padrão. '''

        self.rt.BeginTextColour(wx.BLUE)
        self.rt.BeginUnderline()
        self.rt.BeginURL(url)
        self.rt.WriteText(text)
        if appendNewLine: self.rt.AppendText('')

        self.rt.EndTextColour()
        self.rt.EndUnderline()
        self.rt.EndURL()

    def OnURL(self, event):
        ''' Chamada quando algum link é clicado. Abre o link no browser padrão da máquina. '''

        webbrowser.open_new(event.GetString())

    def writeBlueUnderlined(self, text):
        ''' Escreve `text` em azul com sublinhado. '''

        self.rt.BeginTextColour(wx.BLUE)
        self.rt.BeginUnderline()

        self.rt.WriteText(text)

        self.rt.EndTextColour()
        self.rt.EndUnderline()

    def OnCloseWindow(self, event):
        ''' Fecha a janela. '''

        self.parent.aboutWindow = None
        self.Destroy()