import os
import zipfile
import pandas as pd

from downloader import DownloadThread

# O nome e a posição das colunas dos dados históricos e das estações são diferentes!
# Esse dicionário vai nos auxiliar para pegar um determinado dado nas duas tabelas.
# lista[0] -> Colunas como estão nos dados históricos.
# lista[1] -> Colunas como estão nos dados das estações.
d_dic = {
    "Data": ['DATA (YYYY-MM-DD)', 'Data'],
    "Hora": ['HORA (UTC)', 'Hora (UTC)'],
    "Chuva": ['PRECIPITAÇÃO TOTAL, HORÁRIO (mm)', 'Chuva (mm)'],
    "Pressao": ['PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)', 'Pressao Ins. (hPa)'],
    "Radiacao": ['RADIACAO GLOBAL (KJ/m²)', 'Radiacao (KJ/m²)'],
    "Temperatura": ['TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)', 'Temp. Ins. (C)'],
    "Umidade": ['UMIDADE RELATIVA DO AR, HORARIA (%)', 'Umi. Ins. (%)']
}

# Alguém de lá teve a brilhante ideia de modificar o nome das colunas e a formatação dos
# dados a partir de 2019.
d_dic_2019 = {
    "Data": ['Data', 'Data'],
    "Hora": ['Hora UTC', 'Hora (UTC)'],
    "Chuva": ['PRECIPITAÇÃO TOTAL, HORÁRIO (mm)', 'Chuva (mm)'],
    "Pressao": ['PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)', 'Pressao Ins. (hPa)'],
    "Radiacao": ['RADIACAO GLOBAL (Kj/m²)', 'Radiacao (KJ/m²)'],
    "Temperatura": ['TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)', 'Temp. Ins. (C)'],
    "Umidade": ['UMIDADE RELATIVA DO AR, HORARIA (%)', 'Umi. Ins. (%)']
}

class DataProcessing():
    def __init__(self, files_path, appData):
        self.path = files_path  # Local dos arquivos baixados em /Temp
        self.appData = appData
        self.docsPath = os.path.expanduser('~/Documents/4watt')

    def convertToHour(self, n: str) -> str:
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

    def convertToHour_2019(self, n: str) -> str:
        ''' Recebe uma str da hora no formato '0000 UTC', '0100 UTC', '0200 UTC', ..., '2200 UTC', '2300 UTC' 
        e retorna no formato HH:MM. '''

        n = n.split()[0]
        return n[:2] + ':' + '00'

    def concat_dados_historicos(self, files):
        ''' Concatena os dados históricos para que todas as estações estejam em 
        um arquivo só. Usado para dados históricos para o 2019 e posteriores.'''

        station_dic = {}
        isIt2019 = False

        # files contém o path para todos os zips baixados.
        for file in files:

            # Para cada path de um zip, vamos coletar o path de todos os .csv contidos
            # dentro dele.
            zip = zipfile.ZipFile(file)
            f_list = zip.namelist()
            csv_list = [csv for csv in f_list if csv.endswith('.CSV')]

            # Verificamos se o ano é 2019 ou posterior. A formatação dos .csv é diferente.
            ano = int(zip.filename.split('/')[-1].split('.')[0])
            if ano >= 2019:
                isIt2019 = True
            
            csv_lengh = len(csv_list)
            count = 0

            # Para cada path de um .csv dentro daquele zip...
            for csv in csv_list:
                if isIt2019:
                    dic = d_dic_2019
                else:
                    dic = d_dic

                # Vamos transformá-lo em um data frame de Pandas. Estamos ignorando as oito
                # primeiras linhas, pois elas atrapalham o Pandas a identificar onde começam os headers.
                csv_obj = zip.open(csv)
                df1 = pd.read_csv(csv_obj, encoding='latin-1', skiprows=8, delimiter=';')

                # Aqui, vamos usar o nome de columas as colunas de interesse para dropar todo o resto.
                filter = [x[0] for x in dic.values()]
                df = df1.filter(filter)

                # Agora, vamos renomear todas as columas para um nome mais conciso, para usar em todo os data frames.
                df = df.rename(columns={dic['Data'][0]: 'Data', dic['Hora'][0]: 'Hora', dic['Radiacao'][0]: 'Radiacao',
                    dic['Chuva'][0]: 'Chuva', dic['Pressao'][0]: 'Pressao', dic['Temperatura'][0]: 'Temperatura',
                    dic['Umidade'][0]: 'Umidade'})

                df['Umidade'] = df['Umidade'].astype(str)

                if isIt2019:
                    input_date = '%Y/%M/%d'
                    output_date = '%Y-%M-%d'
                    df['Data'] = pd.to_datetime(df['Data'], format=input_date).dt.strftime(output_date)
                    df['Hora'] = df['Hora'].apply(lambda x: self.convertToHour_2019(x))

                # Capturamos apenas o nome da estação.
                estacao = csv.split('_')[3]

                # Se um data frame já está contido no dicionário de DataFrames, vamos concatená-lo.
                if estacao in station_dic:
                    station_dic[estacao] = pd.concat([station_dic[estacao], df], ignore_index=True)
                
                # Se não, vamos criar uma nova entrada com o nome da estação como chave e o DataFrame como valor.
                # Assim, quando processarmos o próximo .zip, ele será concatenado com seu DataFrame antecessor.
                else:
                    station_dic[estacao] = df

                count += 1
                print(f"Processando {file.split('/')[-1]}, estação {estacao}.\t{count} of {csv_lengh}...")

        # Agora, só precisamos salvar todos os DataFrames no disco. Cuidado com sua RAM.
        for key, value in station_dic.items():
            print(f"Escrevendo {key}.csv no disco...")
            value.to_csv(f"{self.docsPath}/{key}.csv", index=False)

    def update_estacoes(self, path):
        ''' Esta função só deve ser chamada quando todos os dados históricos já estiverem baixados. 
        Acessa o site do INMET pela API e baixa todos os dados faltantes desde a última entrada nos .csv
        salvos na pasta documenttos até o dia anterior. '''

        # file_estacao =  open('../estacao.csv')
        # df2 = pd.read_csv(file_estacao, delimiter=';')

        # filter = [x[1] for x in d_dic.values()]
        # df2 = df2.filter(filter)
        # df2 = df2.rename(columns={d_dic['Data'][1]: 'Data', d_dic['Hora'][1]: 'Hora', d_dic['Radiacao'][1]: 'Radiacao',
        #     d_dic['Chuva'][1]: 'Chuva', d_dic['Pressao'][1]: 'Pressao', d_dic['Temperatura'][1]: 'Temperatura',
        #     d_dic['Umidade'][1]: 'Umidade'})

        # input_date = '%d/%M/%Y'
        # output_date = '%Y-%M-%d'
        # df2['Data'] = pd.to_datetime(df2['Data'], format=input_date).dt.strftime(output_date)

        # df2['Hora'] = df2['Hora'].apply(lambda x: self.convertToHour(x))

        # print(df2.head())
        # pd.concat([df1, df2], ignore_index=True).to_csv('test.csv', index=False)

        # file_estacao.close()



import tempfile
temp_path = f"{tempfile.gettempdir()}/4watt"

files = os.listdir(temp_path)
for i in range (0, len(files)):
    files[i] = f"{temp_path}/{files[i]}"

dp = DataProcessing(files, {})
dp.concat_dados_historicos(files)