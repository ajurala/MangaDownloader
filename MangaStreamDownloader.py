from kivy.network.urlrequest import UrlRequest
from lxml import etree
from threading import Lock

from StringIO import StringIO

import pickle


class MangaStreamDownloader():
    requestPending = False
    mangaSiteName = 'MangaStream'
    mangaSiteURL = 'http://mangastream.com/manga'

    callbackFunc = None
    chapterCallbackFunc = None
    currentChapterListReq = None

    mangaLock = Lock()
    chapterLock = Lock()

    mangaPickle = "MangaStream.pkl"
    mangaList = []

    def __init__(self):
        try:
            self.mangaList = pickle.load(open(self.mangaPickle, "rb"))
        except IOError:
            pass

    def isRequestPending(self):
        return self.requestPending

    def downloadMangaList(self, callbackFunc):
        if not self.requestPending:
            with self.mangaLock:
                self.callbackFunc = callbackFunc
                self.requestPending = True
                UrlRequest(self.mangaSiteURL, self.downloadMangaSuccess)

    def downloadMangaSuccess(self, req, result):
        #print req
        with self.mangaLock:
            if self.callbackFunc is not None:
                parser = etree.HTMLParser()
                tree = etree.parse(StringIO(result), parser)

                #nodeList = tree.xpath('//a[@href=re.match(http://mangastream.com/manga)',
                #                    namespaces={"re": "http://exslt.org/regular-expressions"})

                nodeList = tree.xpath('.//a[starts-with(@href, "http://mangastream.com/manga/")]')

                mangaDict = {}
                for node in nodeList:
                    mangaDict[node.text] = node.get('href')

                mangaList = []
                for manga in sorted(mangaDict.keys()):
                    mangaInfo = {}
                    mangaInfo['name'] = manga
                    mangaInfo['url'] = mangaDict[manga]
                    mangaList.append(mangaInfo)

                self.mangaList = mangaList
                #pickle it
                self.dumpManga()

                self.callbackFunc(self.mangaSiteName, mangaList)
                self.callbackFunc = None

            self.requestPending = False

    def stopPendingChapterRequests():
        # This function might be needed later
        pass

    def downloadChapterList(self, url, callbackFunc):
        print "Chapter list dwnload in ms for "+ url
        with self.chapterLock:
            self.chapterCallbackFunc = callbackFunc
            self.currentChapterListReq = UrlRequest(url, self.downloadChapterListSuccess)

    def downloadChapterListSuccess(self, req, result):

        with self.chapterLock:
            if self.currentChapterListReq == req and self.chapterCallbackFunc is not None:
                parser = etree.HTMLParser()
                tree = etree.parse(StringIO(result), parser)

                nodeList = tree.xpath('.//td/a[starts-with(@href, "http://readms.com/r/")]')

                chapterListDict = {}
                for node in nodeList:
                    if node.text is not None:
                        chapterListDict[node.text] = node.get('href')

                chapterList = []
                for chapter in sorted(chapterListDict.keys()):
                    chapterInfo = {}
                    chapterInfo['name'] = chapter
                    chapterInfo['url'] = chapterListDict[chapter]
                    chapterList.append(chapterInfo)

                print chapterList
                self.chapterCallbackFunc(self.mangaSiteName, chapterList)
                self.chapterCallbackFunc = None
                self.currentChapterListReq = None

    def getMangaList(self):
        return self.mangaList

    def dumpManga(self):
        pickle.dump( self.mangaList, open( self.mangaPickle, "wb" ) )