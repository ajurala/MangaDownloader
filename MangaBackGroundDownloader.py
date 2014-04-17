import os
import shutil
import zipfile
import MangaURLDownloader

from MangaStreamDownloader import MangaStreamDownloader


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

    def loadDownloadChapters(self, mangaSite, manga, urlsInfo, downloadSessionId, func):
        mangaObj = self.mangaSites.get(mangaSite, None)

        if mangaObj is not None:

            folder = os.path.join(self.downloadPath, mangaSite, manga)

            #Call download for these urls
            downloadRequest = {}
            downloadRequest['mangaObj'] = mangaObj
            downloadRequest['func'] = func
            downloadRequest['mangaSite'] = mangaSite
            downloadRequest['manga'] = manga
            downloadRequest['sessionPercent'] = 0
            downloadRequest['chapterSessionPercent'] = 0

            #The manga site will return the urls
            urls = mangaObj.loadDownloadChapters(urlsInfo, downloadSessionId,
                                                    self.progressInfo, self.downloadSessionComplete, self.downloadSessionFailed,
                                                    self.chapterProgressInfo, self.chapterDownloadSessionComplete,
                                                    folder)

            if len(urls) > 0:
                self.downloadRequestInfo[downloadSessionId] = downloadRequest

            return urls

        return []

    def startResumeDownloadChapters(self, downloadSessionId):
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            mangaObj = downloadRequest['mangaObj']

            #Start resume to the download now
            mangaObj.startResumeDownloadChapters(downloadSessionId)

    def progressInfo(self, downloadSessionId, percent):
        pass

    def downloadSessionComplete(self, downloadSessionId):
        # Remove the session on complete
        if self.downloadRequestInfo.get(downloadSessionId, None) is not None:
            self.downloadRequestInfo.pop(downloadSessionId)

    def downloadSessionFailed(self, downloadSessionId):
        # Tell the UI that it has to show some proper message
        downloadRequest = self.downloadRequestInfo.get(downloadSessionId, None)

        if downloadRequest is not None:
            func = downloadRequest['func']
            # Call the func to update UI


    def chapterProgressInfo(self, downloadSessionId, percent):
        pass

    def chapterDownloadSessionComplete(self, downloadSessionId, folder):

        if self.config.get('manga', 'download_as') == "CBZ":
            # Zip the folder and create the cbz
            fileCBZ = folder+'.cbz'

            # Delete the cbz first
            os.remove(fileCBZ)
            cbzf = zipfile.ZipFile(fileCBZ, 'w')
            self.cbzdir(folder, cbzf)
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

    def cbzdir(self, path, cbz):
        for root, dirs, files in os.walk(path):
            for file in files:
                cbzFileItem = os.path.join(root, file)
                cbz.write(cbzFileItem, os.path.relpath(cbzFileItem, os.path.join(path, '.')))
