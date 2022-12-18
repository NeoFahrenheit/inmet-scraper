import os
from pathlib import Path
import shutil
import zipfile
from pubsub import pub

class Files:
    def __init__(self, app_data):
        self.app_data = app_data

        self.home = Path.home()
        self.app_folder = os.path.join(Path.home(), '4waTT')
        self.historical_folder = os.path.join(self.app_folder, 'dados_historicos')

        self.check_folders()

    def clean_all(self, delete_config_file: bool = True):
        """ Deleta todas as pastas e arquivos do programa, assim como
        o arquivo de configuração. """

        shutil.rmtree(self.app_folder)
        if delete_config_file:
            path = os.path.join(self.home, '.4waTT.json')

            if os.path.isfile(path):
                self.app_data.clear()
                os.remove(path)

    def check_folders(self):
        """ Verifica se todas as pastas estão presentes.
        As faltantes serão criadas novamente. """

        if not os.path.isdir(self.app_folder):
            os.mkdir(self.app_folder)
            os.mkdir(self.historical_folder)

        else:
            if not os.path.isdir(self.historical_folder):
                os.mkdir(self.historical_folder)

    def check_historial_data(self, zips: list) -> str:
        """ Nos dados históricos, a pasta zip do último ano é sempre parcial, ou seja, 
        contém os dados até determinado mês. Esta função identifica a data deste arquivo parcial 
        para detectar se ela já contém os dados do ano completo ou foi atualizada.
        `Caso sim`, esta pasta é deletada para ser baixada novamente (não baixa aqui), e retorna 
        uma string com a última data parcial encontrada. """

        # Se self.app_data['last_zip_date'] for vazia, só vamos colocar a data do arquivo parcial e sair.

        # Qual é o ano do zip com data parcial?
        for zip in zips:
            text = zip.a.text.split('(')[1]
            text = text[:-1]    # Retirando o último parêntese.

            if text != 'AUTOMÁTICA':
                # Este text, aqui, tá no formato 'ATÉ dd-mm-yyyy'
                date = text.split('ATÉ ')[1]

                # As datas estão diferentes?
                if self.app_data['last_zip_date'] != '':
                    if self.app_data['last_zip_date'] != date:
                        year = self.app_data['last_zip_date'].split('-')[2]
                        os.remove(os.path.join(self.historical_folder, f"{year}.zip"))
                        return date
                else:
                    return date
    
    def get_stations_list(self):
        """ Usa o último zip dos dados históricos para formar a base de dados 
        das estações que será usada para pesquisa. """

        files = os.listdir(self.historical_folder)
        zip = zipfile.ZipFile(os.path.join(self.historical_folder, files[-1]))
        f_list = zip.namelist()
        csv_list = [csv for csv in f_list if csv.endswith('.CSV')]

        stations = {}
        for csv_zip in csv_list:
            text = zip.open(csv_zip).readlines()

            d = {}
            for line in text[:8]:
                key, value = str(line, 'latin-1').split(';')
                key = key.strip()
                value = value.strip()

                d[key] = value

            d['name'] = f"{d['CODIGO (WMO):']} {d['ESTACAO:']}"
            stations[d['CODIGO (WMO):']] = d

        self.app_data['stations'] = stations
        
        pub.sendMessage('save-file')
        pub.sendMessage('update-combos')
            
