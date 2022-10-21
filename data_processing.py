import pandas

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

class DataProcessing():
    def __init__(self):
        pass