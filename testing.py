import csv

encod1 = 'utf-8-sig'
encod2 = 'latin-1'

with open('../../historico.csv', encoding=encod2) as file:
    reader = csv.DictReader(file, delimiter=';')
    for row in reader:
        print(row)