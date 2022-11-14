import os
from wx import CallAfter
import zipfile
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import timedelta, date
import requests
from pubsub import pub

import file_manager

# O nome e a posição das colunas dos dados históricos e das estações são diferentes!
# Esse dicionário vai nos auxiliar para pegar um determinado dado nas duas tabelas.
# lista[0] -> Colunas como estão nos dados históricos.
# lista[1] -> Colunas como estão nos dados das estações (json).
d_dic = {
    "Data": ['DATA (YYYY-MM-DD)', 'DT_MEDICAO'],
    "Hora": ['HORA (UTC)', 'HR_MEDICAO'],
    "Chuva": ['PRECIPITAÇÃO TOTAL, HORÁRIO (mm)', 'CHUVA'],
    "Pressao": ['PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)', 'PRE_INS'],
    "Radiacao": ['RADIACAO GLOBAL (KJ/m²)', 'RAD_GLO'],
    "Temperatura": ['TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)', 'TEM_INS'],
    "Umidade": ['UMIDADE RELATIVA DO AR, HORARIA (%)', 'UMD_INS']
}

# Alguém de lá teve a brilhante ideia de modificar o nome das colunas e a formatação dos
# dados a partir de 2019.
d_dic_2019 = {
    "Data": ['Data', 'DT_MEDICAO'],
    "Hora": ['Hora UTC', 'HR_MEDICAO'],
    "Chuva": ['PRECIPITAÇÃO TOTAL, HORÁRIO (mm)', 'CHUVA'],
    "Pressao": ['PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)', 'PRE_INS'],
    "Radiacao": ['RADIACAO GLOBAL (Kj/m²)', 'RAD_GLO'],
    "Temperatura": ['TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)', 'TEM_INS'],
    "Umidade": ['UMIDADE RELATIVA DO AR, HORARIA (%)', 'UMD_INS']
}


class DataProcessing:
    def __init__(self, app_data):
        self.app_data = app_data
        
        self.home = Path.home()
        self.app_folder = os.path.join(Path.home(), '4waTT')
        self.historical_folder = os.path.join(self.app_folder, 'dados_historicos')
        self.concat_folder = os.path.join(self.app_folder, 'dados_concatenados')

        self.stations = {}

    def replace_comma(self, number: str | float) -> float | str:
        """ Retorna a string `number` com a vírgula substituída por um ponto. """

        if isinstance(number, str):
            new_number = number.replace(',', '.')
            return new_number

        return number

    def convert_to_quilowatt(self, number: float | int | str) -> float | str:
        """ Converte kJ/m² para kWh/m². Se o campo estiver vazio, retorna uma string vazia. """

        if isinstance(number, float):
            return number / 3600
        else:
            return ''

    def convert_to_hour(self, n: str) -> str:
        ''' Recebe uma str da hora no formato '0', '100', '200', ..., '2200', '2300'
        e retorna no formato HH:MM. '''

        n = str(n)
        size = len(n)

        if size == 1:
            return '00:00'
        elif size < 4:
            s = '0' + n
            return s[:2] + ':00'
        else:
            return n[:2] + ':00'

    def convert_to_hour_2019(self, n: str) -> str:
        ''' Recebe uma str da hora no formato '0000 UTC', '0100 UTC', '0200 UTC', ..., '2200 UTC', '2300 UTC' 
        e retorna no formato HH:MM. '''

        n = n.split()[0]
        return n[:2] + ':' + '00'

    def clip_number(self, number: float) -> float | str:
        """ Se `number` for menor que 30, retorna uma string vazia. """

        if number < 30:
            return ''
        else:
            return number

    def concat_dados_historicos(self, stations: list):
        ''' Concatena os dados históricos das estações em `stations` para que todas elas estejam em 
        um arquivo só. '''

        isIt2019 = False

        files = os.listdir(self.historical_folder)
        zips_size = len(files)

        pub.sendMessage('update-size-text', text='')
        pub.sendMessage('update-speed-text', text='')
        pub.sendMessage('update-overall-gauge-range', value=zips_size)
        pub.sendMessage('update-overall-gauge', value=0)

        files.sort()

        zip_count = 0
        for file in files:
            # Para cada path de um zip, vamos coletar o path de todos os .csv contidos
            # dentro dele.
            zip = zipfile.ZipFile(os.path.join(self.historical_folder, file))
            f_list = zip.namelist()
            csv_list = [csv for csv in f_list if csv.endswith('.CSV')]

            # Verificamos se o ano é 2019 ou posterior. A formatação dos .csv é diferente.
            ano = int(zip.filename.split('\\')[-1].split('.')[0])
            if ano >= 2019:
                isIt2019 = True
            
            pub.sendMessage('update-overall-text', text=f"Concatenando arquivos históricos do ano {ano}...")
            pub.sendMessage('update-current-gauge-range', value=len(csv_list))
            pub.sendMessage('update-current-gauge', value=0)

            current_csv_count = 0
            for csv in csv_list:
                # Capturamos apenas o nome da estação.
                estacao = csv.split('_')[3]

                pub.sendMessage('update-file-text', text=f"Processando estação {estacao}...")
                if isIt2019:
                    dic = d_dic_2019
                else:
                    dic = d_dic

                # Vamos transformá-lo em um data frame de Pandas. Estamos ignorando as oito
                # primeiras linhas, pois elas atrapalham o Pandas a identificar onde começam o headers.
                csv_obj = zip.open(csv)
                df1 = pd.read_csv(csv_obj, encoding='latin-1', skiprows=8, delimiter=';')

                # Aqui, vamos usar o nome de columas as colunas de interesse para dropar todo o resto.
                drop_except = [x[0] for x in dic.values()]
                df = df1.filter(drop_except)

                # Agora, vamos renomear todas as columas para um nome mais conciso, para usar em todo os data frames.
                df = df.rename(columns={dic['Data'][0]: 'Data', dic['Hora'][0]: 'Hora', dic['Radiacao'][0]: 'Radiacao',
                    dic['Chuva'][0]: 'Chuva', dic['Pressao'][0]: 'Pressao', dic['Temperatura'][0]: 'Temperatura',
                    dic['Umidade'][0]: 'Umidade'})

                df['Umidade'] = df['Umidade'].astype(str)

                if isIt2019:
                    input_date = '%Y/%M/%d'
                    output_date = '%Y-%M-%d'
                    df['Data'] = pd.to_datetime(df['Data'], format=input_date).dt.strftime(output_date)
                    df['Hora'] = df['Hora'].apply(lambda x: self.convert_to_hour_2019(x))

                # Se um .csv já está na pasta de downloads, vamos concatená-lo.
                file = os.path.join(self.concat_folder, f"{estacao}.csv")
                if os.path.isfile(file):
                    on_disk = pd.read_csv(file, dtype={'Chuva': object, 'Pressao': object, 
                    'Radiacao': object, 'Temperatura': object, 'Umidade': object})

                    concated_df = pd.concat([on_disk, df], ignore_index=True)
                    concated_df.to_csv(file, index=False)
                
                # Se não, vamos criar uma nova entrada com o nome da estação como chave e o DataFrame como valor.
                # Assim, quando processarmos o próximo .zip, ele será concatenado com seu DataFrame antecessor.
                else:
                    df.to_csv(file, index=False)

                current_csv_count += 1
                pub.sendMessage('update-current-gauge', value=current_csv_count)

            zip_count += 1
            pub.sendMessage('update-overall-gauge', value=zip_count)

    def update_estacoes(self):
        ''' Esta função só deve ser chamada quando todos os dados históricos já estiverem baixados e concatenados. 
        Acessa o site do INMET pela API e baixa todos os dados faltantes desde a última entrada nos .csv
        salvos na pasta documenttos até o dia anterior. '''
        
        pub.sendMessage('OnUpdateTransferSpeed', text=['', ''])
        pub.sendMessage('update-overall-gauge', value=0)
        pub.sendMessage('update-current-gauge', value=0)

        pub.sendMessage('update-filename', text='')
        pub.sendMessage('update-page-info', text="Atualizando os arquivos com dados mais recentes...")

        csv_count = 0

        number_of_csvs = len(os.listdir(self.concat_folder))
        pub.sendMessage('update-current-gauge-maximum-value', value=number_of_csvs)

        for csv in os.listdir(self.concat_folder):
            estacao = csv
            pub.sendMessage('update-filename', text=f"Atualizando estação {estacao.split('.')[0]}...")

            csv_path = os.path.join(self.concat_folder, csv)
            df = pd.read_csv(csv_path, delimiter=',', dtype={'Chuva': object, 'Pressao': object, 
            'Radiacao': object, 'Temperatura': object, 'Umidade': object})

            ld = df['Data'].iloc[-1].split('-')
            last = date(int(ld[0]), int(ld[1]), int(ld[2]))
            last += timedelta(days=1)
            last_str = f"{last.year}-{last.month}-{last.day}"

            yesterday = date.today() - timedelta(days=1)
            yesterday_str = f"{yesterday.year}-{yesterday.month}-{yesterday.day}"

            # Se o intervalo entre a último data e o dia anterior for menor que um dia,
            # não precisamos atualizar este .csv.
            if not yesterday - last >= timedelta(days=1):
                CallAfter(pub.sendMessage, topicName='log-text', text=f"O arquivo {csv} não precisou ser modificado, pois já está atualizado.")
                csv_count += 1
                CallAfter(pub.sendMessage, topicName='update-current-gauge', value=csv_count)
                continue

            # Formato da API: https://apitempo.inmet.gov.br/estacao/<data_inicial>/<data_final>/<cod_estacao>
            # Manual: https://portal.inmet.gov.br/manual/manual-de-uso-da-api-esta%C3%A7%C3%B5es
            request = f"https://apitempo.inmet.gov.br/estacao/{last_str}/{yesterday_str}/{estacao.split('.')[0]}"
            data = self.get_estacao_csv(request)
            if not data:
                CallAfter(pub.sendMessage, topicName='log-text', text=f"Falha ao baixar dados da estação {estacao.split('.')[0]}.", isError=True)
                csv_count += 1
                CallAfter(pub.sendMessage, topicName='update-current-gauge', value=csv_count)
                continue

            json_df = pd.DataFrame(data)

            drop_except = [x[1] for x in d_dic.values()]
            json_df = json_df.filter(drop_except)

            json_df = json_df.rename(columns={d_dic['Data'][1]: 'Data', d_dic['Hora'][1]: 'Hora', d_dic['Radiacao'][1]: 'Radiacao',
                d_dic['Chuva'][1]: 'Chuva', d_dic['Pressao'][1]: 'Pressao', d_dic['Temperatura'][1]: 'Temperatura',
                d_dic['Umidade'][1]: 'Umidade'})

            json_df['Hora'] = json_df['Hora'].apply(lambda x: self.convert_to_hour_2019(x))

            new_df = pd.concat([df, json_df], ignore_index=True)
            new_df.to_csv(csv_path, index=False)

            csv_count += 1
            CallAfter(pub.sendMessage, topicName='update-current-gauge', value=csv_count)

        CallAfter(pub.sendMessage, topicName='update-filename', text=f"Processamento concluído!")

    def get_estacao_csv(self, url: str) -> str | None:
        ''' Faz uma requisição a API do INMET solicitando dados de uma determinada estação
        em um certo período de tempo. '''
        try:
            r = requests.get(url)
            return r.json()
        except:
            return None

    def do_data_cleaning(self):
        """ Remove os valores negativos e NaN dos .csv e substitui para 0. """

        for csv in os.listdir(self.docsPath)[:1]:
            path = os.path.join(self.docsPath, csv)
            
            df = pd.read_csv(path, parse_dates=['Data'])

            df['Hora'] = pd.to_datetime(df['Hora']).dt.time

            # Normalizando NaN para -9999 para ficar em par com o resto do .csv.
            df['Chuva'].fillna(-9999, inplace=True)
            df['Pressao'].fillna(-9999, inplace=True)
            df['Radiacao'].fillna(-9999, inplace=True)
            df['Temperatura'].fillna(-9999, inplace=True)
            df['Umidade'].fillna(-9999, inplace=True)


            only_in = [x for x in d_dic.keys()][2:]
            # Transformando-os todos para float.
            for column in only_in:
                df[column] = df[column].apply(lambda x: self.replace_comma(x))
                df[column] = df[column].astype(float)

            # Não podemos colocar 0 em colunas onde há dados inválidos. Os dados podem não existir por
            # erro de equipamento. Ex: Se choveu em determinado dia e houve erro ou manutenção, não podemos
            # substituí-lo por 0.

            # Quando encontrarmos ocorrências de -9999, presumimos que os dados são inválido e / ou
            # não foram coletados. Vamos deixá-los vazios para não confundir os modelos.
            df['Temperatura'] = df['Temperatura'].apply(lambda x: self.clip_number(x))
            df['Umidade'] = df['Umidade'].apply(lambda x: self.clip_number(x))
            df['Radiacao'] = df['Radiacao'].apply(lambda x: self.clip_number(x))
            df['Chuva'] = df['Chuva'].apply(lambda x: self.clip_number(x))
            df['Pressao'] = df['Pressao'].apply(lambda x: self.clip_number(x))

            # Antes de continuar, vamos converter kJ/m² para kWh/m².
            df['Radiacao'] = df['Radiacao'].apply(lambda x: self.convert_to_quilowatt(x))

            # Vamos, vamos dropar linhas onde não existam dados válidos para radiação,
            # não importa o período do dia. Afinal, Radiação é nosso target.
            df.drop(df[df.Radiacao == ''].index, inplace=True)

            df.to_csv('/home/leandro/Desktop/test.csv', index=False)

    def _populate_stations(self, zip):
        """ Forma a base de dados das estações. É usada para a pesquisa. """

        f_list = zip.namelist()
        csv_list = [csv for csv in f_list if csv.endswith('.CSV')]
