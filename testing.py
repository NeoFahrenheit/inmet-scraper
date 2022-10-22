import csv
import pandas as pd
import data_processing as dp

def convertToHour(n: str) -> str:
    n = str(n)
    size = len(n)

    if size == 1:
        return '00:00'
    elif size < 4:
        s = '0' + n
        return s[:2] + ':00'
    else:
        return n[:2] + ':00'    

encod_estacao = 'latin-1'
encod_historico = 'utf-8-sig'

file =  open('../historico.csv', encoding=encod_estacao)
_ = [next(file) for _ in range(8)]  # Ignorar o início do .csv, já que contém apenas informações da estação.
df1 = pd.read_csv(file, delimiter=';', quotechar='"')

filter = [x[0] for x in dp.d_dic.values()]
df1 = df1.filter(filter)

df1 = df1.rename(columns={dp.d_dic['Data'][0]: 'Data', dp.d_dic['Hora'][0]: 'Hora', dp.d_dic['Radiacao'][0]: 'Radiacao',
    dp.d_dic['Chuva'][0]: 'Chuva', dp.d_dic['Pressao'][0]: 'Pressao', dp.d_dic['Temperatura'][0]: 'Temperatura',
    dp.d_dic['Umidade'][0]: 'Umidade'})


df1['Umidade'] = df1['Umidade'].astype(str)

print(df1.head(), '\n')


file.close()

file_estacao =  open('../estacao.csv')
df2 = pd.read_csv(file_estacao, delimiter=';')

filter = [x[1] for x in dp.d_dic.values()]
df2 = df2.filter(filter)
df2 = df2.rename(columns={dp.d_dic['Data'][1]: 'Data', dp.d_dic['Hora'][1]: 'Hora', dp.d_dic['Radiacao'][1]: 'Radiacao',
    dp.d_dic['Chuva'][1]: 'Chuva', dp.d_dic['Pressao'][1]: 'Pressao', dp.d_dic['Temperatura'][1]: 'Temperatura',
    dp.d_dic['Umidade'][1]: 'Umidade'})

input_date = '%d/%M/%Y'
output_date = '%Y-%M-%d'
df2['Data'] = pd.to_datetime(df2['Data'], format=input_date).dt.strftime(output_date)

df2['Hora'] = df2['Hora'].apply(lambda x: convertToHour(x))

print(df2.head())

file_estacao.close() 

pd.concat([df1, df2], ignore_index=True).to_csv('test.csv', index=False)
