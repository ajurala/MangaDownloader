from threading import Lock
import MangaURLDownloader
import MangaUtils

class MangaChapterSessionDownloader():

    def __init__(self, urls, downloadSessionId, progressInfo, downloadSessionComplete, failedDownload, folder):
        # Save these info

        self.toDownloadUrls = urls
        self.progressInfo = progressInfo
        self.downloadSessionComplete = downloadSessionComplete
        self.failedDownload = failedDownload
        self.downloadSessionId = downloadSessionId
        self.folder = folder
        self.urlCount = len(urls)

        print urls

        # Create the folder
        MangaUtils.mkdir_p(folder)

        #List of responses that are being download
        self.downloadingUrls = {}

        self.lock = Lock()

        self.parallelUrlDownloads = 4

        self.downloadInProgress = False

    def startResumeDownloadSession(self):
        #Start Or Resume the download
        #Once failure count reaches 0, do not continue with the session and wait for reinitialisation
        print "Start to download a chapter"
        with self.lock:
            if not self.downloadInProgress:
                self.downloadInProgress = True
                self.failureCount = 10

                parallelUrlDownloads = self.parallelUrlDownloads

                for i in range(parallelUrlDownloads):
                    url = self.toDownloadUrls.pop(0)

                    response = MangaURLDownloader.downloadUrl(url, self.urlDownloadComplete, self.folder, failDownload=self.failedDownload)
                    self.downloadingUrls[response] = url
                    self.parallelUrlDownloads -= 1

    def urlDownloadComplete(self, response, result):
        # Send a proper progress/complete info to the requester
        with self.lock:
            url = self.downloadingUrls.get(response, None)
            print "Downloading of url " + url + " complete"
            if url is not None:
                self.downloadingUrls.pop(response)

            self.parallelUrlDownloads += 1

            # Calculate the percent and pass on the information
            toDownloadCount = len(self.toDownloadUrls)
            totalToDownloadCount = toDownloadCount + len(self.downloadingUrls)
            downloadCompletedCount = self.urlCount - totalToDownloadCount
            percent = int((float(downloadCompletedCount)/float(self.urlCount))*100.0)

            if toDownloadCount > 0 and self.failureCount > 0:
                url = self.toDownloadUrls.pop(0)

                response = MangaURLDownloader.downloadUrl(url, self.urlDownloadComplete, self.folder)
                self.downloadingUrls[response] = url
                self.parallelUrlDownloads -= 1

            downloadSessionComplete = self.downloadSessionComplete
            progressInfo = self.progressInfo
            failDownload = None

            downloadSessionId = self.downloadSessionId

            if self.failureCount <= 0:
                self.downloadInProgress = False
                failDownload = self.failedDownload

        print "To Download or downloading ... " + str(totalToDownloadCount)
        if totalToDownloadCount == 0:
            downloadSessionComplete(self.downloadSessionId)
        else:
            progressInfo(self.downloadSessionId, downloadCompletedCount, percent)

        if failDownload is not None:
            failDownload(downloadSessionId)

    def urlProgressInfo(self, response):
        # Send a proper progress info to the requester
        # This can be looked at later to give precise progress information
        pass

    def failedDownload(self, response):
        with self.lock:
            self.failureCount -= 1

            url = self.downloadingUrls.get(response, None)
            self.toDownloadUrls.append(url)

            if url is not None:
                self.downloadingUrls.pop(response)
