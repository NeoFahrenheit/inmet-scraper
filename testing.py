import os
import zipfile
import tempfile
import pandas as pd


# home = os.path.expanduser('~/Desktop')
# for file in files[:1]:
#     zip = zipfile.ZipFile(file)
#     f_list = zip.namelist()
#     csv_list = [csv for csv in f_list if csv.endswith('.CSV')]
    
#     obj = zip.open(csv_list[0])
#     df = pd.read_csv(obj, skiprows=8, encoding='latin-1', delimiter=';')
#     print(df.head())
    




# file =  open('../historico.csv', encoding='latin-1')
# _ = [next(file) for _ in range(8)]  # Ignorar o início do .csv, já que contém apenas informações da estação.
# df1 = pd.read_csv(file, delimiter=';', quotechar='"')

# filter = [x[0] for x in d_dic.values()]
# df1 = df1.filter(filter)

# df1 = df1.rename(columns={d_dic['Data'][0]: 'Data', d_dic['Hora'][0]: 'Hora', d_dic['Radiacao'][0]: 'Radiacao',
#     d_dic['Chuva'][0]: 'Chuva', d_dic['Pressao'][0]: 'Pressao', d_dic['Temperatura'][0]: 'Temperatura',
#     d_dic['Umidade'][0]: 'Umidade'})


# df1['Umidade'] = df1['Umidade'].astype(str)

# print(df1.head(), '\n')


# file.close()

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
    
 
 
 
 
 
 
 
 
 
    # files_list = zip.namelist()
    # if '2000/INMET_CO_DF_A001_BRASILIA_07-05-2000_A_31-12-2000.CSV' in files_list:
    #     t = zip.open('2000/INMET_CO_DF_A001_BRASILIA_07-05-2000_A_31-12-2000.CSV')
    #     print(t.read())