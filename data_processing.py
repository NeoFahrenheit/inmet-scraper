import os
from wx import CallAfter, Yield
import zipfile
from pathlib import Path
import pandas as pd
import numpy as np
from pubsub import pub
from datetime import datetime

from id import d_dic, d_dic_2019, d_dic_2020_greater

class DataProcessing:
    def __init__(self, app_data):
        self.app_data = app_data
        
        self.home = Path.home()
        self.app_folder = os.path.join(Path.home(), 'inmet')
        self.historical_folder = os.path.join(self.app_folder, 'dados_historicos')

        self.stations = {}

    def replace_comma(self, number: str | float) -> float | str:
        """ Retorna a string `number` com a vírgula substituída por um ponto. """

        if isinstance(number, str):
            new_number = number.replace(',', '.')
            return new_number
        
        return number

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

    def convert_to_hour_2020(self, n: str) -> str:
        ''' Recebe uma str da hora no formato '0000 UTC', '0100 UTC', '0200 UTC', ..., '2200 UTC', '2300 UTC' 
        e retorna no formato HH:MM. '''

        n = n.split()[0]
        return n[:2] + ':' + '00'

    def convert_date(self, n: str) -> str:
        """ Recebe uma data do tipo DD/MM/YYYY e devolve uma do tipo YYYY-MM-DD. """

        return datetime.strptime(n, '%d/%M/%Y').strftime('%Y-%M-%d')

    def clip_number(self, number: float) -> float | str:
        """ Se `number` for menor que 30, retorna uma string vazia. """

        if number < 30:
            return ''
        else:
            return number

    def count_sequent_invalid_data(self, df, column):
        ''' Conta dados menores que -100 que estão um após o outro, sequencialmente. Ignora o primeiro. '''
        count = 0
        size = len(df.index)

        for i in range(0, size):
            if df[column].iloc[i] < -100:
                if i + 1 < size and df[column].iloc[i + 1] < -100:
                    count += 1

        return count

    def count_total_invalid_data(self, df, column):
        ''' Conta dados menores que -100, não importa como e de que jeito apareçam. '''
        
        count = 0
        size = len(df.index)

        for i in range(0, size):
            if df[column].iloc[i] < -100:
                count += 1

        return count

    def drop_sequent_data(self, df, column):
        ''' Dropa os dados inválidos seguidos. '''

        size = len(df.index)
        to_drop = []
        for i in range(0, size):
            if df[column].iloc[i] < -100:
                if i + 1 < size and df[column].iloc[i + 1] < -100:
                    to_drop.append(i + 1)
        
        df.drop(df.index[to_drop], inplace=True)

    def substitute(self, x):
        " Se x for menor que -100, retorna `np.NaN`. "

        if x < -100:
            return np.NaN
        else:
            return x

    def replace_negative_nan(self, df, column):
        ''' Substitui valores menores que -100 por NaN. '''

        df[column] = df[column].apply(lambda x: self.substitute(x))

    def concat_dados_historicos(self, stations: list):
        ''' Concatena os dados históricos das estações em `stations` para que todas elas estejam em 
        um arquivo só. '''

        isIt2020orGreater = False
        isIt2019 = False

        files = os.listdir(self.historical_folder)
        station_lenght = len(stations)

        year_count = 0
        pub.sendMessage('clean-progress')
        pub.sendMessage('update-overall-gauge-range', value=len(files) -1)
        pub.sendMessage('update-current-gauge-range', value=station_lenght)
        files.sort()

        for file in files:
            # Para cada path de um zip, vamos coletar o path de todos os .csv contidos
            # dentro dele.
            try:
                zip = zipfile.ZipFile(os.path.join(self.historical_folder, file))
                f_list = zip.namelist()
                csv_list = [csv for csv in f_list if csv.endswith('.CSV')]
            except:
                CallAfter(pub.sendMessage, topicName='log', text=f'Falha ao abrir {file}. O arquivo está corrompido ou inválido. Abortando...', isError=True)
                for estacao in stations:
                    path = os.path.join(self.app_folder, f"{estacao}.csv")
                    if os.path.isfile(path):
                        os.remove(path)

                return stations.clear()

            # Verificamos se o ano é 2020 ou posterior. A formatação dos .csv é diferente.
            ano = int(zip.filename.split('\\')[-1].split('.')[0])
            if ano >= 2020:
                isIt2020orGreater = True

            if ano == 2019:
                isIt2019 = True
            else:
                isIt2019 = False
            
            pub.sendMessage('update-overall-text', text=f"Concatenando arquivos históricos do ano {ano}...")
            
            station_count = 0
            # pub.sendMessage('update-current-gauge', value=station_count)

            for csv in csv_list:
                # Capturamos apenas o nome da estação.
                estacao = csv.split('_')[3]
                if estacao not in stations:
                    continue

                pub.sendMessage('update-file-text', text=f"Processando estação {estacao}...")
                if isIt2019:
                    dic = d_dic_2019
                elif isIt2020orGreater:
                    dic = d_dic_2020_greater
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
                dic['Pressao'][0]: 'Pressao', dic['Temperatura'][0]: 'Temperatura', dic['Umidade'][0]: 'Umidade'})

                df['Umidade'] = df['Umidade'].astype(str)

                if isIt2019 or isIt2020orGreater:
                    input_date = '%Y/%M/%d'
                    output_date = '%Y-%M-%d'
                    df['Data'] = pd.to_datetime(df['Data'], format=input_date).dt.strftime(output_date)
                    df['Hora'] = df['Hora'].apply(lambda x: self.convert_to_hour_2020(x))

                # Se um .csv já está na pasta de downloads, vamos concatená-lo.
                file = os.path.join(self.app_folder, f"{estacao}.csv")
                if os.path.isfile(file) and os.stat(file).st_size != 0:
                    on_disk = pd.read_csv(file, dtype={'Pressao': object, 
                    'Radiacao': object, 'Temperatura': object, 'Umidade': object})

                    concated_df = pd.concat([on_disk, df], ignore_index=True)
                    concated_df.to_csv(file, index=False)
                    self.app_data['saved'][estacao]['last_updated'] = concated_df['Data'].iloc[-1]
                
                # Se não, vamos criar uma nova entrada com o nome da estação como chave e o DataFrame como valor.
                # Assim, quando processarmos o próximo .zip, ele será concatenado com seu DataFrame antecessor.
                else:
                    df.to_csv(file, index=False)
                    self.app_data['saved'][estacao]['last_updated'] = df['Data'].iloc[-1]

                station_count += 1
                pub.sendMessage('update-current-gauge', value=station_count)

            year_count += 1
            pub.sendMessage('update-overall-gauge', value=year_count)

    def do_data_cleaning(self, stations: list):
        """ Faz a limpeza dos dados das estações presentes em `stations`. Se houver algum erro, a estação 
        é removida de `stations`. """

        CallAfter(pub.sendMessage, topicName='update-overall-text', text='Limpando os dados...')
        CallAfter(pub.sendMessage, topicName='update-current-gauge-range', value=len(stations))

        clean_count = 1
        for csv in stations:
            path = os.path.join(self.app_folder, f"{csv}.csv")
            CallAfter(pub.sendMessage, topicName='update-file-text', text=f"Limpando estação {csv}")
            Yield()

            df = pd.read_csv(path, delimiter=',', dtype={'Pressao': object, 'Radiacao': object, 'Temperatura': object, 'Umidade': object})

            # df['Hora'] = pd.to_datetime(df['Hora']).dt.time       # Não é necessário se vamos salvar em um arquivo.

            # Normalizando NaN para -9999 para ficar em par com o resto do .csv.
            df['Pressao'].fillna(-9999, inplace=True)
            df['Radiacao'].fillna(-9999, inplace=True)
            df['Temperatura'].fillna(-9999, inplace=True)
            df['Umidade'].fillna(-9999, inplace=True)


            # Substituindo as vírgulas por ponto para facilitar a conversão para número.
            only_in = ['Pressao', 'Radiacao', 'Temperatura', 'Umidade']
            for column in only_in:
                df[column] = df[column].apply(lambda x: self.replace_comma(x))
                df[column] = df[column].astype(float)

            # df['Hora'] = pd.to_datetime(df['Hora']).dt.time       # Não é necessário se vamos salvar em um arquivo.

            # Queremos preservar a maior quantidade de dados possível. Quando a radiação estiver -9999, há duas possibilidades.
            # 1) É um período noturno, portanto é um dado "válido". Pode ser zerado.
            # 2) Houve erro na estação.
            # Na maior parte dos casos, quando há erro na estação, todas as colunas são inválidas. Vamos dropar todas elas.
            df.drop(df[(df.Radiacao < -100) & (df.Pressao < -100) & (df.Temperatura < -100)].index, inplace=True)

            # Agora, podemos substituir os -9999 em 'Radiação" por 0.
            df.Radiacao.clip(lower=0, inplace=True)

            # Em outros casos mais isolados, apenas um instrumento se demonstra defeituoso e os demais dados da coluna podem estar corretos. 
            # Dados inválidos descritos logo abaixo são aqueles menores que -100. 
            # Apenas a coluna Radiacao acima foi zerada para valores menores que -100.

            # Podemos pensar em deletar a linha dos dados inválidos sequenciais e substituir o valor do campo inválido isolado com o dado anterior, 
            # com exceção da coluna Radiacao, que já tratamos acima. Os dados inválidos sequenciais, que são mais difícies de tratar, parecem ser poucos, 
            # o que não impactara de forma significante o nosso dataset. Agora, os dados isolados, podemos substituí-lo com o anterior. Vamos fazer isso!
            for column in only_in:
                self.drop_sequent_data(df, column)

            # Agora, vamos substituir os dados inválidos isolados pelo anterior, mas antes de usar o método ffill, 
            # precisamos transformar os números negativos em NaN primeiro.
            for column in only_in:
                self.replace_negative_nan(df, column)
            df.fillna(method='ffill', inplace=True)

            # Testando os valores mínimos.
            testing = []
            testing.append(df.Pressao.min() > - 30)
            testing.append(df.Temperatura.min() > - 30)
            testing.append(df.Umidade.min() > - 30)

            if not all(testing):
                CallAfter(pub.sendMessage, topicName='log', text=f"Erro ao limpar a estação {csv}.", isError=True)
                stations.remove(csv)
                continue

            clean_count += 1
            CallAfter(pub.sendMessage, topicName='update-current-gauge', value=clean_count)

            df.to_csv(os.path.join(self.app_folder, f"{csv}.csv"), index=False)


    def do_data_cleaning_2(self, stations: list):
        """ Faz a limpeza dos dados das estações presentes em `stations`. Se houver algum erro, a estação 
        é removida de `stations`. """

        CallAfter(pub.sendMessage, topicName='update-overall-text', text='Limpando os dados...')
        CallAfter(pub.sendMessage, topicName='update-current-gauge-range', value=len(stations))

        clean_count = 1
        for csv in stations:
            path = os.path.join(self.app_folder, f"{csv}.csv")
            CallAfter(pub.sendMessage, topicName='update-file-text', text=f"Limpando estação {csv}")
            Yield()

            df = pd.read_csv(path, delimiter=',', dtype={'Pressao': object, 'Radiacao': object, 'Temperatura': object, 'Umidade': object})

            # df['Hora'] = pd.to_datetime(df['Hora']).dt.time       # Não é necessário se vamos salvar em um arquivo.

            # Normalizando NaN para -9999 para ficar em par com o resto do .csv.
            df['Pressao'].fillna(-9999, inplace=True)
            df['Radiacao'].fillna(-9999, inplace=True)
            df['Temperatura'].fillna(-9999, inplace=True)
            df['Umidade'].fillna(-9999, inplace=True)


            # Substituindo as vírgulas por ponto para facilitar a conversão para número.
            only_in = ['Pressao', 'Radiacao', 'Temperatura', 'Umidade']
            for column in only_in:
                df[column] = df[column].apply(lambda x: self.replace_comma(x))
                df[column] = df[column].astype(float)

            # df['Hora'] = pd.to_datetime(df['Hora']).dt.time       # Não é necessário se vamos salvar em um arquivo.

            # Queremos preservar a maior quantidade de dados possível. Quando a radiação estiver -9999, há duas possibilidades.
            # 1) É um período noturno, portanto é um dado "válido". Pode ser zerado.
            # 2) Houve erro na estação.
            # Na maior parte dos casos, quando há erro na estação, todas as colunas são inválidas. Vamos dropar todas elas.
            df.drop(df[(df.Radiacao < -100) & (df.Pressao < -100) & (df.Temperatura < -100)].index, inplace=True)

            # Agora, podemos substituir os -9999 em 'Radiação" por 0.
            df.Radiacao.clip(lower=0, inplace=True)

            # Em outros casos mais isolados, apenas um instrumento se demonstra defeituoso e os demais dados da coluna podem estar corretos. 
            # Dados inválidos descritos logo abaixo são aqueles menores que -100. 
            # Apenas a coluna Radiacao acima foi zerada para valores menores que -100.

            # Podemos pensar em deletar a linha dos dados inválidos sequenciais e substituir o valor do campo inválido isolado com o dado anterior, 
            # com exceção da coluna Radiacao, que já tratamos acima. Os dados inválidos sequenciais, que são mais difícies de tratar, parecem ser poucos, 
            # o que não impactara de forma significante o nosso dataset. Agora, os dados isolados, podemos substituí-lo com o anterior. Vamos fazer isso!
            for column in only_in:
                self.drop_sequent_data(df, column)

            # Agora, vamos substituir os dados inválidos isolados pelo anterior, mas antes de usar o método ffill, 
            # precisamos transformar os números negativos em NaN primeiro.
            for column in only_in:
                self.replace_negative_nan(df, column)
            df.fillna(method='ffill', inplace=True)

            # Testando os valores mínimos.
            testing = []
            testing.append(df.Pressao.min() > - 30)
            testing.append(df.Temperatura.min() > - 30)
            testing.append(df.Umidade.min() > - 30)

            if not all(testing):
                CallAfter(pub.sendMessage, topicName='log', text=f"Erro ao limpar a estação {csv}.", isError=True)
                stations.remove(csv)
                continue

            clean_count += 1
            CallAfter(pub.sendMessage, topicName='update-current-gauge', value=clean_count)

            df.to_csv(os.path.join(self.app_folder, f"{csv}.csv"), index=False)
