from threading import Lock
import MangaURLDownloader
import MangaUtils

class MangaChapterSessionDownloader():

    def __init__(self, urls, downloadSessionId, progressInfo, downloadSessionComplete, folder):
        # Save these info

        self.toDownloadUrls = urls
        self.progressInfo = progressInfo
        self.downloadSessionComplete = downloadSessionComplete
        self.downloadSessionId = downloadSessionId
        self.folder = folder
        self.urlCount = len(urls)

        print urls

        # Create the folder
        MangaUtils.mkdir_p(folder)

        #List of responses that are being download
        self.downloadingUrls = {}

        self.parallelUrlDownloads = 4

        self.lock = Lock()

    def startResumeDownloadSession(self):
        #Start Or Resume the download
        #Once failure count reaches 0, do not continue with the session and wait for reinitialisation
        print "Start to download a chapter"
        with self.lock:
            self.failureCount = 4

            for i in range(self.parallelUrlDownloads):
                url = self.toDownloadUrls.pop(0)

                response = MangaURLDownloader.downloadUrl(url, self.urlDownloadComplete, self.folder, failDownload=self.failedDownload)
                self.downloadingUrls[response] = url

    def urlDownloadComplete(self, response, result):
        # Send a proper progress/complete info to the requester
        with self.lock:
            url = self.downloadingUrls.get(response, None)
            print "Downloading of url " + url + " complete"
            if url is not None:
                self.downloadingUrls.pop(response)

            # Calculate the percent and pass on the information
            toDownloadCount = len(self.toDownloadUrls)
            totalToDownloadCount = toDownloadCount + len(self.downloadingUrls)
            downloadCompletedCount = self.urlCount - totalToDownloadCount
            percent =  int((float(downloadCompletedCount)/float(self.urlCount))*100.0)

            if toDownloadCount > 0:
                url = self.toDownloadUrls.pop(0)

                response = MangaURLDownloader.downloadUrl(url, self.urlDownloadComplete, self.folder)
                self.downloadingUrls[response] = url

            # This can be done outside lock too.
            # But on calling callback within lock will make sure that UI updates happen
            # first and then next downloads resume
            print "To Download or downloading ... " + str(totalToDownloadCount)
            if totalToDownloadCount == 0:
                self.downloadSessionComplete(self.downloadSessionId)
            else:
                self.progressInfo(self.downloadSessionId, downloadCompletedCount, percent)

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
