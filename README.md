# INMET SCRAPER

Este é um software feito com o objetivo de coletar, analisar e processar dados meteorológicos do Brasil, com foco na variável de radiação solar.
Isso ocorre da seguinte forma:
1. Todos os dados, de todas as estações meteorológicas disponível no site de dados históricos do INMET (https://portal.inmet.gov.br/dadoshistoricos), são baixados.
2. O programa analiza todos os .csv e cria um arquivo .json com a informação de todas as estações presentes. Isso é utilizado para fins de pesquisa e exibição de informações.
3. Ao escolher uma determinada estação para a concatenação, o programa encontra o .csv nas pastas anuais. Posteriormente, os dados dos anos seguintes são concatenados no final do arquivo anterior, deixando, no final do processo, um arquivo .csv único com todos os dados daquela estação.
4. No processo de limpeza, dados inválidos ou com valores absurdos são removidos da planilha.

## Planos Futuros
- Implementar um método de Machine Learning de séries temporais para prever a variável de radiação solar.
- Criar um versão de console (CLI).

## Features
- Interfáce gráfica intuitiva
- Download automático de dados (Web Scraping)
- Limpeza de dados (Data Cleaning)

## Instalação

Instale as bibliotecas necessárias para rodar o programa. Execute a partir de main.py.

```sh
pip install wxPython
pip install beautifulsoup4
pip install pypubsub
pip install requests
pip install pandas
```
![scraper_ss](https://github.com/NeoFahrenheit/inmet-scraper/assets/16950058/7b54cc58-f014-4af0-abda-304f33b55f7d)
