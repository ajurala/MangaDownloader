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
        MangaConfig.__init__(self)
        try:
            with open(self.mangaPickle, "rb") as fd:
                self.mangaList = pickle.load(fd)
        except IOError:
            pass
        except ValueError as err:
            print "Still getting ValueError"
            print err
            pass

    def dumpManga(self):
        with open(self.mangaPickle, "wb") as fd:
            pickle.dump(self.mangaList, fd)

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

    def loadDownloadChapters(self, urlsInfo, downloadSessionId, progressInfo, downloadSessionComplete, downloadSessionFailed,
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

            print "Number of chapters in this session " + str(len(temp_urls))
            if len(temp_urls) > 0:
                downloadSession = {}
                downloadSession['downloadInProgress'] = False
                downloadSession['progressInfo'] = progressInfo
                downloadSession['downloadSessionComplete'] = downloadSessionComplete
                downloadSession['chapterProgressInfo'] = chapterProgressInfo
                downloadSession['chapterDownloadSessionComplete'] = chapterDownloadSessionComplete
                downloadSession['downloadSessionFailed'] = downloadSessionFailed
                downloadSession['chapterURLs'] = temp_urls
                downloadSession['chapterNames'] = temp_chapter_names
                downloadSession['currentChapter'] = 0
                downloadSession['folder'] = folder
                downloadSession['downloadChapterSessionsInfo'] = []
                downloadSession['totalImages'] = 0
                downloadSession['totalDownloadedImages'] = 0

                self.downloadSessions[downloadSessionId] = downloadSession

        return temp_urls

    def startResumeDownloadChapters(self, downloadSessionId):
        with self.sessionLock:
            downloadSession = self.downloadSessions.get(downloadSessionId, None)
            if downloadSession is not None and not downloadSession['downloadInProgress']:

                downloadSession['downloadInProgress'] = True

                # From these temp_urls get all the manga image urls and then initiate threads
                chapterURLs = downloadSession['chapterURLs']
                currentChapter = downloadSession['currentChapter']

                url = chapterURLs[currentChapter]
                downloadChapterSessionInfo = {}
                downloadChapterSessionInfo['imagesURLs'] = []
                downloadChapterSessionInfo['chapterSessionDownloader'] = None
                downloadChapterSessionInfo['folder'] = None

                downloadSession['downloadChapterSessionsInfo'].append(downloadChapterSessionInfo)

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

                    downloadSession['totalImages'] += downloadSession['totalImages'] + 1

                    # Get the next url and see if needs to be downloaded
                    node = node.getparent()
                    url = node.get('href')
                    curUrl = req.geturl()

                    curPage = int(curUrl.split('/')[-1])
                    try:
                        nextPage = int(url.split('/')[-1])
                    except ValueError:
                        nextPage = 0

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

                            downloadSession['downloadChapterSessionsInfo'].append(downloadChapterSessionInfo)
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
                                                                            self.chapterDownloadSessionFailed,
                                                                            folder)

                        downloadChapterSessionInfo['chapterSessionDownloader'] = sessionDownloader
                        downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                        sessionDownloader.startResumeDownloadSession()

                self.downloadSessions[downloadSessionId] = downloadSession


    def chapterProgressInfo(self, downloadSessionId, downloadedCount, percent):
        with self.sessionLock:
            if downloadSessionId is not None:
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:
                    totalProgress = (float(downloadSession['totalDownloadedImages'] + downloadedCount) / float(downloadSession['totalImages'])) * 100

                    progressInfo = downloadSession['progressInfo']
                    chapterProgressInfo = downloadSession['chapterProgressInfo']

                    chapterProgressInfo(downloadSessionId, percent)
                    progressInfo(downloadSessionId, totalProgress)

    def chapterDownloadSessionComplete(self, downloadSessionId):
        print "Chapter Download Complete"

        chapterProgressInfo = None
        progressInfo = None
        chapterDownloadSessionComplete = None
        downloadSessionComplete = None

        with self.sessionLock:
            if downloadSessionId is not None:
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:
                    currentChapter = downloadSession['currentChapter']
                    downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                    currentChapterFolder = downloadChapterSessionInfo['folder']

                    totalDownloadedImages = downloadSession['totalDownloadedImages'] + len(downloadChapterSessionInfo['imagesURLs'])
                    totalProgress = (float(totalDownloadedImages) / float(downloadSession['totalImages'])) * 100

                    chapterURLs = downloadSession['chapterURLs']

                    url = chapterURLs[currentChapter]

                    if self.downloadURLs.get(url, None) is not None:
                        self.downloadURLs.pop(url)

                    downloadSession['chapterURLs'].pop(currentChapter)
                    downloadSession['chapterNames'].pop(currentChapter)
                    downloadSession['downloadChapterSessionsInfo'].pop(currentChapter)
                    #currentChapter += 1

                    downloadSession['currentChapter'] = currentChapter
                    downloadSession['totalDownloadedImages'] = totalDownloadedImages

                    percent = 100

                    # Check if next chapter to be downloaded. If so then start it
                    
                    if currentChapter < len(downloadSession['chapterURLs']):
                        percent = 0
                        folder = os.path.join(downloadSession['folder'], downloadSession['chapterNames'][currentChapter])

                        #downloadSession['currentChapter'] = currentChapter

                        downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                        downloadChapterSessionInfo['folder'] = folder

                        sessionDownloader = MangaChapterSessionDownloader(downloadChapterSessionInfo['imagesURLs'], downloadSessionId,
                                                                            self.chapterProgressInfo,
                                                                            self.chapterDownloadSessionComplete,
                                                                            self.chapterDownloadSessionFailed,
                                                                            folder)

                        downloadChapterSessionInfo['chapterSessionDownloader'] = sessionDownloader
                        downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                        sessionDownloader.startResumeDownloadSession()
                    else:
                        downloadSessionComplete = downloadSession['downloadSessionComplete']

                    progressInfo = downloadSession['progressInfo']
                    chapterProgressInfo = downloadSession['chapterProgressInfo']
                    chapterDownloadSessionComplete = downloadSession['chapterDownloadSessionComplete']

                    self.downloadSessions[downloadSessionId] = downloadSession

        if chapterProgressInfo is not None:
            chapterProgressInfo(downloadSessionId, percent)

        if progressInfo is not None:
            progressInfo(downloadSessionId, totalProgress)

        if chapterDownloadSessionComplete is not None:
            chapterDownloadSessionComplete(downloadSessionId, currentChapterFolder)

        if downloadSessionComplete is not None:
            downloadSessionComplete(downloadSessionId)

    def chapterDownloadSessionFailed(self, downloadSessionId):
        downloadSessionFailed = None
        with self.sessionLock:
            if downloadSessionId is not None:
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:
                    downloadSessionFailed = downloadSession['downloadSessionFailed']
                    downloadSession['downloadInProgress'] = False

        if downloadSessionFailed is not None:
            downloadSessionFailed(downloadSessionId)