from lxml import etree
from threading import Lock

from StringIO import StringIO

import MangaURLDownloader

from MangaChapterSessionDownloader import MangaChapterSessionDownloader
from MangaConfig import MangaConfig

import pickle


class MangaStreamDownloader(MangaConfig):
    requestPending = False
    mangaSiteName = 'MangaStream'
    mangaSiteURL = 'http://mangastream.com/manga'

    callbackFunc = None
    chapterCallbackFunc = None
    currentChapterListReq = None

    mangaLock = Lock()
    chapterLock = Lock()
    sessionLock = Lock()

    mangaPickle = "MangaStream.db"
    mangaList = []

    downloadURLs = {}
    downloadSessions = {}
    downloadChapterPageInfo = {}

    def __init__(self):
        try:
            with open(self.mangaPickle, "rb") as fd:
                self.mangaList = pickle.load(fd)
        except IOError:
            pass
        except ValueError:
            pass

    def dumpManga(self):
        with open( self.mangaPickle, "wb" ) as fd:
            pickle.dump( self.mangaList, fd)

    def isRequestPending(self):
        return self.requestPending

    def downloadMangaList(self, callbackFunc):
        if not self.requestPending:
            with self.mangaLock:
                self.callbackFunc = callbackFunc
                self.requestPending = True
                MangaURLDownloader.downloadUrl(self.mangaSiteURL, self.downloadMangaSuccess)

    def downloadMangaSuccess(self, req, result):
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
        with self.chapterLock:
            self.chapterCallbackFunc = callbackFunc
            self.currentChapterListReq = MangaURLDownloader.downloadUrl(url, self.downloadChapterListSuccess)

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

                self.chapterCallbackFunc(self.mangaSiteName, chapterList)
                self.chapterCallbackFunc = None
                self.currentChapterListReq = None

    def getMangaList(self):
        return self.mangaList

    def loadDownloadChapters(self, urls, downloadSessionId, progressInfo, downloadSessionComplete,
                                chapterProgressInfo, chapterDownloadSessionComplete, folder):
        # Check the urls that is already being downloaded and start a new session for remaining ones
        temp_urls = []

        with self.sessionLock:
            for url in urls:
                exists = self.downloadURLs.get(url, None)
                if exists is None:
                    temp_urls.append(url)
                    self.downloadURLs[url] = downloadSessionId

            
            sessionDownloader = MangaChapterSessionDownloader(temp_urls, downloadSessionId,
                                                                self.chapterProgressInfo,
                                                                self.chapterDownloadSessionComplete,
                                                                folder)

            downloadSession = {}
            downloadSession['progressInfo'] = progressInfo
            downloadSession['downloadSessionComplete'] = downloadSessionComplete
            downloadSession['chapterProgressInfo'] = chapterProgressInfo
            downloadSession['chapterDownloadSessionComplete'] = chapterDownloadSessionComplete
            downloadSession['chapterURLs'] = temp_urls
            downloadSession['currentChapter'] = 0
            downloadSession['folder'] = folder
            downloadSession['downloadChapterSessionsInfo'] = {}

            self.downloadSessions[downloadSessionId] = downloadSession

        return temp_urls

    def startResumeDownloadChapters(self, downloadSessionId):
        with self.sessionLock:
            downloadSession = self.downloadSessions.get(downloadSessionId, None)
            if downloadSession is not None:

                # From these temp_urls get all the manga image urls and then initiate threads

                return True

        return False

    def parsedChapterPage(self, req, result):
        with self.sessionLock:
            downloadSessionId = self.downloadChapterPageInfo.get(req, None)
            if downloadSessionId is not None:
                pass

    def chapterProgressInfo(self, downloadSessionId, percent):
        pass

    def chapterDownloadSessionComplete(self, downloadSessionId):
        pass

