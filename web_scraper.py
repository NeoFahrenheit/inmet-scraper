import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from pubsub import pub

import downloader

class Scraper():
    def __init__(self, app_data):
        self.app_folder = os.path.join(Path.home(), '4waTT')
        self.historical_folder = os.path.join(self.app_folder, 'dados_historicos')
        self.app_data = app_data

    def download_dados_inmet(self):
        ''' Faz o download de todos os .zip da página `https://portal.inmet.gov.br/dadoshistoricos`. 
        Não baixa arquivos já existentes. '''

        page_url = 'https://portal.inmet.gov.br/dadoshistoricos'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'}
        try:
            html_page = requests.get(page_url, headers=headers)
        except:
            raise Exception('Could not communicate with the host.')

        soup = BeautifulSoup(html_page.content, 'html.parser')        
        zips = soup.find_all('article', {'class': 'post-preview'})
        last_on_zip = self.check_partial_zip(zips)

        for zip in zips:
            url = zip.a['href']
            filename = os.path.basename(url)
            path = os.path.join(self.historical_folder, filename)

            # Se o arquivo não existe, vamos baixá-lo.
            if not os.path.isfile(path):
                dl_thread = downloader.DownloadThread(self, path, url)
                dl_thread.join() # Apenas um download por vez. Tentar evitar block por IP.

        # Apenas no final, quando tivermos certeza que todos os arquivos foram baixados,
        # é seguro atualizar 'last_zip_date' no arquivo, se necessário.
        if last_on_zip != '':
            self.app_data['last_zip_date'] = last_on_zip
            pub.sendMessage('save-file')

    def check_partial_zip(self, zips: list) -> bool:
        """ Nos dados históricos, a pasta zip do último ano é sempre parcial, ou seja, 
        contém os dados até determinado mês. Esta função identifica a data deste arquivo parcial 
        para detectar se ela já contém os dados do ano completos ou foi atualizada.
        `Caso sim`, esta pasta é deletada para ser baixada novamente, não aqui, e esta função 
        retorna uma string com a última data parcial encontrada. Retorna uma string vazia, caso contrário. """

        if self.app_data['last_zip_date'] == '':
            return ''

        # Qual é o ano do zip com data parcial?
        for zip in zips:
            text = zip.a.text.split('(')[1]
            text = text[:-1]    # Retirando o último parêntese.

            if text != 'AUTOMÁTICA':
                # Este text, aqui, tá no formato 'ATÉ dd-mm-yyyy'
                date = text.split('ATÉ ')[1]

                # As datas estão diferentes?
                if self.app_data['last_zip_date'] != date:
                    year = self.app_data['last_zip_date'].split('-')[2]
                    os.remove(os.path.join(self.historical_folder, f"{year}.zip"))
                    return date

        return ''