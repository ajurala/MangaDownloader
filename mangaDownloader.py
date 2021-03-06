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
import datetime


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
        'url': rec['url'],
        'previousDate': rec['previousDate']
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
        'on_press': on_chapterselect_button_click,
        'url': rec['url'],
        'active': rec['checked'],
        'color': rec['color'],
        'date': rec['date'],
        'index': rec['index']
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

        self.ids.selectAllDownloadSession.bind(on_press=self.selectUnSelectList)
        self.ids.clearAllDownloadSession.bind(on_press=self.selectUnSelectList)
        self.ids.selectAllChapters.bind(on_press=self.selectUnSelectList)
        self.ids.clearAllChapters.bind(on_press=self.selectUnSelectList)
        self.ids.selectNew.bind(on_press=self.selectUnSelectList)
        self.ids.downloadNew.bind(on_press=self.downloadNew)

        self.init = True
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
        self.ids.status.text = "Getting " + self.currentMangaSite + "'s manga list"

    def updateMangaList(self, mangaSite, mangaList):
        data = mangaList
        self.list_adapter.data = data
        self.ids.mangaList.populate()

        if not self.init:
            self.ids.status.text = "Updated " + self.currentMangaSite + "'s manga list"

        self.init = False

    def mangaSelected(self, list_adapter, *args):
        if len(list_adapter.selection) == 1:
            selected_object = list_adapter.selection[0]
            selectedManga = selected_object.text
            if selectedManga != self.toDownloadManga:
                self.ids.labelManga.text = "Selected Manga " + selectedManga
                self.selectedManga = selectedManga
                #Update the list of available chapters

                #Show progress screen
                #self.ids.mangasScreenManager.current = 'ChapterList'
                self.ids.mangasScreenManager.current = 'ChapterListProgress'

                self.toDownloadManga = selected_object.text
                self.toDownloadUrls = []
                #print "Starting to download now ..."
                self.ids.status.text = "Getting " + self.selectedManga + "'s chapters"

                #Get the updated Date from the saved list
                #OPTIMIZE THIS - Think in DICT terms

                previousDate = selected_object.previousDate
                for manga in list_adapter.data:
                    if manga['name'] == selectedManga:
                        previousDate = manga['previousDate']

                self.mangaBackGroundDownloader.downloadChapterList(self.currentMangaSite, selected_object.url, self.updateChapterList, previousDate)

    def updateChapterList(self, mangaSite, chapterList):
        i = 0
        for chapter in chapterList:
            chapter['checked'] = False
            chapter['index'] = i
            newChapter = chapter.get('new', False)
            if newChapter:
                chapter['color'] = (0, 1, 0, 1)
            else:
                chapter['color'] = (0, 0, 0, 1)
            i += 1

        data = chapterList
        self.chapterlist_adapter.data = data
        self.ids.chapterList.populate()
        #Show the list view screen now
        self.ids.mangasScreenManager.current = 'ChapterList'
        self.ids.status.text = self.selectedManga + "'s chapters available for download"

    def downloadChapters(self, instance):

        with self.downloadUILock:
            downloadSessionId = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

            while self.downloadingMangasIds.get(downloadSessionId, None) is not None:
                downloadSessionId = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

            urls = self.mangaBackGroundDownloader.loadDownloadChapters(self.currentMangaSite,
                                                                                  self.toDownloadManga,
                                                                                  self.toDownloadUrls,
                                                                                  downloadSessionId,
                                                                                  self.downloadingProgress,
                                                                                  self.updateMangaDates)

            if len(urls) > 0:
                #Update downloading data with this instance. Pass the unique id for it
                downloadSession = {}

                downloadSession['text'] = self.currentMangaSite
                downloadSession['mangaInfotext'] = self.toDownloadManga + " 0/" + str(len(urls))
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

    def updateMangaDates(self, mangaSite, index, date):
        if self.currentMangaSite == mangaSite and index is not None:
            self.list_adapter.data[index]['previousDate'] = date
            self.forceRefreshListView(self.ids.mangaList)

    def downloadingProgress(self, downloadSessionId, chapterProgress=None, chapterInfo=None, sessionProgress=None, mangaInfo=None, sessionFail=False, downloadCompleted=False):
        with self.downloadUILock:
            statusText = ""

            downloadSession = self.downloadingMangasIds.get(downloadSessionId, None)
            if downloadSession is not None:
                if sessionFail:
                    chapterInfotext = "[b][color=ff0000]" + escape_markup("Failed to download Chapter ") + \
                                      "[color=000000]" + escape_markup(chapterInfo) + "[/color]" + \
                                      escape_markup(" Try again by clicking 'Resume' button") + "[/b][/color]"

                    downloadSession['chapterInfotext'] = chapterInfotext
                    statusText = chapterInfotext
                    self.forceRefreshListView(self.ids.downloadList, statusText)

                    return

                if chapterProgress is not None:
                    downloadSession['chapterProgress'] = chapterProgress

                if chapterInfo is not None:
                    downloadSession['chapterInfotext'] = chapterInfo
                    statusText = chapterInfo

                if mangaInfo is not None:
                    downloadSession['mangaInfotext'] = mangaInfo
                    statusText = mangaInfo

                if sessionProgress is not None:
                    # print "Weeeeeee "+ str(sessionProgress)
                    downloadSession['mangaProgress'] = sessionProgress
                #If it is not completed, then only accept any status change of complete
                if not downloadSession['downloadCompleted']:
                    downloadSession['downloadCompleted'] = downloadCompleted

                self.forceRefreshListView(self.ids.downloadList, statusText)
            else:
                print "Got some extraneous progress info - must have been removed already"

    def forceRefreshListView(self, listview, statusText=""):
        listview.adapter.update_for_new_data()
        listview._trigger_reset_populate()

        self.ids.status.text = statusText

    def on_chapterselect_checkbox_active(self, checkbox, value):
        chapterInfo = {}
        chapterInfo['chapterName'] = checkbox.text
        chapterInfo['url'] = checkbox.url
        chapterInfo['date'] = checkbox.date

        if value:
            self.toDownloadUrls.append(chapterInfo)
        else:
            self.toDownloadUrls.remove(chapterInfo)

    def on_chapterselect_button_click(self, label):
        checkbox =  label.checkboxid
        checkbox.active = not checkbox.active
        self.on_chapterselect_checkbox_active(checkbox, checkbox.active)

    def on_down_checkbox_active(self, checkbox, value):
        downloadSessionId = checkbox.downloadSessionId
        downloadSession = self.downloadingMangasIds[downloadSessionId]

        if value:
            self.downloadingMangasSelected.append(downloadSessionId)
        else:
            self.downloadingMangasSelected.remove(downloadSessionId)

        with self.downloadUILock:
            downloadSession['checked'] = value

        print self.downloadingMangasSelected

    def pauseDownloads(self, downloadSessionIdsList):
        for downloadSessionId in downloadSessionIdsList:
            self.mangaBackGroundDownloader.pauseDownloadChapters(downloadSessionId)
            with self.downloadUILock:
                downloadSession = self.downloadingMangasIds[downloadSessionId]
                downloadSession['text'] = downloadSession['mangaSite'] + " (Paused)"

        self.forceRefreshListView(self.ids.downloadList)

    def resumeDownloads(self, downloadSessionIdsList):
        for downloadSessionId in downloadSessionIdsList:
            self.mangaBackGroundDownloader.resumeDownloadChapters(downloadSessionId)
            with self.downloadUILock:
                downloadSession = self.downloadingMangasIds[downloadSessionId]
                downloadSession['text'] = downloadSession['mangaSite']

        self.forceRefreshListView(self.ids.downloadList)

    def removeDownloads(self, downloadSessionIdsList):
        with self.downloadUILock:
            for downloadSessionId in downloadSessionIdsList:
                self.mangaBackGroundDownloader.stopDownloadChapters(downloadSessionId)
                downloadSession = self.downloadingMangasIds.pop(downloadSessionId)
                self.downloadlist_adapter.data.remove(downloadSession)

        self.forceRefreshListView(self.ids.downloadList)

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
            if len(self.downloadingMangasSelected) > 0:
                popup = MangaPopup('Remove all', 'Are you sure you want to remove selected downloads?\nCannot undo this operation')
                popup.bind(on_ok=self.remove_downloads)
                popup.open()
        elif instance == self.ids.removeAllDownloadSession:
            popup = MangaPopup('Remove all', 'Are you sure you want to remove all the downloads?\nCannot undo this operation')
            popup.bind(on_ok=self.remove_all)
            popup.open()
        elif instance == self.ids.resumeDownloadSession:
            print "resume called"
            self.resumeDownloads(self.downloadingMangasSelected)
        elif instance == self.ids.resumeAllDownloadSession:
            popup = MangaPopup('Resume all', 'Are you sure you want to resume all the downloads?')
            popup.bind(on_ok=self.resume_all)
            popup.open()

    def remove_downloads(self, instance):
        self.removeDownloads(self.downloadingMangasSelected)

    def pause_all(self, instance):
        print "Yes we pause all"
        downloadSessionIdsList = self.downloadingMangasIds.keys()
        self.pauseDownloads(downloadSessionIdsList)

    def remove_all(self, instance):
        print "Yes we remove all"
        downloadSessionIdsList = self.downloadingMangasIds.keys()
        self.removeDownloads(downloadSessionIdsList)

    def resume_all(self, instance):
        print "Yes we resume all"
        downloadSessionIdsList = self.downloadingMangasIds.keys()
        self.resumeDownloads(downloadSessionIdsList)

    def selectUnSelectList(self, instance):
        if instance == self.ids.selectAllDownloadSession:
            self.downloadingMangasSelected = list(self.downloadingMangasIds.keys())
            for downloadSessionId in self.downloadingMangasSelected:
                with self.downloadUILock:
                    downloadSession = self.downloadingMangasIds[downloadSessionId]
                    downloadSession['checked'] = True

            self.forceRefreshListView(self.ids.downloadList)

        elif instance == self.ids.clearAllDownloadSession:
            for downloadSession in self.downloadingMangasIds.values():
                with self.downloadUILock:
                    downloadSession['checked'] = False

            del self.downloadingMangasSelected[:]

            self.forceRefreshListView(self.ids.downloadList)

        elif instance == self.ids.selectAllChapters:
            self.toDownloadUrls = list(self.chapterlist_adapter.data)
            for chapter in self.chapterlist_adapter.data:
                chapter['checked'] = True

            self.forceRefreshListView(self.ids.chapterList)

        elif instance == self.ids.clearAllChapters:
            for chapter in self.chapterlist_adapter.data:
                chapter['checked'] = False

            del self.toDownloadUrls[:]

            self.forceRefreshListView(self.ids.chapterList)

        elif instance == self.ids.selectNew:
            for chapter in self.chapterlist_adapter.data:
                if chapter['new']:
                    chapter['checked'] = True

                    chapterInfo = {}
                    chapterInfo['chapterName'] = chapter['name']
                    chapterInfo['url'] = chapter['url']
                    chapterInfo['date'] = chapter['date']

                    self.toDownloadUrls.append(chapterInfo)
            self.forceRefreshListView(self.ids.chapterList)

    def downloadNew(self, instance):
        if instance == self.ids.downloadNew:
            # Save the current downloadUrls, Clear the download urls, then download the new urls, save back the previous urls
            tmpUrls = list(self.toDownloadUrls)
            del self.toDownloadUrls[:]
            for chapter in self.chapterlist_adapter.data:
                if chapter['new']:
                    chapterInfo = {}
                    chapterInfo['chapterName'] = chapter['name']
                    chapterInfo['url'] = chapter['url']
                    chapterInfo['date'] = chapter['date']

                    self.toDownloadUrls.append(chapterInfo)
            self.downloadChapters(self.ids.downloadChapters)
            self.toDownloadUrls = list(self.toDownloadUrls)


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
            'delete_folder': "0",
            'include_mangasite_folder': "1"
        })

    def on_start(self):
        pass

    def on_stop(self):
        pass


def on_chapterselect_checkbox_active(checkbox, value):
    mangaDownloaderInstance.on_chapterselect_checkbox_active(checkbox, value)

def on_chapterselect_button_click(button):
    mangaDownloaderInstance.on_chapterselect_button_click(button)

def on_down_checkbox_active(checkbox, value):
    mangaDownloaderInstance.on_down_checkbox_active(checkbox, value)


if __name__ == '__main__':
    MangaDownloaderApp().run()
