__author__ = 'aj'

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.adapters.listadapter import ListAdapter

import string
import random
import mangaViewDefines

data = [str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))) for i in range(1000, 1020)]

cdata = [str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))) for i in range(100, 105)]

ddata = [{'text':str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))),
'mangaInfotext': 'Manga Info',
'chapterInfotext': 'Chapter Info',
'mangaProgress': 40,
'chapterProgress': 95} for i in range(100, 105)]

mangaDownloaderInstance = None


class MangaDownloader(TabbedPanel):

    downloadMangaChapters = {}

    toDownloadUrls = []
    downloadingMangas = []
    downloadManga = ""

    args_converter = lambda row_index, rec: {
        'text': rec,
        'size_hint_y': None,
        'height': 25,
        'shorten': 'true',
        'valign': 'middle',
        'halign': 'left'
    }

    list_adapter = ListAdapter(data=data,
                               args_converter=args_converter,
                               template='MangaButton',
                               #cls=ListItemButton,
                               selection_mode='single',
                               allow_empty_selection=False)

    cargs_converter = lambda row_index, rec: {
        'text': rec,
        'on_active': on_chapterselect_checkbox_active,
        'url': 'this is an url ... for ' + rec
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
        'mangaName': 'this is an url ... for ... ' + rec['text']
    }

    downloadlist_adapter = ListAdapter(data=ddata,
                                       args_converter=dargs_converter,
                                       template='MangaDownload',
                                       selection_mode='none',
                                       allow_empty_selection=True)

    def __init__(self):
        TabbedPanel.__init__(self)
        
        self.list_adapter.bind(on_selection_change=self.mangaSelected)

        self.ids.downloadChapters.bind(on_press=self.downloadChapters)
        self.ids.getMangaList.bind(on_press=self.downloadMangaList)

        self.ids.pause.bind(on_press=self.pauseCancelDownloads)
        self.ids.pauseAll.bind(on_press=self.pauseCancelDownloads)
        self.ids.cancel.bind(on_press=self.pauseCancelDownloads)
        self.ids.cancelAll.bind(on_press=self.pauseCancelDownloads)

    def downloadMangaList(self, instance):
        #update Listview
        print "Will update listview here ..."

    def mangaSelected(self, list_adapter, *args):
        if len(list_adapter.selection) == 1:

            selected_object = list_adapter.selection[0]

            self.ids.labelManga.text = "Selected Manga "+selected_object.text
            #Update the list of available chapters

            #Show progress screen
            self.ids.mangasScreenManager.current = 'ChapterListProgress'

            ndata = [str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))) for i in range(100, 105)]

            #Start a thread which gets the chapter and sets the data and shows the appropriate screen
            #print ndata
            self.chapterlist_adapter.data = ndata
            self.ids.chapterList.populate()

            self.downloadManga = selected_object.text
            self.downloadUrls = []            

            #Show the list view screen now
            self.ids.mangasScreenManager.current = 'ChapterList'

    def downloadChapters(self, instance):
        pass

    def on_chapterselect_checkbox_active(self, checkbox, value):
        if value:
            self.toDownloadUrls.append(checkbox.url)
        else:
            self.toDownloadUrls.remove(checkbox.url)

    def on_down_checkbox_active(self, checkbox, value):
        if value:
            self.downloadingMangas.append(checkbox.mangaName)
        else:
            self.downloadingMangas.remove(checkbox.mangaName)
        print self.downloadingMangas

    def pauseCancelDownloads(self, instance):
        if instance == self.ids.pause:
            print "pause called"
        elif instance == self.ids.pauseAll:
            print "pause all called"
        if instance == self.ids.cancel:
            print "cancel called"
        elif instance == self.ids.cancelAll:
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


