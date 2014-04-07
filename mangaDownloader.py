__author__ = 'aj'

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.adapters.listadapter import ListAdapter

import string
import random
import mangaViewDefines
import MangaBackGroundDownloader

#data = [str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))) for i in range(1000, 1020)]

#cdata = [str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))) for i in range(100, 105)]

#ddata = [{'text':str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))),
#'mangaInfotext': 'Manga Info',
#'chapterInfotext': 'Chapter Info',
#'mangaProgress': 40,
#'chapterProgress': 95} for i in range(100, 105)]

mangaDownloaderInstance = None


class MangaDownloader(TabbedPanel):

    mangaBackGroundDownloader = None

    downloadMangaChapters = {}

    toDownloadUrls = []
    toDownloadManga = ""

    downloadingMangasIds = {}
    downloadingMangasSelected = []
    ddata = []

    currentMangaSite = "MangaStream"

    args_converter = lambda row_index, rec: {
        'text': rec['name'],
        'size_hint_y': None,
        'height': 25,
        'shorten': 'true',
        'valign': 'middle',
        'halign': 'left',
        'url': rec['url']
    }

    list_adapter = ListAdapter(data=[],
                               args_converter=args_converter,
                               template='MangaButton',
                               #cls=ListItemButton,
                               selection_mode='single',
                               allow_empty_selection=True)

    cargs_converter = lambda row_index, rec: {
        'text': rec['name'],
        'on_active': on_chapterselect_checkbox_active,
        'url': rec['url']
    }

    chapterlist_adapter = ListAdapter(data=[],
                                      args_converter=cargs_converter,
                                      template='Chapter',
                                      selection_mode='none',
                                      allow_empty_selection=True)

    dargs_converter = lambda row_index, rec: {
        'text': rec['text'],
        'mangaInfotext': rec['mangaInfotext'],
        'chapterInfotext': rec['chapterInfotext'],
        'mangaProgress': rec['mangaProgress'],
        'chapterProgress': rec['chapterProgress'],
        'on_active': on_down_checkbox_active,
        'mangaName': rec['text'],
        'downloadSessionId': rec['downloadSessionId']
    }

    downloadlist_adapter = ListAdapter(data=[],
                                       args_converter=dargs_converter,
                                       template='MangaDownload',
                                       selection_mode='none',
                                       allow_empty_selection=True)

    def __init__(self):
        TabbedPanel.__init__(self)
        
        self.mangaBackGroundDownloader = MangaBackGroundDownloader.MangaBackGroundDownloader()

        self.list_adapter.bind(on_selection_change=self.mangaSelected)

        self.ids.downloadChapters.bind(on_press=self.downloadChapters)
        self.ids.getMangaList.bind(on_press=self.downloadMangaList)

        self.ids.pause.bind(on_press=self.pauseCancelDownloads)
        self.ids.pauseAll.bind(on_press=self.pauseCancelDownloads)
        self.ids.cancel.bind(on_press=self.pauseCancelDownloads)
        self.ids.cancelAll.bind(on_press=self.pauseCancelDownloads)

        self.mangaBackGroundDownloader.getMangaList(self.currentMangaSite, self.updateMangaList)

    def downloadMangaList(self, instance):
        #update Listview
        print "Will update listview now ..."

        self.mangaBackGroundDownloader.downloadMangaList(self.currentMangaSite, self.updateMangaList)

    def updateMangaList(self, mangaSite, mangaList):
        print 'updated the list ... '
        data = mangaList
        self.list_adapter.data = data
        self.ids.mangaList.populate()

    def mangaSelected(self, list_adapter, *args):
        if len(list_adapter.selection) == 1:
            selected_object = list_adapter.selection[0]
            selectedManga = selected_object.text
            if selectedManga != self.toDownloadManga:
                self.ids.labelManga.text = "Selected Manga " + selectedManga
                #Update the list of available chapters

                #Show progress screen
                self.ids.mangasScreenManager.current = 'ChapterListProgress'

                self.toDownloadManga = selected_object.text
                self.toDownloadUrls = []

                self.mangaBackGroundDownloader.downloadChapterList(self.currentMangaSite, selected_object.url, self.updateChapterList)

    def updateChapterList(self, mangaSite, chapterList):
        print 'updated the chapter list ... '
        data = chapterList
        self.chapterlist_adapter.data = data
        self.ids.chapterList.populate()
        #Show the list view screen now
        self.ids.mangasScreenManager.current = 'ChapterList'

    def downloadChapters(self, instance):
        downloadSessionId = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

        while self.downloadingMangasIds.get(downloadSessionId, None) is not None:
            downloadSessionId = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

        self.toDownloadUrls = self.mangaBackGroundDownloader.loadDownloadChapters(self.currentMangaSite,
                                                                              self.toDownloadManga,
                                                                              self.toDownloadUrls,
                                                                              downloadSessionId,
                                                                              self.downloadingProgress)

        if len(self.toDownloadUrls) > 0:
          #Update downloading data with this instance. Pass the unique id for it
          downloadSession = {}

          downloadSession['text'] = self.currentMangaSite
          downloadSession['mangaInfotext'] = self.toDownloadManga + " 1/" + str(len(self.toDownloadUrls))
          downloadSession['chapterInfotext'] = ""
          downloadSession['mangaProgress'] = 0
          downloadSession['chapterProgress'] = 0
          downloadSession['mangaName'] = self.toDownloadManga
          downloadSession['numberOfChapters'] = len(self.toDownloadUrls)

          downloadSession['downloadSessionId'] = downloadSessionId

          #self.ddata.append(downloadSession)
          #self.downloadingMangasIds[downloadSessionId] = len(self.ddata) - 1

          self.downloadlist_adapter.data.append(downloadSession)
          self.downloadingMangasIds[downloadSessionId] = len(self.downloadlist_adapter.data) - 1

          self.ids.downloadList.populate()

          self.mangaBackGroundDownloader.startResumeDownloadChapters(downloadSessionId)

    def downloadingProgress(self, downloadSessionId, chapterProgress):
        pass

    def on_chapterselect_checkbox_active(self, checkbox, value):
        if value:
            self.toDownloadUrls.append(checkbox.url)
        else:
            self.toDownloadUrls.remove(checkbox.url)

    def on_down_checkbox_active(self, checkbox, value):
        if value:
            self.downloadingMangasSelected.append(checkbox.downloadSessionId)
        else:
            self.downloadingMangasSelected.remove(checkbox.downloadSessionId)
        print self.downloadingMangasSelected

    def pauseCancelDownloads(self, instance):
        if instance == self.ids.pause:
            print "pause called"
        elif instance == self.ids.pauseAll:
            print "pause all called"
        elif instance == self.ids.remove:
            print "cancel called"
        elif instance == self.ids.removeAll:
            print "cancel all called"
        elif instance == self.ids.resume:
            print "cancel called"
        elif instance == self.ids.resumeAl:
            print "cancel all called"


class MangaDownloaderApp(App):
    def build(self):
        global mangaDownloaderInstance

        mangaDownloaderInstance = MangaDownloader()
        return mangaDownloaderInstance


def on_chapterselect_checkbox_active(checkbox, value):
    mangaDownloaderInstance.on_chapterselect_checkbox_active(checkbox, value)


def on_down_checkbox_active(checkbox, value):
    mangaDownloaderInstance.on_down_checkbox_active(checkbox, value)


if __name__ == '__main__':
    MangaDownloaderApp().run()
