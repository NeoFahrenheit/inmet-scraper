import os
from wx import CallAfter
import zipfile
import pandas as pd
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
    def __init__(self, temp_path, app_data):
        self.temp_path = temp_path  # Local dos arquivos baixados em /Temp
        self.appData = app_data
        self.docsPath = os.path.expanduser('~/Documents/4watt')

        if not os.path.isdir(self.docsPath):
            os.mkdir(self.docsPath)

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

    def concat_dados_historicos(self, temp_files):
        ''' Concatena os dados históricos para que todas as estações estejam em 
        um arquivo só. Usado para dados históricos para o 2019 e posteriores.'''

        station_dic = {}
        isIt2019 = False

        files = os.listdir(temp_files)
        zips_size = len(files)
        CallAfter(pub.sendMessage, topicName='OnUpdateTransferSpeed', text=['', ''])
        CallAfter(pub.sendMessage, topicName='update-overall-gauge', value=0)
        CallAfter(pub.sendMessage, topicName='update-overall-gauge-maximum-value', value=zips_size)

        zip_count = 0
        for file in files:
            # Para cada path de um zip, vamos coletar o path de todos os .csv contidos
            # dentro dele.
            zip = zipfile.ZipFile(f"{temp_files}/{file}")
            f_list = zip.namelist()
            csv_list = [csv for csv in f_list if csv.endswith('.CSV')]

            # Verificamos se o ano é 2019 ou posterior. A formatação dos .csv é diferente.
            ano = int(zip.filename.split('/')[-1].split('.')[0])
            if ano >= 2019:
                isIt2019 = True
            
            CallAfter(pub.sendMessage, topicName='update-page-info', text=f"Processando arquivos do ano de {ano}...")

            CallAfter(pub.sendMessage, topicName='update-current-gauge-maximum-value', value=len(csv_list))
            CallAfter(pub.sendMessage, topicName='update-current-gauge', value=0)

            current_csv_count = 0
            for csv in csv_list:
                # Capturamos apenas o nome da estação.
                estacao = csv.split('_')[3]

                CallAfter(pub.sendMessage, topicName='update-filename', text=f"Processando arquivo da estação {estacao}...")
                if isIt2019:
                    dic = d_dic_2019
                else:
                    dic = d_dic

                # Vamos transformá-lo em um data frame de Pandas. Estamos ignorando as oito
                # primeiras linhas, pois elas atrapalham o Pandas a identificar onde começam os headers.
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

                # Se um data frame já está contido no dicionário de DataFrames, vamos concatená-lo.
                if estacao in station_dic:
                    station_dic[estacao] = pd.concat([station_dic[estacao], df], ignore_index=True)
                
                # Se não, vamos criar uma nova entrada com o nome da estação como chave e o DataFrame como valor.
                # Assim, quando processarmos o próximo .zip, ele será concatenado com seu DataFrame antecessor.
                else:
                    station_dic[estacao] = df

                current_csv_count += 1
                CallAfter(pub.sendMessage, topicName='update-current-gauge', value=current_csv_count)

            zip_count += 1
            CallAfter(pub.sendMessage, topicName='update-overall-gauge', value=zip_count)

        # Agora, só precisamos salvar todos os DataFrames no disco. Cuidado com sua RAM.
        CallAfter(pub.sendMessage, topicName='update-page-info', text=f"Salvando os arquivos .csv do disco...")
        CallAfter(pub.sendMessage, topicName='update-current-gauge-maximum-value', value=len(os.listdir(self.docsPath)))
        CallAfter(pub.sendMessage, topicName='update-current-gauge', value=0)

        save_count = 0
        for key, value in station_dic.items():
            CallAfter(pub.sendMessage, topicName='update-filename', text=f"Escrevendo {key}.csv no disco...")
            value.to_csv(f"{self.docsPath}/{key}.csv", index=False)

            save_count += 1
            CallAfter(pub.sendMessage, topicName='update-current-gauge', value=save_count)

    def update_estacoes(self):
        ''' Esta função só deve ser chamada quando todos os dados históricos já estiverem baixados e concatenados. 
        Acessa o site do INMET pela API e baixa todos os dados faltantes desde a última entrada nos .csv
        salvos na pasta documenttos até o dia anterior. '''

        path = self.docsPath
        
        CallAfter(pub.sendMessage, topicName='OnUpdateTransferSpeed', text=['', ''])
        CallAfter(pub.sendMessage, topicName='update-overall-gauge', value=0)
        CallAfter(pub.sendMessage, topicName='update-current-gauge', value=0)

        CallAfter(pub.sendMessage, topicName='update-filename', text='')
        CallAfter(pub.sendMessage, topicName='update-page-info', text="Atualizando os arquivos com dados mais recentes...")

        csv_count = 0
        number_of_csvs = len(os.listdir(path))
        CallAfter(pub.sendMessage, topicName='update-current-gauge-maximum-value', value=number_of_csvs)

        for csv in os.listdir(path):
            estacao = csv
            CallAfter(pub.sendMessage, topicName='update-filename', text=f"Atualizando estação {estacao.split('.')[0]}...")

            csv_path = os.path.join(path, csv)
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