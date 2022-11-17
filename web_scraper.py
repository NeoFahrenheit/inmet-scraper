import os
from wx import CallAfter
from threading import Thread
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from pubsub import pub

import download_thread
import file_manager

class Scraper(Thread):
    def __init__(self, parent, app_data, call_after: list):
        Thread.__init__(self)
        self.main_frame = parent
        self.is_downloading = False
        self.call_after = call_after

        self.app_folder = os.path.join(Path.home(), '4waTT')
        self.historical_folder = os.path.join(self.app_folder, 'dados_historicos')
        self.app_data = app_data

        self.file_manager = file_manager.Files(self.app_data)
        self.start()

    def run(self):
        self.download_dados_inmet()

    def download_dados_inmet(self):
        ''' Faz o download de todos os .zip da página `https://portal.inmet.gov.br/dadoshistoricos`. 
        Não baixa arquivos já existentes. '''

        self.is_downloading = True
        
        page_url = 'https://portal.inmet.gov.br/dadoshistoricos'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'}
        try:
            html_page = requests.get(page_url, headers=headers)
        except:
            raise Exception('Could not communicate with the host.')

        soup = BeautifulSoup(html_page.content, 'html.parser')        
        zips = soup.find_all('article', {'class': 'post-preview'})
        last_on_zip = self.file_manager.check_historial_data(zips)

        # Comunica o frame principal sobre as características deste download.
        self.main_frame.on_clear_progress()
        self.main_frame.overall_gauge.SetRange(len(zips))
        self.main_frame.overall_text.SetLabel('Baixando dados históricos...')

        zip_count = 0
        for zip in zips:
            url = zip.a['href']
            filename = os.path.basename(url)
            path = os.path.join(self.historical_folder, filename)
            self.main_frame.file_text.SetLabel(filename)

            # Se o arquivo não existe, vamos baixá-lo.
            if not os.path.isfile(path):
                self.main_frame.current_gauge.SetValue(0)

                try:
                    dl_thread = download_thread.DownloadThread(path, url)
                    dl_thread.join() # Apenas um download por vez. Tentar evitar block por IP.
                    CallAfter(pub.sendMessage, topicName='log', text=f"Arquivo {filename} baixado com sucesso.")
                except:
                    if os.path.isfile(path):
                        os.remove(path)
                    
                    CallAfter(pub.sendMessage, topicName='log', 
                    text=f'Erro ao baixar arquivo histórico {filename}. Abortando operação...', 
                    isError=True)
                    break

            zip_count += 1
            self.main_frame.overall_gauge.SetValue(zip_count)

        # Apenas no final, quando tivermos certeza que todos os arquivos foram baixados,
        # é seguro atualizar 'last_zip_date' no arquivo, se necessário.
        self.app_data['last_zip_date'] = last_on_zip
        pub.sendMessage('save-file')

        # self.main_frame.on_clean_progress()
        # self.main_frame.progress_sizer.ShowItems(False)
        # self.main_frame.info_sizer.Layout()

        self.is_downloading = False
        pub.sendMessage('save-file')

        # Chama as funções que deverão ser chamadas após o download dos dados históricos.
        # Eu não posso dar .join() neste thread, pois vai bloquear a GUI. Se o usuário quer atualizar tudo,
        # tenho que dar um jeito de chamar essas funções aqui.

        self.call_after()
        self.main_frame.on_clear_progress()
        pub.sendMessage('set-processing-being-done', value=False)