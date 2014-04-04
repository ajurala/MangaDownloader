__author__ = 'aj'

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.listview import ListItemButton

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
args_converter = lambda row_index, rec: {
    'text': rec,
    'size_hint_y': None,
    'height': 25,
    'shorten': 'true',
    'valign': 'middle',
    'halign': 'left'
}

cargs_converter = lambda row_index, rec: {
    'text': rec
}

dargs_converter = lambda row_index, rec: {
    'text': rec['text'],
    'mangaInfotext': rec['mangaInfotext'],
    'chapterInfotext': rec['chapterInfotext'],
    'mangaProgress': rec['mangaProgress'],
    'chapterProgress': rec['chapterProgress']
}



class MangaDownloader(TabbedPanel):
    list_adapter = ListAdapter(data=data,
                               args_converter=args_converter,
                               template='MangaButton',
                               #cls=ListItemButton,
                               selection_mode='single',
                               allow_empty_selection=False)

    chapterlist_adapter = ListAdapter(data=[],
                                      args_converter=cargs_converter,
                                      template='Chapter',
                                      selection_mode='none',
                                      allow_empty_selection=True)

    downloadlist_adapter = ListAdapter(data=ddata,
                                       args_converter=dargs_converter,
                                       template='MangaDownload',
                                       selection_mode='none',
                                       allow_empty_selection=True)

    def __init__(self):
        TabbedPanel.__init__(self)
        self.list_adapter.bind(on_selection_change=self.mangaSelected)

    def mangaSelected(self, list_adapter, *args):
        if len(list_adapter.selection) == 1:

            selected_object = list_adapter.selection[0]

            self.ids.labelManga.text = "Selected Manga "+selected_object.text
            #Update the list of available chapters

            ndata = [str(i)+' '.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(5, 30))) for i in range(100, 105)]

            #print ndata
            self.chapterlist_adapter.data = ndata
            self.ids.chapterList.populate()


class MangaDownloaderApp(App):
    def build(self):
        return MangaDownloader()

if __name__ == '__main__':
    MangaDownloaderApp().run()
