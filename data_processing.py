import os
from wx import CallAfter, Yield
import zipfile
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import timedelta, date
import requests
from pubsub import pub

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
                    path = os.path.join(self.concat_folder, f"{estacao}.csv")
                    if os.path.isfile(path):
                        os.remove(path)

                return stations.clear()

            # Verificamos se o ano é 2019 ou posterior. A formatação dos .csv é diferente.
            ano = int(zip.filename.split('\\')[-1].split('.')[0])
            if ano >= 2019:
                isIt2019 = True
            
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

                station_count += 1
                pub.sendMessage('update-current-gauge', value=station_count)

            year_count += 1
            pub.sendMessage('update-overall-gauge', value=year_count)

    def update_estacoes(self, stations) -> list:
        ''' Esta função só deve ser chamada quando todos os dados históricos já estiverem baixados e concatenados. 
        Acessa o site do INMET pela API e baixa todos os dados faltantes desde a última entrada nos .csv
        salvos na pasta documenttos até o dia anterior. Retorna a lista com as estações que atualizaram com sucesso. '''

        CallAfter(pub.sendMessage, topicName='on_clear_progress')
        CallAfter(pub.sendMessage, topicName='update-overall-text', text="Atualizando arquivos...")

        csv_count = 1

        number_of_csvs = len(stations)
        CallAfter(pub.sendMessage, topicName='update-current-gauge-range', value=number_of_csvs)

        for csv in os.listdir(self.concat_folder):
            estacao = csv
            station_key = estacao.split('.')[0] 
            if station_key not in stations:
                continue
            
            CallAfter(pub.sendMessage, topicName='update-file-text', text=f"Atualizando estação {estacao.split('.')[0]}...")
            Yield()

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
                CallAfter(pub.sendMessage, topicName='log', text=f"O arquivo {csv} não precisou ser modificado, pois já está atualizado.")
                csv_count += 1
                CallAfter(pub.sendMessage, topicName='update-current-gauge', value=csv_count)
                continue

            # Formato da API: https://apitempo.inmet.gov.br/estacao/<data_inicial>/<data_final>/<cod_estacao>
            # Manual: https://portal.inmet.gov.br/manual/manual-de-uso-da-api-esta%C3%A7%C3%B5es
            request = f"https://apitempo.inmet.gov.br/estacao/{last_str}/{yesterday_str}/{estacao.split('.')[0]}"
            data = self.get_estacao_csv(request)
            if not data:
                CallAfter(pub.sendMessage, topicName='log', text=f"Falha ao baixar dados da estação {estacao.split('.')[0]}.", isError=True)
                csv_count += 1
                CallAfter(pub.sendMessage, topicName='update-current-gauge', value=csv_count)
                stations.remove(station_key)
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
            
            self.app_data['saved'][station_key]['last_updated'] = f"{yesterday.day}-{yesterday.month}-{yesterday.year}"

            csv_count += 1
            CallAfter(pub.sendMessage, topicName='update-current-gauge', value=csv_count)


    def get_estacao_csv(self, url: str) -> str | None:
        ''' Faz uma requisição a API do INMET solicitando dados de uma determinada estação
        em um certo período de tempo. '''
        try:
            r = requests.get(url)
            return r.json()
        except:
            return None

    def do_data_cleaning(self, stations: list):
        """ Faz a limpeza dos dados das estações presentes em `stations`. Se houver algum erro, a estação 
        é removida de `stations`. """

        CallAfter(pub.sendMessage, topicName='update-overall-text', text='Limpando os dados...')
        CallAfter(pub.sendMessage, topicName='update-current-gauge-range', value=len(stations))

        clean_count = 1
        for csv in stations:
            path = os.path.join(self.concat_folder, f"{csv}.csv")
            CallAfter(pub.sendMessage, topicName='update-file-text', text=f"Limpando estação {csv}")
            Yield()

            df = pd.read_csv(path, delimiter=',', dtype={'Chuva': object, 'Pressao': object, 
            'Radiacao': object, 'Temperatura': object, 'Umidade': object})

            # df['Hora'] = pd.to_datetime(df['Hora']).dt.time       # Não é necessário se vamos salvar em um arquivo.

            # Normalizando NaN para -9999 para ficar em par com o resto do .csv.
            df['Chuva'].fillna(-9999, inplace=True)
            df['Pressao'].fillna(-9999, inplace=True)
            df['Radiacao'].fillna(-9999, inplace=True)
            df['Temperatura'].fillna(-9999, inplace=True)
            df['Umidade'].fillna(-9999, inplace=True)


            # Substituindo as vírgulas por ponto para facilitar a conversão para número.
            only_in = ['Chuva', 'Pressao', 'Radiacao', 'Temperatura', 'Umidade']
            for column in only_in:
                df[column] = df[column].apply(lambda x: self.replace_comma(x))
                df[column] = df[column].astype(float)

            # df['Hora'] = pd.to_datetime(df['Hora']).dt.time       # Não é necessário se vamos salvar em um arquivo.

            # Queremos preservar a maior quantidade de dados possível. Quando a radiação estiver -9999, há duas possibilidades.
            # 1) É um período noturno, portanto é um dado "válido". Pode ser zerado.
            # 2) Houve erro na estação.
            # Na maior parte dos casos, quando há erro na estação, todas as colunas são inválidas. Vamos dropar todas elas.
            df.drop(df[(df.Radiacao < -100) & (df.Chuva < -100) & (df.Pressao < -100) & (df.Temperatura < -100)].index, inplace=True)

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
            testing.append(df.Chuva.min() > - 30)
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

    def _populate_stations(self, zip):
        """ Forma a base de dados das estações. É usada para a pesquisa. """

        f_list = zip.namelist()
        csv_list = [csv for csv in f_list if csv.endswith('.CSV')]