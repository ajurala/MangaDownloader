from lxml import etree
from threading import Lock

from StringIO import StringIO

import MangaURLDownloader
import os

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

    def loadDownloadChapters(self, urlsInfo, downloadSessionId, progressInfo, downloadSessionComplete,
                                chapterProgressInfo, chapterDownloadSessionComplete, folder):
        # Check the urls that is already being downloaded and start a new session for remaining ones
        temp_urls = []
        temp_chapter_names = []

        with self.sessionLock:
            for urlInfo in urlsInfo:
                url = urlInfo['url']
                chapterName = urlInfo['chapterName']
                exists = self.downloadURLs.get(url, None)
                if exists is None:
                    temp_urls.append(url)
                    temp_chapter_names.append(chapterName)
                    self.downloadURLs[url] = downloadSessionId

            if len(temp_urls) > 0:
                downloadSession = {}
                downloadSession['progressInfo'] = progressInfo
                downloadSession['downloadSessionComplete'] = downloadSessionComplete
                downloadSession['chapterProgressInfo'] = chapterProgressInfo
                downloadSession['chapterDownloadSessionComplete'] = chapterDownloadSessionComplete
                downloadSession['chapterURLs'] = temp_urls
                downloadSession['chapterNames'] = temp_chapter_names
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
                chapterURLs = downloadSession['chapterURLs']
                currentChapter = downloadSession['currentChapter']

                url = chapterURLs[currentChapter]
                downloadChapterSessionInfo = {}
                downloadChapterSessionInfo['imagesURLs'] = []
                downloadChapterSessionInfo['chapterSessionDownloader'] = None
                downloadChapterSessionInfo['folder'] = None

                downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                req = MangaURLDownloader.downloadUrl(url, self.parsedChapterPage)

                self.downloadChapterPageInfo[req] = downloadSessionId

                return True

        return False

    def parsedChapterPage(self, req, result):
        with self.sessionLock:
            downloadSessionId = self.downloadChapterPageInfo.get(req, None)
            if downloadSessionId is not None:
                self.downloadChapterPageInfo.pop(req)
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:
                    currentChapter = downloadSession['currentChapter']

                    downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]

                    # Get the png url
                    parser = etree.HTMLParser()
                    tree = etree.parse(StringIO(result), parser)

                    nodeList = tree.xpath('.//img[starts-with(@src, "http://img.mangastream.com/cdn/manga/")]')

                    # This should not happen
                    # TODO - Log this kind of situation
                    if len(nodeList) > 1:
                        return

                    node = nodeList[0]
                    imageURL  = node.get('src')

                    downloadChapterSessionInfo['imagesURLs'].append(imageURL)
                    downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                    # Get the next url and see if needs to be downloaded
                    node = node.getParent()
                    url = node.get('href')
                    curUrl = req.geturl()

                    curPage = int(curUrl.split('/')[-1])
                    nextPage = int(url.split('/')[-1])

                    if nextPage < curPage:
                        url = None

                        # Get next chapter url
                        chapterURLs = downloadSession['chapterURLs']
                        currentChapter += 1

                        if currentChapter < len(chapterURLs):
                            url = chapterURLs[currentChapter]
                            downloadChapterSessionInfo = {}
                            downloadChapterSessionInfo['imagesURLs'] = []
                            downloadChapterSessionInfo['chapterSessionDownloader'] = None
                            downloadChapterSessionInfo['folder'] = None

                            downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo
                            downloadSession['currentChapter'] = currentChapter

                    if url is not None:
                        req = MangaURLDownloader.downloadUrl(url, self.parsedChapterPage)

                        self.downloadChapterPageInfo[req] = downloadSessionId
                    else:
                        # Start the session
                        currentChapter = 0
                        folder = os.path.join(downloadSession['folder'], downloadSession['chapterNames'][currentChapter])

                        downloadSession['currentChapter'] = currentChapter

                        downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                        downloadChapterSessionInfo['folder'] = folder

                        sessionDownloader = MangaChapterSessionDownloader(downloadChapterSessionInfo['imagesURLs'], downloadSessionId,
                                                                            self.chapterProgressInfo,
                                                                            self.chapterDownloadSessionComplete,
                                                                            folder)

                        downloadChapterSessionInfo['chapterSessionDownloader'] = sessionDownloader
                        downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                self.downloadSessions[downloadSessionId] = downloadSession


    def chapterProgressInfo(self, downloadSessionId, percent):
        pass

    def chapterDownloadSessionComplete(self, downloadSessionId):
        pass

