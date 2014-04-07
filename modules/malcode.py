# Copyright (c) 2013, Neriberto C.Prado
#
# This file is part of HG - https://github.com/neriberto/hg
# See the file 'docs/LICENSE' for copying permission.


import requests
from xml.dom.minidom import parseString

class malcode (object):

    Name = "Malc0de"
    URL = "http://malc0de.com/"

    def run(self):
        URLS = []
        # Download list from malc0de
        content = self.Download("http://malc0de.com/rss")
        if content != None:
            bk = content.replace("\n", "")
            # enforce ISO-8859-1 how in RSS
            dom = None
            try:
                dom = parseString(bk.encode("ISO-8859-1"))
            except:
                dom = parseString(bk)
            for node in dom.getElementsByTagName("description"):
                # extract the URLs
                line = node.toxml().replace("<description>", "")
                info = line.replace("</description", "")
                try:
                    URLS.append("http://" + info.split(',')[0].split(':')[1][1:])
                except:
                    pass
            return URLS
        else:
            return None

    def Download(self, URL):
        '''
        :description : Execute download from a URL
        '''
        try:
            r = requests.get(URL)
            return r.content
        except Exception, e:
            print "Failure, %s" % e
            return None
