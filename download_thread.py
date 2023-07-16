import os
from threading import Thread
import requests
from pubsub import pub

class DownloadThread(Thread):
    def __init__(self, path: str, url: str):
        Thread.__init__(self)
        self.isActive = True

        self.path = path
        self.url = url
        self.dl = 0
        self.dl_temp = 0

        self.start()

    def run(self):
        perc_temp = 0
        
        try:
            r = requests.get(self.url, stream=True)
        except:
            raise Exception('Could not communicate with the host.')

        # Alguns sites não possuem o tamanho total do arquivo. Portanto,
        # neste caso, não dá pra mostrar progresso do download.
        self.total_length = r.headers.get('content-length')
        isGoingOk = True

        pub.subscribe(self._on_timer, 'ping-timer')
        with open(self.path, 'wb') as f:
            try:
                if not self.total_length:
                    for data in r.iter_content(chunk_size=4096):
                        if self.isActive:
                            self.dl += len(data)
                            self.dl_temp += len(data)
                            f.write(data)

                        else:
                            isGoingOk = False
                            break

                else:
                    self.total_length = int(self.total_length)
                    self.total_size = self._get_downloaded_value(self.total_length)
                    self.total_unit = self._get_unit(self.total_length)

                    for data in r.iter_content(chunk_size=4096):
                        if self.isActive:
                            self.dl += len(data)
                            self.dl_temp += len(data)
                            f.write(data)
                            value = int(100 * self.dl / self.total_length)

                            if perc_temp != value:
                                perc_temp = value
                                pub.sendMessage(topicName='update-current-gauge', value=perc_temp)

                        else:
                            isGoingOk = False
                            break
            except:
                isGoingOk = False

        pub.sendMessage(topicName='update-current-gauge', value=100)

        # Se ocorrer algum problema no download, removemos o arquivo.
        # Só queremos ter arquivos totalmente baixados.
        if not isGoingOk:
            os.remove(self.path)
            raise Exception('Download canceled or connection to the host lost')

    def _get_progress_text(self):
        ''' Retorna uma tupla com estatísticas do quanto do arquivo já foi baixado 
        e a velocidade de download, respectivamente. '''

        downloaded = self._get_downloaded_value(self.dl)
        unit_downloaded = self._get_unit(self.dl)

        speed = self._get_downloaded_value(self.dl_temp)
        speed_unit = self._get_unit(self.dl_temp)

        if self.total_length:
            t = (f"{downloaded:.2f} {unit_downloaded} / {self.total_size:.2f} {self.total_unit}",
                 f"{speed:.2f} {speed_unit}/s")
        else:
            t = (f"{downloaded:.2f} {unit_downloaded} / ?", f"{speed:.2f} {speed_unit}/s")

        self.dl_temp = 0
        return t

    def _get_unit(self, size):
        """ Retorna unidade de medida, dado o tamanho `size` em bytes."""

        if size < 1024:
            return 'B'
        elif size < 1_048_576:
            return 'KB'
        else:
            return 'MB'

    def _get_downloaded_value(self, size):
        ''' Retorna um inteiro. Dependendo de `size`, o número é entrege sem modificação,
        dividido 1024 (1KB) ou  por 1.048.7106 (1MB). Deve ser usado junto com sua unidade correspondente. '''

        if size < 1024:
            return size
        elif size < 1_048_576:
            return size / 1024
        else:
            return size / 1_048_576

    def _on_timer(self):
        """ Chamada a cada segundo. Envia informações de progresso ao frame principal. """

        size, speed = self._get_progress_text()
        pub.sendMessage('update-size-text', text=size)
        pub.sendMessage('update-speed-text', text=speed)

    def on_end_thread(self):
        ''' Usada para mudar a variável `self.isActive` para posteriormente terminar esta thread. '''

        self.isActive = False
