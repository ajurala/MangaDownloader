from lxml import etree
from threading import Lock
from threading import Thread
from threading import BoundedSemaphore
from StringIO import StringIO

import MangaUtils
import MangaURLDownloader
import datetime
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

    def getDate(self, dateText):
        dteComma = dateText.find(',')
        if dteComma == -1:
            dateText = dateText[0:dateText.find(' ')]
            if dateText == "Toda":
                days = 0
            else:
                days = int(dateText)

            dte = datetime.date.today() - datetime.timedelta(days=days)
        else:
            month = dateText[0:3]
            day = dateText[4: dteComma - 2]
            day = day if len(day) == 2 else "0"+day
            year = dateText[-4:]
            dte = datetime.datetime.strptime(year+month+day, "%Y%b%d").date()

        return dte

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
                    mangaInfo['previousDate'] = datetime.date.min
                    mangaList.append(mangaInfo)

                self.mangaList = mangaList
                #pickle it
                self.dumpManga()

                self.callbackFunc(self.mangaSiteName, mangaList)
                self.callbackFunc = None

            self.requestPending = False

    def stopPendingChapterRequests(self):
        # This function might be needed later
        pass

    def downloadChapterList(self, url, callbackFunc, previousDate=datetime.date.min):
        with self.chapterLock:
            self.chapterCallbackFunc = callbackFunc
            self.currentChapterListReq = MangaURLDownloader.downloadUrl(url, self.downloadChapterListSuccess)
            self.previousDate = previousDate

    def downloadChapterListSuccess(self, req, result):

        with self.chapterLock:
            if self.currentChapterListReq == req and self.chapterCallbackFunc is not None:
                parser = etree.HTMLParser()
                tree = etree.parse(StringIO(result), parser)

                nodeList = tree.xpath('.//td/a[starts-with(@href, "http://readms.com/r/")]')

                chapterListDict = {}
                for node in nodeList:
                    if node.text is not None:
                        chapterInfo = []
                        chapterInfo.append(node.get('href'))
                        dateText = node.getparent().getnext().text
                        chapterInfo.append(self.getDate(dateText))
                        print chapterInfo[1]
                        chapterListDict[node.text] = chapterInfo

                chapterList = []
                for chapter in sorted(chapterListDict.keys()):
                    chapterInfo = {}
                    chapterInfo['name'] = chapter
                    chapterInfo['url'] = chapterListDict[chapter][0]
                    chapterInfo['date'] = chapterListDict[chapter][1]
                    if chapterInfo['date'] > self.previousDate:
                        chapterInfo['new'] = True
                    else:
                        chapterInfo['new'] = False
                    chapterList.append(chapterInfo)

                self.chapterCallbackFunc(self.mangaSiteName, chapterList)
                self.chapterCallbackFunc = None
                self.currentChapterListReq = None

    def getMangaList(self):
        return self.mangaList

    def loadDownloadChapters(self, mangaName, urlsInfo, downloadSessionId, progressInfo, downloadSessionComplete, downloadSessionFailed,
                                chapterProgressInfo, chapterDownloadSessionComplete, folder):
        # Check the urls that is already being downloaded and start a new session for remaining ones
        temp_urls = []
        temp_chapter_names = []
        temp_chapter_dates = []

        with self.sessionLock:
            for urlInfo in urlsInfo:
                url = urlInfo['url']
                chapterName = urlInfo['chapterName']
                chapterDate = urlInfo['date']
                exists = self.downloadURLs.get(url, None)
                if exists is None:
                    temp_urls.append(url)
                    temp_chapter_names.append(chapterName)
                    temp_chapter_dates.append(chapterDate)
                    self.downloadURLs[url] = downloadSessionId

            print "Number of chapters in this session " + str(len(temp_urls))
            if len(temp_urls) > 0:
                downloadSession = {}
                downloadSession['mangaName'] = mangaName
                downloadSession['downloadInProgress'] = False
                downloadSession['downloadPaused'] = False
                downloadSession['downloadComplete'] = False
                downloadSession['progressInfo'] = progressInfo
                downloadSession['downloadSessionComplete'] = downloadSessionComplete
                downloadSession['chapterProgressInfo'] = chapterProgressInfo
                downloadSession['chapterDownloadSessionComplete'] = chapterDownloadSessionComplete
                downloadSession['downloadSessionFailed'] = downloadSessionFailed
                downloadSession['chapterURLs'] = temp_urls
                downloadSession['chapterNames'] = temp_chapter_names
                downloadSession['chapterDates'] = temp_chapter_dates
                downloadSession['currentChapter'] = 0
                downloadSession['folder'] = folder
                downloadSession['downloadChapterSessionsInfo'] = []
                downloadSession['totalImages'] = 0
                downloadSession['totalDownloadedImages'] = 0
                downloadSession['semaphore'] = BoundedSemaphore()

                self.downloadSessions[downloadSessionId] = downloadSession

        return temp_urls

    def startDownloadChapters(self, downloadSessionId):
        chapterProgress = None
        currentChapterName = ""

        with self.sessionLock:
            downloadSession = self.downloadSessions.get(downloadSessionId, None)
            if downloadSession is not None and not downloadSession['downloadInProgress'] and not downloadSession['downloadComplete']:

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

                req = MangaURLDownloader.downloadUrl(url, self.parsedChapterPage, failDownload=self.parseChapterPageFailed)

                self.downloadChapterPageInfo[req] = downloadSessionId

                chapterProgress = downloadSession['chapterProgressInfo']
                currentChapterName = downloadSession['chapterNames'][currentChapter]

        if chapterProgress is not None:
            chapterInfo = "Parsing " + currentChapterName + " (1)"

            # Update UI in a thread
            t = Thread(target=self.updateStartParse, args=(chapterProgress, downloadSessionId, chapterInfo))
            t.start()

    def updateStartParse(self, progressInfo, downloadSessionId, chapterInfo):
        progressInfo(downloadSessionId, currentChapterName=chapterInfo)

    def parseChapterPageFailed(self, req):
        print "Page parsing failed"
        with self.sessionLock:
            downloadSessionId = self.downloadChapterPageInfo.get(req, None)

        self.chapterDownloadSessionFailed(downloadSessionId)

    def parsedChapterPage(self, req, result):
        chapterProgress = None
        currentChapterName = ""
        semaphore = None
        parsingChapterPageNumber = 0
        with self.sessionLock:
            downloadSessionId = self.downloadChapterPageInfo.get(req, None)
            if downloadSessionId is not None:
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
                    parsingChapterPageNumber = len(downloadChapterSessionInfo['imagesURLs']) + 1

                    downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                    downloadSession['totalImages'] += 1

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

                            parsingChapterPageNumber = 1

                    semaphore = downloadSession['semaphore']
                    self.downloadSessions[downloadSessionId] = downloadSession

        # If semaphore not acquired then it pauses the thread automatically
        if semaphore:
            with semaphore:
                pass
        else:
            return

        with self.sessionLock:
            downloadSessionId = self.downloadChapterPageInfo.get(req, None)
            if downloadSessionId is not None:
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:

                    if url is not None:
                        newreq = MangaURLDownloader.downloadUrl(url, self.parsedChapterPage, failDownload=self.parseChapterPageFailed)

                        self.downloadChapterPageInfo[newreq] = downloadSessionId

                        chapterProgress = downloadSession['chapterProgressInfo']
                        currentChapterName = downloadSession['chapterNames'][currentChapter]
                    else:
                        # Start the session
                        currentChapter = 0
                        folder = os.path.join(downloadSession['folder'], MangaUtils.removeInvalidCharacters(downloadSession['chapterNames'][currentChapter]))

                        downloadSession['currentChapter'] = currentChapter

                        downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                        downloadChapterSessionInfo['folder'] = folder

                        # Chapter Session Downloader deletes the items in list
                        # and list is mutable in python and hence separate the list
                        urls = []
                        for url in downloadChapterSessionInfo['imagesURLs']:
                            urls.append(url)

                        sessionDownloader = MangaChapterSessionDownloader(urls, downloadSessionId,
                                                                            self.chapterProgressInfo,
                                                                            self.chapterDownloadSessionComplete,
                                                                            self.chapterDownloadSessionFailed,
                                                                            folder)

                        downloadChapterSessionInfo['chapterSessionDownloader'] = sessionDownloader
                        downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                        sessionDownloader.startDownloadSession()

                self.downloadSessions[downloadSessionId] = downloadSession

            self.downloadChapterPageInfo.pop(req)

        if chapterProgress is not None:
            chapterInfo = "Parsing " + currentChapterName + " (" + str(parsingChapterPageNumber) + ")"
            chapterProgress(downloadSessionId, currentChapterName=chapterInfo)

    def chapterProgressInfo(self, downloadSessionId, downloadedCount, percent):
        chapterProgressInfo = None
        progressInfo = None
        currentChapterName = ""

        with self.sessionLock:
            if downloadSessionId is not None:
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:
                    totalProgress = (float(downloadSession['totalDownloadedImages'] + downloadedCount) / float(downloadSession['totalImages'])) * 100

                    progressInfo = downloadSession['progressInfo']
                    chapterProgressInfo = downloadSession['chapterProgressInfo']
                    currentChapter = downloadSession['currentChapter']
                    currentChapterName = downloadSession['chapterNames'][currentChapter]

        if chapterProgressInfo is not None:
            chapterProgressInfo(downloadSessionId, currentChapterName, percent)

        if progressInfo is not None:
            progressInfo(downloadSessionId, totalProgress)

    def chapterDownloadSessionComplete(self, downloadSessionId):
        print "Chapter Download Complete"

        chapterProgressInfo = None
        progressInfo = None
        chapterDownloadSessionComplete = None
        downloadSessionComplete = None
        currentChapterName = ""

        with self.sessionLock:
            if downloadSessionId is not None:
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:
                    currentChapter = downloadSession['currentChapter']
                    downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                    currentChapterFolder = downloadChapterSessionInfo['folder']
                    currentChapterName = downloadSession['chapterNames'][currentChapter]
                    currentChapterDate = downloadSession['chapterDates'][currentChapter]

                    mangaPreviousDate = None
                    mangaIndex = None

                    # Get the current previous date and compare the same and save if current is latest
                    mangaName = downloadSession['mangaName']

                    # OPTIMIZE THIS - Think in DICT terms
                    i = 0
                    while i < len(self.mangaList):
                        manga = self.mangaList[i]
                        if manga['name'] == mangaName:
                            if manga['previousDate'] <  currentChapterDate:
                                manga['previousDate'] = currentChapterDate
                                mangaPreviousDate = currentChapterDate
                                mangaIndex = i
                                self.dumpManga()
                            break
                        i += 1

                    totalDownloadedImages = downloadSession['totalDownloadedImages'] + len(downloadChapterSessionInfo['imagesURLs'])
                    totalProgress = (float(totalDownloadedImages) / float(downloadSession['totalImages'])) * 100

                    chapterURLs = downloadSession['chapterURLs']

                    url = chapterURLs[currentChapter]

                    if self.downloadURLs.get(url, None) is not None:
                        self.downloadURLs.pop(url)

                    downloadSession['chapterURLs'].pop(currentChapter)
                    downloadSession['chapterNames'].pop(currentChapter)
                    downloadSession['chapterDates'].pop(currentChapter)
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

                        # Chapter Session Downloader deletes the items in list
                        # and list is mutable in python and hence separate the list
                        urls = []
                        for url in downloadChapterSessionInfo['imagesURLs']:
                            urls.append(url)

                        sessionDownloader = MangaChapterSessionDownloader(urls, downloadSessionId,
                                                                            self.chapterProgressInfo,
                                                                            self.chapterDownloadSessionComplete,
                                                                            self.chapterDownloadSessionFailed,
                                                                            folder)

                        downloadChapterSessionInfo['chapterSessionDownloader'] = sessionDownloader
                        downloadSession['downloadChapterSessionsInfo'][currentChapter] = downloadChapterSessionInfo

                        sessionDownloader.startDownloadSession()
                    else:
                        downloadSessionComplete = downloadSession['downloadSessionComplete']
                        downloadSession['downloadComplete'] = True

                    progressInfo = downloadSession['progressInfo']
                    chapterProgressInfo = downloadSession['chapterProgressInfo']
                    chapterDownloadSessionComplete = downloadSession['chapterDownloadSessionComplete']

                    self.downloadSessions[downloadSessionId] = downloadSession

        if chapterProgressInfo is not None:
            chapterProgressInfo(downloadSessionId, currentChapterName, percent)

        if progressInfo is not None:
            # print "WELL WELL WELL " + str(totalProgress)
            progressInfo(downloadSessionId, totalProgress)

        if chapterDownloadSessionComplete is not None:
            chapterDownloadSessionComplete(downloadSessionId, currentChapterName, currentChapterFolder, mangaIndex, mangaPreviousDate)

        if downloadSessionComplete is not None:
            downloadSessionComplete(downloadSessionId)

    def chapterDownloadSessionFailed(self, downloadSessionId):
        print "Chapter Download failed"
        downloadSessionFailed = None
        with self.sessionLock:
            if downloadSessionId is not None:
                downloadSession = self.downloadSessions.get(downloadSessionId, None)
                if downloadSession is not None:
                    downloadSessionFailed = downloadSession['downloadSessionFailed']
                    downloadSession['downloadInProgress'] = False
                    downloadSession['downloadComplete'] = False
                    currentChapter = downloadSession['currentChapter']
                    currentChapterName = downloadSession['chapterNames'][currentChapter]

        if downloadSessionFailed is not None:
            downloadSessionFailed(downloadSessionId, currentChapterName)

    def pauseDownloadChapters(self, downloadSessionId):

        with self.sessionLock:
            downloadSession = self.downloadSessions.get(downloadSessionId, None)
            if downloadSession is not None and downloadSession['downloadInProgress'] and not downloadSession['downloadPaused'] and not downloadSession['downloadComplete']:
                # Use semaphore for page parsing situation
                # We can pause the parsing page too and need not worry abt this semaphore
                # TODO - Thoughts on the above comment
                semaphore = downloadSession['semaphore']
                semaphore.acquire()
                downloadSession['downloadPaused'] = True
                currentChapter = downloadSession['currentChapter']
                downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                sessionDownloader = downloadChapterSessionInfo['chapterSessionDownloader']

                if sessionDownloader is not None:
                    sessionDownloader.pauseDownloadSession()

    def resumeDownloadChapters(self, downloadSessionId):
        with self.sessionLock:
            downloadSession = self.downloadSessions.get(downloadSessionId, None)
            if downloadSession is not None and downloadSession['downloadInProgress'] and downloadSession['downloadPaused'] and not downloadSession['downloadComplete']:
                # Use semaphore for page parsing situation
                semaphore = downloadSession['semaphore']
                semaphore.release()
                downloadSession['downloadPaused'] = False
                currentChapter = downloadSession['currentChapter']
                downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                sessionDownloader = downloadChapterSessionInfo['chapterSessionDownloader']

                if sessionDownloader is not None:
                    sessionDownloader.resumeDownloadSession()

    def stopDownloadChapters(self, downloadSessionId):
        with self.sessionLock:
            downloadSession = self.downloadSessions.get(downloadSessionId, None)
            if downloadSession is not None:
                # No need for special structure for parsing page, removing the downloadSessionId from the list is sufficient
                print 'stopDownloadChapters - MangaStream'

                currentChapter = downloadSession['currentChapter']
                downloadChapterSessionInfo = downloadSession['downloadChapterSessionsInfo'][currentChapter]
                sessionDownloader = downloadChapterSessionInfo['chapterSessionDownloader']

                if sessionDownloader is not None:
                    sessionDownloader.stopDownloadSession()

                urls = downloadSession['chapterURLs']
                for url in urls:
                    self.downloadURLs.pop(url)

                # Completely stopped, remove it from the list
                self.downloadSessions.pop(downloadSessionId)
