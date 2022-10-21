import os
from wx import CallAfter
import sys
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pubsub import pub

import downloader

# A idéia dessa classe é ter uma thread para gerenciar outra thread que faz o download.
# Desta maneira, impedimos de a GUI de ficar congelada.
class Scraper(Thread):
    def __init__(self, parent):
        Thread.__init__(self)

        self.last_dados_historicos = ''
        self.isActive = True
        pub.subscribe(self.OnEndThread, 'kill-thread')

        DRIVER_WIN_PATH = 'chromedriver.exe'
        if not os.path.exists('files'):
            os.mkdir('files')

        options = Options()
        options.headless = True
        options.add_argument("--window-size=1920,1200")
        self.driver = webdriver.Chrome(options=options, executable_path=DRIVER_WIN_PATH)

        # self.driver = webdriver.Chrome(executable_path=DRIVER_WIN_PATH)
        self.start()

    def run(self):
        self.dados_historicos_inmet()
        # self.dados_estacoes_inmet()
        self.isActive = False

    def dados_historicos_inmet(self):
        ''' Faz o download de todos os .zip da página `https://portal.inmet.gov.br/dadoshistoricos`. '''

        if not os.path.exists('files/inmet/dados_historicos'):
            os.makedirs('files/inmet/dados_historicos')

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
                path = f'files/inmet/{filename}'
                pub.sendMessage('update-filename', text=filename)
                pub.sendMessage('update-overall-gauge', value=i)
                pub.sendMessage('update-current-gauge', value=0)

                # tag.text é a descrição, em texto, dos links. Vamos pegar a data da última ocorrência dos dados históricos
                # para agregar com tabelas atualizadas mais para frente.
                if 'AUTOMÁTICA' not in tag.text:
                    date = tag.text.split('(ATÉ ')[1]
                    self.last_dados_historicos = date[:-1]

                # Se o arquivo não existe, vamos baixá-lo.
                if not os.path.isfile(path):
                    dl_thread = downloader.DownloadThread(path, url)
                    dl_thread.join() # Apenas um download por vez. Tentar evitar block por IP.
                    CallAfter(self.AddToLog, filename, page_url)
                
                i += 1

            else:
                sys.exit()

    def dados_estacoes_inmet(self):
        ''' Faz o download dos .csv (Tabela de Dados das Estações) de todos os estados do Brasil 
        usando o link `https://tempo.inmet.gov.br/TabelaEstacoes/A422#`. '''

        page_url = 'https://tempo.inmet.gov.br/TabelaEstacoes/A422#'
        self.driver.get(page_url)

        elements = self.driver.find_element(By.XPATH, '//*[@id="root"]/div[1]/div[1]').click()
            
    def OnEndThread(self):
        ''' Usada para mudar a variável `self.isActive` para posteriormente terminar esta thread. '''

        self.isActive = False

    def AddToLog(self, filename, page_url):
        ''' Adiciona uma mensagem ao Log. '''

        pub.sendMessage('log-text', text=f"{filename} de {page_url} baixado com sucesso.")




