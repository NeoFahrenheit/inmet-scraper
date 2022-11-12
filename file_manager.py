import os
from pathlib import Path
import shutil
import web_scraper

class Files:
    def __init__(self):
        self.home = Path.home()
        self.app_folder = os.path.join(Path.home(), '4waTT')
        historical = os.path.join(self.app_folder, 'dados_historicos')
        concat = os.path.join(self.app_folder, 'dados_concatenados')

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
            os.mkdir(historical)
            os.mkdir(concat)

        else:
            if not os.path.isdir(historical):
                os.mkdir(historical)

            if not os.path.isdir(concat):
                os.mkdir(concat)

    def check_historial_data(self) -> bool:
        """ Analisa a pasta '4waTT/historical_data' e verifica se 
        há arquivos para serem baixados. Retorna false se não conseguir acesso ao host. """