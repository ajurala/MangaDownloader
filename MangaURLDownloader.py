import urllib2
import threading

urlRequests = {}
urlThreads = {}

urlLock = threading.Lock()

chunk_size = 8192


class MangaURLDownloader(threading.Thread):

    def __init__(self, response):
        threading.Thread.__init__(self)
        self.response = response
        self.stopDownload = False

        self.semaphore = threading.BoundedSemaphore()

    def run(self):
        with urlLock:
            urlThreadInfo = urlThreads.get(self.response, None)

        if urlThreadInfo is not None:
            result = ""

            total_size = self.response.info().getheader('Content-Length')
            if total_size is not None:
                total_size = int(total_size.strip())
            bytes_so_far = 0

            finishCallback = urlThreadInfo['finishCallback']
            file = urlThreadInfo['file']
            progressCallback = urlThreadInfo['progressCallback']
            url = urlThreadInfo['url']

            #Open file if url response to be saved in file
            if file is not None:
                fd = open(file, "wb")

            while 1:
                # If download stop issued then come out of it
                if self.stopDownload:
                    break

                # If semaphore not acquired then it pauses the thread automatically
                # TODO - What to do about situations where timeout happens for reading chunk
                # as it was paused for a long time ???
                with self.semaphore:
                    pass

                chunk = self.response.read(chunk_size)
                bytes_so_far += len(chunk)

                if not chunk:
                    break

                if file is not None:
                    fd.write(chunk)
                else:
                    result += chunk

                if total_size is not None and progressCallback is not None:
                    percent = float(bytes_so_far) / total_size
                    percent = round(percent*100, 2)

                    progressCallback(self.response, percent)

            # Remove the references now as either the download is complete or stopped
            urlRequests.pop(url)
            urlThreads.pop(self.response)

            # if stop was not issued and callback present then call it
            if not self.stopDownload and finishCallback:
                finishCallback(self.response, result)
        else:
            return


def downloadUrl(url, finishCallback, file=None, progressCallback=None):
    response = None

    if finishCallback is not None:
        response = urlRequests.get(url, None)
        if response is None:

            response = urllib2.urlopen(url)

            # Create a thread and save the info here
            thread = MangaURLDownloader(response)
            with urlLock:
                urlThreadInfo = {}
                urlThreadInfo['thread'] = thread
                urlThreadInfo['finishCallback'] = finishCallback
                urlThreadInfo['file'] = file
                urlThreadInfo['progressCallback'] = progressCallback
                urlThreadInfo['url'] = url

                urlThreads[response] = urlThreadInfo
                urlRequests[url] = response

            thread.setDaemon(True)
            thread.start()

    return response


def pauseDownload(response):
    with urlLock:
        urlThreadInfo = urlThreads.get(response, None)

    if urlThreadInfo is not None:
        thread = urlThreads['thread']
        # Call to acquire should lock the resource and hence should pause the chunk request
        thread.semaphore.acquire()
        return True

    return False


def resumeDownload(response):
    with urlLock:
        urlThreadInfo = urlThreads.get(response, None)

    if urlThreadInfo is not None:
        thread = urlThreads['thread']
        # Call to acquire should lock the resource and hence should pause the chunk request
        try:
            thread.semaphore.release()
        except ValueError:
            pass

        return True

    return False


def stopDownload(response):
    with urlLock:
        urlThreadInfo = urlThreads.get(response, None)

    if urlThreadInfo is not None:
        thread = urlThreads['thread']
        # set the stopDownload to true, and the thread before next chunk read will stop the download
        thread.stopDownload = True
        return True

    return False
