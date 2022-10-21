import csv
import pandas as pd
import data_processing as dp

encod_estacao = 'latin-1'
encod_historico = 'utf-8-sig'

file =  open('../historico.csv', encoding=encod_estacao)
_ = [next(file) for _ in range(8)]  # Ignorar o início do .csv, já que contém apenas informações da estação.

df = pd.read_csv(file, delimiter=';', quotechar='"')

filter = [x[0] for x in dp.d_dic.values()]
print(filter)
df = df.filter(filter)
print(df.head())


file.close()

#file_estacao =  open('../historico.csv', encoding=encod_estacao)

