#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013, Neriberto C.Prado
#
# This file is part of HG - https://github.com/neriberto/hg
# See the file 'docs/LICENSE' for copying permission.

from hg.core.feeds import Feeds
from lxml import etree


class zeus(Feeds):

    Name = 'Zeus'
    URL = 'https://zeustracker.abuse.ch/monitor.php?urlfeed=binaries'

    def run(self, q):
        try:
            content = self.Download(self.URL)
            if content is not None:
                children = ['title', 'link', 'description', 'guid']
                main_node = 'item'

                tree = etree.parse(content)
                for item in tree.findall('//%s' % main_node):
                    dic = {}
                    for field in children:
                        if field == 'description':
                            dic[field] = item.findtext(field)
                            url = (dic['description'].split(' ')[1])[:-1]
                            if len(url) > 8:
                                q.put(url, True, 5)
        except KeyboardInterrupt:

            pass
