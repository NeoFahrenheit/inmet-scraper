import requests
from threading import Thread
from pubsub import pub

class DownloadThread(Thread):
    ''' Esta é a Thread que faz o download. '''
    
    def __init__(self, path, url):
        Thread.__init__(self)
        self.isActive = True
        pub.subscribe(self.OnEndThread, 'kill-thread')

        self.path = path
        self.url = url
        self.dl = 0
        self.dl_temp = 0

        self.start()
        

    def run(self):
        perc_temp = 0
        r = requests.get(self.url, stream=True)

        # Alguns sites não possuem o tamanho total do arquivo. Portanto,
        # neste caso, não dá pra mostrar progresso do download.
        self.total_length = r.headers.get('content-length')
        pub.subscribe(self.OnTimer, 'ping-timer')

        with open(self.path, 'wb') as f:
            if not self.total_length: # no content length header
                self.update_gauge(0)
                for data in r.iter_content(chunk_size=4096):
                    if self.isActive:
                        self.dl += len(data)
                        self.dl_temp += len(data)
                        f.write(data)

            else:
                self.total_length = int(self.total_length)
                self.total_size = self.get_downloaded_value(self.total_length)
                self.total_unit = self.get_unit(self.total_length)

                for data in r.iter_content(chunk_size=4096):
                    if self.isActive:
                        self.dl += len(data)
                        self.dl_temp += len(data)
                        f.write(data)
                        value = int(100 * self.dl / self.total_length)

                        if perc_temp != value:
                            perc_temp = value
                            self.update_gauge(value)

    def get_progress_text(self):
        '''Retorna uma tupla com estatísticas do quanto do arquivo já foi baixado
        e a velocidade de download, respectivamente. '''

        downloaded = self.get_downloaded_value(self.dl)
        unit_downloaded = self.get_unit(self.dl)

        speed = self.get_downloaded_value(self.dl_temp)
        speed_unit = self.get_unit(self.dl_temp)

        if self.total_length:
            t = (f"{downloaded:.2f} {unit_downloaded} / {self.total_size:.2f} {self.total_unit}", f"{speed:.2f} {speed_unit}/s")
        else:
            t = (f"{downloaded:.2f} {unit_downloaded} / ?", f"{speed:.2f} {speed_unit}/s")
            
        self.dl_temp = 0
        return t

    def get_unit(self, size):
        unit = ''
        if size < 1024:
            unit = 'B'
        elif size < 1_048_576:
            unit = 'KB'
        else:
            unit = 'MB'

        return unit

    def get_downloaded_value(self, size):
        ''' Retorna um inteiro. Dependendo de `size`, o número é entrege sem modificação,
        dividido 1024 (1KB) ou  por 1.048.756 (1MB). Deve ser usado junto com sua unidade correspondente. '''
    
        if size < 1024:
            return size
        elif size < 1_048_576:
            return size / 1024
        else:
            return size / 1_048_576

    def update_gauge(self, value):
        ''' Envia para o Frame principal o valor para atualizar a barra de progresso de download do arquivo atual. '''

        pub.sendMessage('update-current-gauge', value=value)

    def OnTimer(self):
        ''' Chamada a cada segundo. Entrega o texto de progresso do download atual para o Frame principal. '''

        pub.sendMessage('update-transfer-status', text=self.get_progress_text())

    def OnEndThread(self):
        ''' Usada para mudar a variável `self.isActive` para posteriormente terminar esta thread. '''
        self.isActive = False
        
