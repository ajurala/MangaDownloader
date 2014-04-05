from kivy.network.urlrequest import UrlRequest
#import lxml


class MangaBackGroundDownloader():

    mangaSiteURL = {'MangaStream': 'http://mangastream.com/manga'}
    mangaSiteRequest = {}
    mangaSiteRequestInfo = {}

    def __init__(self):
        pass

    def downloadMangaList(self, mangaSite, func):
        #Request already pending then ignore
        if self.mangaSiteRequest.get(mangaSite, None) is None:
            print "Yeah started ..."
            url = self.mangaSiteURL.get(mangaSite, None)
            if url is not None:
                req = UrlRequest(url, self.downloadMangaSuccess)
                #print req

                self.mangaSiteRequest[mangaSite] = 'Y'

                requestInfo = {}
                requestInfo['mangaSite'] = mangaSite
                requestInfo['func'] = func

                self.mangaSiteRequestInfo[req] = requestInfo

                #if self.mangaSiteRequestInfo.get(req, None) is None:
                #    print "woah why none"

    def downloadMangaSuccess(self, req, result):
        #print req
        requestInfo = self.mangaSiteRequestInfo.get(req, None)
        
        #parse.
        print requestInfo

        if requestInfo is not None:
            func = requestInfo['func']

            self.mangaSiteRequest.pop(requestInfo['mangaSite'])
            self.mangaSiteRequestInfo.pop(req)

            func(['Aj', 'Ur'])
