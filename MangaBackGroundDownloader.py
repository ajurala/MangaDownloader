import os
import shutil
import zipfile
import MangaURLDownloader
import MangaUtils

from MangaStreamDownloader import MangaStreamDownloader

#TODO - thread lock might be needed here

class MangaBackGroundDownloader():

    mangaSites = {'MangaStream': MangaStreamDownloader()}
    mangaSiteRequestInfo = {}
    chapterRequestInfo = {}
    downloadRequestInfo = {}
    config = None

    def __init__(self):
        self.downloadPath = "./"

    def setConfig(self, config):
        self.config = config

        for key in self.mangaSites.keys():
            mangaObj = self.mangaSites[key]
            mangaObj.setConfig(config)

    def setDownloadPath(self, downloadPath):
        self.downloadPath = downloadPath

    def setProxyInfo(self, proxy_enable, proxy_url, proxy_port):
        MangaURLDownloader.setProxyInfo(proxy_enable, proxy_url, proxy_port)

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

    def downloadChapterList(self, mangaSite, url, func, previousDate):
        mangaObj = self.mangaSites.get(mangaSite, None)

        if mangaObj is not None:

            # This call below might be needed in future - Keep it
            #mangaObj.stopPendingChapterRequests()

            mangaObj.downloadChapterList(url, self.chapterListCallBack, previousDate)

            self.chapterRequestInfo[mangaSite] = func

    def chapterListCallBack(self, mangaSite, mangaList):
        callbackFunc = self.chapterRequestInfo.get(mangaSite, None)

        if callbackFunc is not None:
            self.chapterRequestInfo.pop(mangaSite)
            callbackFunc(mangaSite, mangaList)

    def loadDownloadChapters(self, mangaSite, manga, urlsInfo, downloadSessionId, func, updateMangaDates):
        mangaObj = self.mangaSites.get(mangaSite, None)

        if mangaObj is not None:
            if self.config.get('manga', 'include_mangasite_folder') == "1":
                folder = os.path.join(self.downloadPath, mangaSite, MangaUtils.removeInvalidCharacters(manga))
            else:
                folder = os.path.join(self.downloadPath, MangaUtils.removeInvalidCharacters(manga))

            #Call download for these urls
            downloadRequest = {}
            downloadRequest['mangaObj'] = mangaObj
            downloadRequest['func'] = func
            downloadRequest['updateMangaDates'] = updateMangaDates
            downloadRequest['mangaSite'] = mangaSite
            downloadRequest['manga'] = manga
            downloadRequest['sessionPercent'] = 0
            downloadRequest['chapterSessionPercent'] = 0
            downloadRequest['totalDownloadedChapters'] = 0

            #The manga site will return the urls
            urls = mangaObj.loadDownloadChapters(manga, urlsInfo, downloadSessionId,
                                                    self.progressInfo, self.downloadSessionComplete, self.downloadSessionFailed,
                                                    self.chapterProgressInfo, self.chapterDownloadSessionComplete,
                                                    folder)

            totalChapters = len(urls)
            if totalChapters > 0:
                downloadRequest['totalChapters'] = totalChapters
                self.downloadRequestInfo[downloadSessionId] = downloadRequest

            return urls

        return []

    def startDownloadChapters(self, downloadSessionId):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            mangaObj = downloadRequest['mangaObj']

            #Start resume to the download now
            mangaObj.startDownloadChapters(downloadSessionId)

    def progressInfo(self, downloadSessionId, percent=0, mangaInfo=None):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            func = downloadRequest['func']
            func(downloadSessionId, mangaInfo=mangaInfo, sessionProgress=percent)

    def downloadSessionComplete(self, downloadSessionId):
        # Remove the session on complete
        mangaInfo = "All Chapters have been downloaded"
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)
        if downloadRequest is not None:
            func = downloadRequest['func']
            func(downloadSessionId, mangaInfo=mangaInfo, downloadCompleted=True)
            self.downloadRequestInfo.pop(downloadSessionId)

    def downloadSessionFailed(self, downloadSessionId, currentChapterName):
        # Tell the UI that it has to show some proper message
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            func = downloadRequest['func']
            func(downloadSessionId, chapterInfo=currentChapterName, sessionFail=True)

    def chapterProgressInfo(self, downloadSessionId, currentChapterName, percent=0):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            func = downloadRequest['func']
            func(downloadSessionId, chapterInfo=currentChapterName, chapterProgress=percent)

    def chapterDownloadSessionComplete(self, downloadSessionId, currentChapterName, folder, index, date):

        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)
        if downloadRequest is not None:
            func = downloadRequest['func']
            updateDates = downloadRequest['updateMangaDates']
            downloadRequest['totalDownloadedChapters'] += 1
            mangaInfo = downloadRequest['manga'] + " " + str(downloadRequest['totalDownloadedChapters']) + "/" + str(downloadRequest['totalChapters'])
            func(downloadSessionId, mangaInfo=mangaInfo, chapterInfo=currentChapterName)
            updateDates(downloadRequest['mangaSite'], index, date)

        if self.config.get('manga', 'download_as') == "CBZ":
            # Zip the folder and create the cbz
            fileCBZ = folder+'.cbz'

            # Delete the cbz first
            if os.path.isfile(fileCBZ):
                os.remove(fileCBZ)

            cbzf = zipfile.ZipFile(fileCBZ, 'w')
            MangaUtils.cbzdir(folder, cbzf)
            cbzf.close()

            delete_folder = self.config.get('manga', 'delete_folder')
            #print delete_folder
            if delete_folder == "1":
                try:
                    #print "removing folder: " + folder
                    shutil.rmtree(folder)
                except OSError as err:
                    print "Could not remove folder "+ folder
                    print err

    def pauseDownloadChapters(self, downloadSessionId):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            mangaObj = downloadRequest['mangaObj']

            #Start resume to the download now
            mangaObj.pauseDownloadChapters(downloadSessionId)

    def resumeDownloadChapters(self, downloadSessionId):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            mangaObj = downloadRequest['mangaObj']

            #Start resume to the download now
            mangaObj.resumeDownloadChapters(downloadSessionId)

    def stopDownloadChapters(self, downloadSessionId):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            mangaObj = downloadRequest['mangaObj']

            #Start resume to the download now
            mangaObj.stopDownloadChapters(downloadSessionId)

