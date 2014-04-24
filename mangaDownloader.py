__author__ = 'aj'

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', 0)

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.settings import SettingsWithSidebar
from kivy.utils import escape_markup
from kivy.uix.popup import Popup

from threading import Lock

import os
import string
import random
import mangaViewDefines
import MangaBackGroundDownloader


mangaDownloaderInstance = None

class MangaPopup(Popup):
    def __init__(self, title, message):
        Popup.__init__(self)
        self.auto_dismiss = False
        self.title = title
        self.ids.message.text = message

        self.register_event_type('on_ok')

    def on_press_dismiss(self, *args):
        self.dismiss()
        return False

    def on_press_ok(self, *args):
        #Call events
        self.dispatch('on_ok')
        self.dismiss()
        return False

    def on_ok(self):
        pass

class MangaDownloader(TabbedPanel):

    mangaBackGroundDownloader = None

    downloadUILock = Lock()

    downloadMangaChapters = {}

    toDownloadUrls = []
    toDownloadManga = ""

    downloadingMangasIds = {}

    downloadingMangasSelected = []

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
        'downloadSessionId': rec['downloadSessionId'],
        'downloadCompleted': rec['downloadCompleted'],
        'disabled': rec['downloadCompleted'],
        'active': rec['checked']
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
        self.settings.add_json_panel('Manga Settings', self.config, 'manga_settings.json')
        self.settings.add_json_panel('Proxy Settings', self.config, 'proxy_settings.json')
        self.ids.optionTab.add_widget(self.settings)

        self.mangaBackGroundDownloader.setConfig(self.config)

        self.settings.bind(on_config_change=self.on_config_change)
        self.setDownloadPath()
        self.setProxyInfo()

    def on_config_change(self, instance, config, section, key, value):
        if instance is self.settings and config is self.config:
            if section == "proxy":
                self.setProxyInfo()
            if section == "manga" and key == "download_folder":
                self.setDownloadPath()

    def setDownloadPath(self):
        self.mangaBackGroundDownloader.setDownloadPath(self.config.get('manga', 'download_folder'))

    def setProxyInfo(self):
        proxy_enable = self.config.get('proxy', 'proxy_enable') == "1"
        proxy_url = self.config.get('proxy', 'proxy_url')
        proxy_port = self.config.get('proxy', 'proxy_port')

        self.mangaBackGroundDownloader.setProxyInfo(proxy_enable, proxy_url, proxy_port)

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
                #self.ids.mangasScreenManager.current = 'ChapterList'
                self.ids.mangasScreenManager.current = 'ChapterListProgress'

                self.toDownloadManga = selected_object.text
                self.toDownloadUrls = []
                print "Starting to download now ..."

                self.mangaBackGroundDownloader.downloadChapterList(self.currentMangaSite, selected_object.url, self.updateChapterList)

    def updateChapterList(self, mangaSite, chapterList):
        data = chapterList
        self.chapterlist_adapter.data = data
        self.ids.chapterList.populate()
        #Show the list view screen now
        self.ids.mangasScreenManager.current = 'ChapterList'

    def downloadChapters(self, instance):

        with self.downloadUILock:
            downloadSessionId = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

            while self.downloadingMangasIds.get(downloadSessionId, None) is not None:
                downloadSessionId = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

            urls = self.mangaBackGroundDownloader.loadDownloadChapters(self.currentMangaSite,
                                                                                  self.toDownloadManga,
                                                                                  self.toDownloadUrls,
                                                                                  downloadSessionId,
                                                                                  self.downloadingProgress)

            if len(urls) > 0:
                #Update downloading data with this instance. Pass the unique id for it
                downloadSession = {}

                downloadSession['text'] = self.currentMangaSite
                downloadSession['mangaInfotext'] = self.toDownloadManga + " 1/" + str(len(urls))
                downloadSession['chapterInfotext'] = ""
                downloadSession['mangaProgress'] = 0
                downloadSession['chapterProgress'] = 0

                downloadSession['mangaSite'] = self.currentMangaSite

                downloadSession['mangaName'] = self.toDownloadManga
                downloadSession['numberOfChapters'] = len(urls)

                downloadSession['downloadSessionId'] = downloadSessionId
                downloadSession['downloadCompleted'] = False
                downloadSession['checked'] = False

                self.downloadlist_adapter.data.append(downloadSession)
                self.downloadingMangasIds[downloadSessionId] = self.downloadlist_adapter.data[-1] #len(self.downloadlist_adapter.data) - 1

                self.forceRefreshListView(self.ids.downloadList)

                self.mangaBackGroundDownloader.startDownloadChapters(downloadSessionId)

    def downloadingProgress(self, downloadSessionId, chapterProgress=None, chapterInfo=None, sessionProgress=None, mangaInfo=None, sessionFail=False, downloadCompleted=False):
        with self.downloadUILock:

            downloadSession = self.downloadingMangasIds[downloadSessionId]
            if sessionFail:
                chapterInfotext = "[b][color=ff0000]" + escape_markup("Failed to download Chapter ") + \
                                  "[color=000000]" + escape_markup(chapterInfo) + "[/color]" + \
                                  escape_markup(" Try again by clicking 'Resume' button") + "[/b][/color]"

                downloadSession['chapterInfotext'] = chapterInfotext
                self.forceRefreshListView(self.ids.downloadList)

                return

            if chapterProgress is not None:
                downloadSession['chapterProgress'] = chapterProgress

            if chapterInfo is not None:
                downloadSession['chapterInfotext'] = chapterInfo

            if mangaInfo is not None:
                downloadSession['mangaInfotext'] = mangaInfo

            if sessionProgress is not None:
                downloadSession['mangaProgress'] = sessionProgress

            #If it is not completed, then only accept any status change of complete
            if not downloadSession['downloadCompleted']:
                downloadSession['downloadCompleted'] = downloadCompleted

            self.forceRefreshListView(self.ids.downloadList)

    def forceRefreshListView(self, listview):
        listview.adapter.update_for_new_data()
        listview._trigger_reset_populate()

    def on_chapterselect_checkbox_active(self, checkbox, value):
        chapterInfo = {}
        chapterInfo['chapterName'] = checkbox.text
        chapterInfo['url'] = checkbox.url

        if value:
            self.toDownloadUrls.append(chapterInfo)
        else:
            self.toDownloadUrls.remove(chapterInfo)

    def on_down_checkbox_active(self, checkbox, value):
        downloadSessionId = checkbox.downloadSessionId
        downloadSession = self.downloadingMangasIds[downloadSessionId]

        if value:
            self.downloadingMangasSelected.append(downloadSessionId)
        else:
            self.downloadingMangasSelected.remove(downloadSessionId)

        downloadSession['checked'] = value

        print self.downloadingMangasSelected

    def pauseDownloads(self, downloadSessionIdsList):
        for downloadSessionId in downloadSessionIdsList:
            self.mangaBackGroundDownloader.pauseDownloadChapters(downloadSessionId)

        print "Done pausing provided sessions"

    def resumeDownloads(self, downloadSessionIdsList):
        for downloadSessionId in downloadSessionIdsList:
            self.mangaBackGroundDownloader.resumeDownloadChapters(downloadSessionId)

    # TODO - Remove downloads - Needs some thought on that, so will do later

    def pauseCancelDownloads(self, instance):
        if instance == self.ids.pauseDownloadSession:
            print "pause called"
            self.pauseDownloads(self.downloadingMangasSelected)
        elif instance == self.ids.pauseAllDownloadSession:
            popup = MangaPopup('Pause all', 'Are you sure you want to pause all the downloads?')
            popup.bind(on_ok=self.pause_all)
            popup.open()
        elif instance == self.ids.removeDownloadSession:
            print "remove called"
        elif instance == self.ids.removeAllDownloadSession:
            popup = MangaPopup('Remove all', 'Are you sure you want to remove all the downloads?')
            popup.bind(on_ok=self.remove_all)
            popup.open()
        elif instance == self.ids.resumeDownloadSession:
            print "resume called"
            self.resumeDownloads(self.downloadingMangasSelected)
        elif instance == self.ids.resumeAllDownloadSession:
            popup = MangaPopup('Resume all', 'Are you sure you want to resume all the downloads?')
            popup.bind(on_ok=self.resume_all)
            popup.open()

    def pause_all(self, instance):
        print "Yes we pause all"
        downloadSessionIdsList = self.downloadingMangasIds.keys()
        self.pauseDownloads(downloadSessionIdsList)

    def remove_all(self, instance):
        print "Yes we remove all"

    def resume_all(self, instance):
        print "Yes we resume all"
        downloadSessionIdsList = self.downloadingMangasIds.keys()
        self.resumeDownloads(downloadSessionIdsList)

class MangaDownloaderApp(App):
    def build(self):
        global mangaDownloaderInstance
        self.use_kivy_settings = False

        mangaDownloaderInstance = MangaDownloader()
        return mangaDownloaderInstance

    def build_config(self, config):
        config.setdefaults('proxy', {
            'proxy_enable': False,
            'proxy_url': "",
            'proxy_port': "8080"
        })


        config.setdefaults('manga', {
            'download_folder': os.getcwd(),
            'download_as': "CBZ",
            'delete_folder': False
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
