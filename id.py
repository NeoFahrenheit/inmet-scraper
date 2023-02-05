# O nome e a posição das colunas dos dados históricos e das estações são diferentes!
# Esse dicionário vai nos auxiliar para pegar um determinado dado nas duas tabelas.
# lista[0] -> Colunas como estão nos dados históricos.
# lista[1] -> Colunas como estão nos dados das estações (website).
d_dic = {
    "Data": ['DATA (YYYY-MM-DD)', 'DT_MEDICAO'],
    "Hora": ['HORA (UTC)', 'HR_MEDICAO'],
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
    "Pressao": ['PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)', 'PRE_INS'],
    "Radiacao": ['RADIACAO GLOBAL (Kj/m²)', 'RAD_GLO'],
    "Temperatura": ['TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)', 'TEM_INS'],
    "Umidade": ['UMIDADE RELATIVA DO AR, HORARIA (%)', 'UMD_INS']
}

# Para download feitos através de web scraping no site do INMET.
d_dic_inmet = {
    "Data": ['Data', 'DT_MEDICAO'],
    "Hora": ['Hora (UTC)', 'HR_MEDICAO'],
    "Pressao": ['Pressao Ins. (hPa)', 'PRE_INS'],
    "Radiacao": ['Radiacao (KJ/m²)', 'RAD_GLO'],
    "Temperatura": ['Temp. Ins. (C)', 'TEM_INS'],
    "Umidade": ['Umi. Ins. (%)', 'UMD_INS']
}

class ID:
    MENU_SCROLL = 1
    LISTBOX = 2

    
    POPUP_CONCAT = 2002
    POPUP_UPDATE = 2003
    POPUP_CLEAN = 2004 
    POPUP_DELETE = 2005
    POPUP_SAVE = 2006