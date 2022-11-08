import os
from wx import CallAfter
import sys
import tempfile
from threading import Thread
import requests
from bs4 import BeautifulSoup
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

    def run(self):
        # self.download_dados_inmet()
        dp = data_processing.DataProcessing(self.temp_path, self.appData)
        dp.do_data_cleaning()

    def download_dados_inmet(self):
        ''' Faz o download de todos os .zip da página `https://portal.inmet.gov.br/dadoshistoricos`. '''

        dp = data_processing.DataProcessing(self.temp_path, self.appData)

        if self.appData['is_historial_concluded']:
            dp.update_estacoes()
            return

        page_url = 'https://portal.inmet.gov.br/dadoshistoricos'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'}
        html_page = requests.get(page_url, headers=headers)

        soup = BeautifulSoup(html_page.content, 'html.parser')
        zips = soup.find_all('article', {'class': 'post-preview'})

        pub.sendMessage('update-overall-gauge-maximum-value', value=len(zips))
        
        i = 1
        for zip in zips:
            if self.isActive:
                url = zip.a['href']
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




