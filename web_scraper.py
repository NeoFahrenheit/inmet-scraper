import os
from wx import CallAfter
import sys
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
    def __init__(self, temp_path, data):
        Thread.__init__(self)

        self.temp_path = temp_path
        self.appData = data

        self.last_dados = ''
        self.isActive = True
        
        pub.subscribe(self.OnEndThread, 'kill-thread')
        DRIVER_WIN_PATH = 'chromedriver.exe'

        options = Options()
        options.headless = True
        options.add_argument("--window-size=1920,1200")
        self.driver = webdriver.Chrome(options=options, executable_path=DRIVER_WIN_PATH)

        self.start()

    def run(self):
        self.dados_historicos_inmet()
        # self.dados_estacoes_inmet()

    def dados_historicos_inmet(self):
        ''' Faz o download de todos os .zip da página `https://portal.inmet.gov.br/dadoshistoricos`. '''

        if self.appData['last_data']:
            # self.updateDataSet()
            return

        last_dados = ''

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
                
                # tag.text é a descrição, em texto, dos links. Vamos pegar a data da última ocorrência dos dados históricos
                # para agregar com tabelas atualizadas mais para frente.
                if 'AUTOMÁTICA' not in tag.text:
                    date = tag.text.split('(ATÉ ')[1]
                    last_dados = date[:-1]

                i += 1

            else:
                sys.exit()
        
        self.appData['last_data'] = last_dados
        pub.sendMessage('save-file')
        dp = data_processing.DataProcessing(self.temp_path)
        dp.concat_dados_historicos()
    

    def OnEndThread(self):
        ''' Usada para mudar a variável `self.isActive` para posteriormente terminar esta thread. '''

        self.isActive = False

    def AddToLog(self, filename, page_url):
        ''' Adiciona uma mensagem ao Log. '''

        pub.sendMessage('log-text', text=f"{filename} de {page_url} baixado com sucesso.")




