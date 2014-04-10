__author__ = 'aj'

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', 0)

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.settings import SettingsWithSidebar
from kivy.uix.settings import SettingsWithTabbedPanel

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

    config = None

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

        self.ids.pauseDownloadSession.bind(on_press=self.pauseCancelDownloads)
        self.ids.pauseAllDownloadSession.bind(on_press=self.pauseCancelDownloads)
        self.ids.removeDownloadSession.bind(on_press=self.pauseCancelDownloads)
        self.ids.removeAllDownloadSession.bind(on_press=self.pauseCancelDownloads)
        self.ids.resumeDownloadSession.bind(on_press=self.pauseCancelDownloads)
        self.ids.resumeAllDownloadSession.bind(on_press=self.pauseCancelDownloads)

        self.mangaBackGroundDownloader.getMangaList(self.currentMangaSite, self.updateMangaList)


        #Build the settings page
        self.settings = SettingsWithSidebar()
        self.settings.interface.menu.remove_widget(self.settings.interface.menu.close_button)
        app = App.get_running_app()
        self.config = app.load_config()
        self.settings.add_json_panel('Proxy Settings', app.load_config(), 'proxy_settings.json')
        self.ids.optionTab.add_widget(self.settings)

        self.mangaBackGroundDownloader.setConfig(self.config)

    def downloadMangaList(self, instance):
        #update Listview
        self.mangaBackGroundDownloader.downloadMangaList(self.currentMangaSite, self.updateMangaList)

    def updateMangaList(self, mangaSite, mangaList):
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

    def pauseCancelDownloads(self, instance):
        if instance == self.ids.pauseDownloadSession:
            print "pause called"
        elif instance == self.ids.pauseAllDownloadSession:
            print "pause all called"
        elif instance == self.ids.removeDownloadSession:
            print "remove called"
        elif instance == self.ids.removeAllDownloadSession:
            print "remove all called"
        elif instance == self.ids.resumeDownloadSession:
            print "resume called"
        elif instance == self.ids.resumeAllDownloadSession:
            print "resume all called"



class MangaDownloaderApp(App):
    def build(self):
        global mangaDownloaderInstance
        self.use_kivy_settings = False

        mangaDownloaderInstance = MangaDownloader()
        return mangaDownloaderInstance

    def build_config(self, config):
        config.setdefaults('proxy', {
            'toggle_proxy': False,
            'proxy_url': "",
            'proxy_port': "8080"
        })

    def on_start(self):
        pass

    def on_stop(self):
        pass


def on_chapterselect_checkbox_active(checkbox, value):
    mangaDownloaderInstance.on_chapterselect_checkbox_active(checkbox, value)


def on_down_checkbox_active(checkbox, value):
    mangaDownloaderInstance.on_down_checkbox_active(checkbox, value)


if __name__ == '__main__':
    MangaDownloaderApp().run()
