from MangaStreamDownloader import MangaStreamDownloader


class MangaBackGroundDownloader():

    mangaSites = {'MangaStream': MangaStreamDownloader()}
    mangaSiteRequestInfo = {}
    chapterRequestInfo = {}
    downloadRequestInfo = {}

    def __init__(self):
        pass

    def downloadMangaList(self, mangaSite, func):
        #Request already pending then ignore
        mangaObj = self.mangaSites.get(mangaSite, None)

        if mangaObj is not None and not mangaObj.isRequestPending():

            mangaObj.downloadMangaList(self.mangaListCallBack)

            self.mangaSiteRequestInfo[mangaSite] = func

    def getMangaList(self, mangaSite, func):
        mangaObj = self.mangaSites.get(mangaSite, None)
        func(mangaSite, mangaObj.getMangaList())

    def mangaListCallBack(self, mangaSite, mangaList):
        callbackFunc = self.mangaSiteRequestInfo.get(mangaSite, None)

        if callbackFunc is not None:
            self.mangaSiteRequestInfo.pop(mangaSite)
            callbackFunc(mangaSite, mangaList)

    def downloadChapterList(self, mangaSite, url, func):
        mangaObj = self.mangaSites.get(mangaSite, None)

        if mangaObj is not None:

            # This call below might be needed in future - Keep it
            #mangaObj.stopPendingChapterRequests()

            mangaObj.downloadChapterList(url, self.chapterListCallBack)

            self.chapterRequestInfo[mangaSite] = func

    def chapterListCallBack(self, mangaSite, mangaList):
        callbackFunc = self.chapterRequestInfo.get(mangaSite, None)

        if callbackFunc is not None:
            self.chapterRequestInfo.pop(mangaSite)
            callbackFunc(mangaSite, mangaList)

    def loadDownloadChapters(self, mangaSite, manga, urls, downloadSessionId, func):
        mangaObj = self.mangaSites.get(mangaSite, None)

        if mangaObj is not None:
            #Call download for these urls
            downloadRequest = {}
            downloadRequest['mangaObj'] = mangaObj
            downloadRequest['func'] = func
            self.downloadRequestInfo[downloadSessionId] = downloadRequest

            #The manga site will return the urls
            return urls

        return []

    def startResumeDownloadChapters(self, downloadSessionId):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            mangaObj = downloadRequest['mangaObj']
            #Start resume to the download now