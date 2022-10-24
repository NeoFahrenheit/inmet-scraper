import os
from wx import CallAfter
import sys
import tempfile
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pubsub import pub

import downloader
import data_processing

# A idéia dessa classe é ter uma thread para gerenciar outra thread que faz o download.
# Desta maneira, impedimos de a GUI de ficar congelada.


class Scraper(Thread):
    def __init__(self, data):
        Thread.__init__(self)

        self.temp_path = f"{tempfile.gettempdir()}/4watt"
        self.docs_path = os.path.expanduser('~/Documents/4watt')
        self.appData = data

        self.is_historial_concluded = ''
        self.isActive = True
        
        pub.subscribe(self.OnEndThread, 'kill-thread')
        DRIVER_WIN_PATH = 'chromedriver.exe'

        options = Options()
        options.headless = True
        options.add_argument("--window-size=1920,1200")
        self.driver = webdriver.Chrome(options=options, executable_path=DRIVER_WIN_PATH)

    def run(self):
        self.download_dados_inmet()

    def download_dados_inmet(self):
        ''' Faz o download de todos os .zip da página `https://portal.inmet.gov.br/dadoshistoricos`. '''

        dp = data_processing.DataProcessing(self.temp_path, self.appData)

        if self.appData['is_historial_concluded']:
            dp.update_estacoes()
            return

        page_url = 'https://portal.inmet.gov.br/dadoshistoricos'
        pub.sendMessage('update-page-info', text=f"Baixando da página {page_url}")
        self.driver.get(page_url)

        elements = self.driver.find_elements(By.TAG_NAME, "article")
        pub.sendMessage('update-overall-gauge-maximum-value', value=len(elements))
        
        i = 1
        for link in elements:
            if self.isActive:
                tag = link.find_element(By.TAG_NAME, 'a')
                url = tag.get_attribute('href')
                filename = os.path.basename(url)
                path = f'{self.temp_path}/{filename}'
                pub.sendMessage('update-filename', text=filename)
                pub.sendMessage('update-overall-gauge', value=i)
                pub.sendMessage('update-current-gauge', value=0)

                # Se o arquivo não existe, vamos baixá-lo.
                if not os.path.isfile(path):
                    dl_thread = downloader.DownloadThread(self, path, url)
                    dl_thread.join() # Apenas um download por vez. Tentar evitar block por IP.
                    CallAfter(self.AddToLog, filename, page_url)

                i += 1

            else:
                sys.exit()
        
        dp.concat_dados_historicos(self.temp_path)
        self.appData['is_historial_concluded'] = True
        pub.sendMessage('save-file')
        
        dp.update_estacoes()
    

    def OnEndThread(self):
        ''' Usada para mudar a variável `self.isActive` para posteriormente terminar esta thread. '''

        self.isActive = False

    def AddToLog(self, filename, page_url):
        ''' Adiciona uma mensagem ao Log. '''

        pub.sendMessage('log-text', text=f"{filename} de {page_url} baixado com sucesso.")




