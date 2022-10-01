import os
import requests
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pubsub import pub

import downloader

# A idéia dessa classe é ter uma thread para gerenciar outra thread que faz o download.
# Desta maneira, impedimos que a GUI de ficar congelada.
class Scraper(Thread):
    def __init__(self, parent):
        Thread.__init__(self)
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

    def dados_historicos_inmet(self):
        ''' Faz o download de todos os .zip da página `https://portal.inmet.gov.br/dadoshistoricos`. '''

        if not os.path.exists('files/inmet'):
            os.mkdir('files/inmet')

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
                pub.sendMessage('update-filename', text=filename)
                
                pub.sendMessage('update-overall-gauge', value=i)
                dl_thread = downloader.DownloadThread(f'files/inmet/{filename}', url)
                dl_thread.join() # Apenas um download por vez. Tentar evitar block por IP.
                i += 1
            
    def OnEndThread(self):
        ''' Usada para mudar a variável `self.isActive` para posteriormente terminar esta thread. '''
        self.isActive = False



