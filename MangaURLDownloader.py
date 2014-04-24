import os
import socket
import urllib2
import threading

from threading import Timer
from urllib2 import urlparse

urlRequests = {}
urlThreads = {}

urlLock = threading.Lock()

chunk_size = 8192

# proxy_enable = False
# proxy_url = ""
# proxy_port = ""

class MangaURLDownloader(threading.Thread):

    def __init__(self, requestId, url, finishCallback, folder, progressCallback, failDownload, file):
        threading.Thread.__init__(self)

        urlThreadInfo = {}
        urlThreadInfo['thread'] = self
        with urlLock:
            urlRequests[url] = requestId
            urlThreads[requestId] = urlThreadInfo

        self.finishCallback = finishCallback
        self.folder = folder
        self.progressCallback = progressCallback
        self.failDownload = failDownload
        self.url = url
        self.requestId = requestId
        self.stopDownload = False
        self.file = file

        self.semaphore = threading.BoundedSemaphore()

        self.failed = False

    def readTimeout(self, response):
        print "readTimeout called"
        response.close()

    def run(self):
        print "Starting to download " + self.url

        finishCallback = self.finishCallback
        folder = self.folder
        progressCallback = self.progressCallback
        url = self.url
        file = self.file
        try:
            user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
            req = urllib2.Request(self.url, headers={'User-Agent': user_agent})
            # timeout after 10 seconds
            timeout = 10.0
            self.response = urllib2.urlopen(req, None, timeout)
        except urllib2.URLError:
            # TODO - Log such issues
            print "could not open the url " + self.url
            self.response = None
            self.failed = True
        except socket.timeout:
            print "could not open the url due to timeout " + self.url
            self.response = None
            self.failed = True
        except Exception as e:
            print "Generic Exception " + self.url
            print e
            self.response = None
            self.failed = True

        if self.response is not None:
            result = ""

            total_size = self.response.info().getheader('Content-Length')
            if total_size is not None:
                total_size = int(total_size.strip())
            bytes_so_far = 0

            fileNotDownloaded = True
            #Open file if url response to be saved in file
            if folder is not None:
                if file is not None:
                    urlSplitList = urlparse.urlsplit(url)
                    urlPath = urlSplitList[2]
                    file = urlPath.split('/')[-1]

                file = os.path.join(folder, file)

                # Check for file size ...
                if os.path.exists(file):
                    currentSize = os.path.getsize(file)
                    print file
                    print total_size
                    print currentSize
                    if total_size is not None and total_size == currentSize:
                        fileNotDownloaded = False

            if fileNotDownloaded:
                if folder is not None:
                    fd = open(file, "wb")
                timeout = 20
                while 1:
                    # If download stop issued then come out of it
                    if self.stopDownload:
                        break

                    # If semaphore not acquired then it pauses the thread automatically
                    # TODO - What to do about situations where timeout happens for reading chunk
                    # as it was paused for a long time ???
                    with self.semaphore:
                        pass

                    t = Timer(timeout, self.readTimeout, [self.response])
                    t.start()

                    try:
                        chunk = self.response.read(chunk_size)
                    except:
                        self.failed = True
                        chunk = None

                    t.cancel()

                    if not chunk:
                        break

                    bytes_so_far += len(chunk)

                    if folder is not None:
                        fd.write(chunk)
                    else:
                        result += chunk

                    if total_size is not None and progressCallback is not None:
                        percent = float(bytes_so_far) / total_size
                        percent = round(percent * 100.0, 2)

                        progressCallback(self.requestId, percent)
            else:
                print "File already downloaded "+self.url
        # Remove the references now as either the download is complete or stopped
        if url is not None:
            urlRequests.pop(url)
        urlThreads.pop(self.requestId)

        # if stop was not issued and callback present then call it
        if self.failed and self.failDownload is not None:
            self.failDownload(self.requestId)
        elif not self.failed and not self.stopDownload and finishCallback is not None:
            finishCallback(self.requestId, result)

class MangaURL():
    def __init__(self, url):
        self.url = url

    def geturl(self):
        return self.url

def downloadUrl(url, finishCallback, folder=None, progressCallback=None, failDownload=None, file=None):
    requestId = None

    if finishCallback is not None:
        with urlLock:
            requestId = urlRequests.get(url, None)

        if requestId is None:
            requestId = MangaURL(url)

            # Start a thread which saves info
            thread = MangaURLDownloader(requestId, url, finishCallback, folder, progressCallback, failDownload, file)

            thread.setDaemon(True)
            thread.start()

    return requestId


def pauseDownload(requestId):
    with urlLock:
        urlThreadInfo = urlThreads.get(requestId, None)

    if urlThreadInfo is not None:
        thread = urlThreadInfo['thread']

        # Call to acquire should lock the resource and hence should pause the chunk request
        thread.semaphore.acquire()
        return True

    return False


def resumeDownload(requestId):
    with urlLock:
        urlThreadInfo = urlThreads.get(requestId, None)

    if urlThreadInfo is not None:
        thread = urlThreadInfo['thread']
        # Call to acquire should lock the resource and hence should pause the chunk request
        try:
            thread.semaphore.release()
        except ValueError:
            pass

        return True

    return False


def stopDownload(requestId):
    with urlLock:
        urlThreadInfo = urlThreads.get(requestId, None)

    if urlThreadInfo is not None:
        thread = urlThreads['thread']
        # set the stopDownload to true, and the thread before next chunk read will stop the download
        thread.stopDownload = True
        return True

    return False

def setProxyInfo(proxy_enable, proxy_url, proxy_port):
        # self.proxy_enable = proxy_enable
        # self.proxy_url = proxy_url
        # self.proxy_port = proxy_port

        if proxy_enable:
            proxy = urllib2.ProxyHandler({'http': proxy_url + ":" + proxy_port})
        else:
            proxy = urllib2.ProxyHandler({})

        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
