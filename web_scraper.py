import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


class Scraper():
    def __init__(self):
        DRIVER_WIN_PATH = 'chromedriver.exe'
        if not os.path.exists('files'):
            os.mkdir('files')

        # No futuro, quando darmos deploy, não precisaremos iniciar o Chrome com janelas.
        # options = Options()
        # options.headless = True
        # options.add_argument("--window-size=1920,1200")
        # driver = webdriver.Chrome(options=options, executable_path=DRIVER_WIN_PATH)

        self.driver = webdriver.Chrome(executable_path=DRIVER_WIN_PATH)
        self.dados_historicos_inmet()

    def dados_historicos_inmet(self):
        '''Faz o download dos .zip de 2000 até o último ano completo.
        Se a pasta 'files/inmet' já existir, não faz nada'''

        if not os.path.exists('files/inmet'):
            os.mkdir('files/inmet')
        else:
            return

        self.driver.get('https://portal.inmet.gov.br/dadoshistoricos')
        elements = self.driver.find_elements(By.TAG_NAME, "article")
        for link in elements:
            if link.text.find('AUTO') != -1:
                tag = link.find_element(By.TAG_NAME, 'a')
                url = tag.get_attribute('href')
                year = link.text.split(' ')[1]
                r = requests.get(url)
                with open(f"files/inmet/{year}.zip", 'wb') as f:
                    f.write(r.content)