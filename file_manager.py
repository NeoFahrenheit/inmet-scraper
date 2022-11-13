import os
from pathlib import Path
import shutil

class Files:
    def __init__(self, app_data):
        self.app_data = app_data
        self.home = Path.home()
        self.app_folder = os.path.join(Path.home(), '4waTT')
        self.historical_folder = os.path.join(self.app_folder, 'dados_historicos')
        self.concat_folder = os.path.join(self.app_folder, 'dados_concatenados')

        self.check_folders()

    def clean_all(self):
        """ Deleta todas as pastas e arquivos do programa, assim como
        o arquivo de configuração. """

        shutil.rmtree(self.app_folder)
        os.remove(os.path.join(self.home, '.4waTT'))

    def check_folders(self):
        """ Verifica se todas as pastas estão presentes.
        As faltantes serão criadas novamente. """


        if not os.path.isdir(self.app_folder):
            os.mkdir(self.app_folder)
            os.mkdir(self.historical_folder)
            os.mkdir(self.concat_folder)

        else:
            if not os.path.isdir(self.historical_folder):
                os.mkdir(self.historical_folder)

            if not os.path.isdir(self.concat_folder):
                os.mkdir(self.concat_folder)

    def check_historial_data(self, zips: list) -> bool:
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