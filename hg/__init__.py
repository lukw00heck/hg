#!/usr/bin/python
# -*- coding: utf-8 -*-

#

import ConfigParser
import os
import fnmatch
import hashlib
import logging
import magic
import Queue
import tempfile
import time
import threading
import requests
import shutil
import sys


class hg(object):

    _Config = {}
    _Processors = []
    _Feeds = []
    _Fila = Queue.Queue()
    _End_Process = False
    '''
    Number of Threads
    '''
    _NUM_CONCURRENT_DOWNLOADS = 2
    '''
    Determine if need to download the URL
    '''
    _getData = False

    def __init__(self, downloads=2):
        self._NUM_CONCURRENT_DOWNLOADS = downloads
        Path = \
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         '../')
        self._Processors = self.LoadModules(Path, 'processors')
        self._Feeds = self.LoadModules(Path, 'feeds')

        # Configure the logging

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            stream=sys.stdout)

        # Configure requests to show only WARNING messages

        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('HG').setLevel(logging.WARNING)
        logging.addLevelName(logging.WARNING, "\033[1;31m%s\033[1;0m"
                             % logging.getLevelName(logging.WARNING))
        logging.addLevelName(logging.ERROR, "\033[1;41m%s\033[1;0m"
                             % logging.getLevelName(logging.ERROR))

        fconf = os.path.join(Path, 'conf/hg.conf')
        if os.path.exists(fconf):
            cfg = ConfigParser.ConfigParser()
            cfg.read(fconf)

            VX = {}
            VX['Enabled'] = cfg.get('vxcage', 'enabled')
            VX['connection'] = cfg.get('vxcage', 'connection')
            if VX['Enabled'] == "yes":
                self._getData = True

            Viper = {}
            Viper['Enabled'] = cfg.get('viper', 'enabled')
            Viper['connection'] = cfg.get('viper', 'connection')
            if Viper['Enabled'] == "yes":
                self._getData = True

            Cuckoo = {}
            Cuckoo['Enabled'] = cfg.get('cuckoo', 'enabled')
            Cuckoo['connection'] = cfg.get('cuckoo', 'connection')
            if Cuckoo['Enabled'] == "yes":
                self._getData = True

            self._Config['VxCage'] = VX
            self._Config['Cuckoo'] = Cuckoo
            self._Config['Viper'] = Viper

        if self._getData:
            logging.info('Initializing HG')
        else:
            logging.error('You must enable at least one module in the config')
            sys.exit(-1)

    def LoadModules(self, Root, Directory):
        Modules = []
        Walk_In = os.path.join(Root, Directory)
        for (_, _, names) in os.walk(Walk_In):
            for name in fnmatch.filter(names, '*.py'):
                if name == '__init__.py':
                    continue
                name = '%s.%s' % (Directory, name.split('.py')[0])
                processor = __import__(name, globals(), locals(), [''])
                components = name.split('.')[1:]
                for com in components:
                    class_ = getattr(processor, com)
                    Modules.append(class_())
        return Modules

    def SaveFile(self, data):
        if len(data['filename']) <= 0:
            logging.debug('Not a valid filename')
            sys.exit(-1)
        tempd = tempfile.mkdtemp()
        path = os.path.join(tempd, data['filename'])
        fp = open(path, 'wb')
        fp.write(data['content'])
        fp.close()
        return path

    def GetFileType(self, data):
        filetype = None
        try:

            # using python-magic from apt-get(Ubuntu)

            ms = magic.open(magic.MAGIC_MIME)
            ms.load()
            filetype = ms.buffer(data)
        except:
            try:

                # from pip install libmagic, python-magic

                filetype = magic.Magic(mime=True).from_buffer(data)
            except Exception as e:
                logging.error(e)
                self._End_Process = True

        return filetype.split(';')[0]

    def Fetch(self, URL):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            re = requests.get(URL, allow_redirects=True,
                timeout=100, headers=headers)

            if re.status_code != 200:
                return dict({'filename': None, 'content': None, 'status_code': re.status_code})

            UseDisp = False
            for item in re.headers:
                if item.lower() == 'content-disposition':
                    UseDisp = True
            if not UseDisp:
                filename = URL.split('/')[-1].split('#')[0].split('?')[0]
                if filename is not None:
                    filename = URL.split('/')
            else:
                Disposition = re.headers['Content-Disposition']
                try:
                    filename = Disposition.split('filename=')[1].split('"')[1]
                except Exception:
                    filename = Disposition.split('filename=')[1].split('"')[0]

            if len(filename) <= 0:
                logging.debug(URL)
                sys.exit(-1)

            return dict({'filename': filename, 'content': re.content,
                        'status_code': re.status_code})

        except Exception:
            return dict({'filename': None, 'content': None,
                        'status_code': '0'})  # 0 for timeout
        except KeyboardInterrupt:
            pass

    def Downloader(self):
        while not self._End_Process:
            try:
                url = self._Fila.get(True, 5)
            except Queue.Empty:
                continue

            # If any module that need to download the URL is enable,
            # we stop here
            if self._getData is False:
                return

            data = self.Fetch(url)
            if data['status_code'] == 200:
                logging.info(url)

            if data['content'] is None:
                return

            fpath = self.SaveFile(data['content'])
            ftype = self.GetFileType(data['content'])
            if os.path.getsize(fpath) <= 0:
                return

            for proc in self._Processors:
                proc.run(self._Config, fpath, ftype)
            os.remove(fpath)
            shutil.rmtree(os.path.dirname(os.path.abspath(fpath)))
            data = None
            self._Fila.task_done()

    def run(self):
        threads = []

        logging.info('Initializing Downloaders')
        logging.info('Working threads: %s', self._NUM_CONCURRENT_DOWNLOADS)
        for unused_index in range(self._NUM_CONCURRENT_DOWNLOADS):
            thread = threading.Thread(target=self.Downloader)
            thread.daemon = True
            thread.start()
            threads.append(thread)

        while not self._End_Process:
            try:
                if self._Fila.qsize() > 300:
                    logging.info('Status: %s files to download',
                                 self._Fila.qsize())
                    logging.info('Status: Feeds waiting 5 minute')
                    time.sleep(60 * 5)
                    continue
                for feed in self._Feeds:
                    try:
                        feed.run(self._Fila)
                    except Exception as e:
                        logging.error('Feed with errors: %s', feed.Name)
                        logging.error(e)
                        sys.exit(-1)
                logging.info('Status: Feeds retrieved, waiting 30 minutes'
                             )
                time.sleep(60 * 30)
            except KeyboardInterrupt:
                logging.info('Shutdown HG')
                self._End_Process = True
