#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013, Neriberto C.Prado
#
# This file is part of HG - https://github.com/neriberto/hg
# See the file 'docs/LICENSE' for copying permission.

from hg.core.processors import Processors
import logging
import requests


class viper(Processors):

    Name = 'Viper'
    ADDURL = '%sfile/add'

    def not_exist(self, MD5, URL):
        try:
            Data = {'md5': MD5}
            r = requests.post('%sfile/find' % URL, data=Data)
            return r.status_code == 404
        except Exception as e:
            logging.error('Viper:not_exist %s' % e)
            return False
