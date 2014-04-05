from kivy.lang import Builder
Builder.load_string("""
[MangaButton@ListItemButton]:
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    size_hint_y: None
    #height: self.text_size[1]
    height: 30
    text: ctx.text
    text_size: self.size
#
# [MangaButton@SelectableView+GridLayout]:
#     cols: 1
#     spacing: 10
#     size_hint_y: None
#     height: thetb.texture_size[1]

#     ListItemButton:
#         id: thetb
#         halign: 'center'
#         valign: 'middle'
#         text: ctx.text
#         text_size: self.width, None
#         size_hint: (1, None)
#         size: self.parent.width, self.texture_size[1]
#         max_lines: 3

<MangaDownloaderLabel@Label>:
    size_hint_x: 1
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    padding_x: -10

[Chapter@BoxLayout]
    size_hint: 1, None
    height: chapterSelect.height

    CheckBox:
        id: chapterSelect
        size_hint: None, None
        height: 40
        on_active: ctx['on_active'](*args)
        url: ctx.url
        canvas:
            Clear:
            Color:
                rgba: 0, 1, 0, 1
            Rectangle:
                source: 'atlas://data/images/defaulttheme/checkbox%s_%s' % (('_radio' if self.group else ''), ('on' if self.active else 'off'))
                size: 32, 32
                pos: int(self.center_x - 16), int(self.center_y - 16)

    MangaDownloaderLabel:
        id: chapterText
        text: ctx.text
        padding_x: 30

[MangaDownload@BoxLayout]
    orientation: 'vertical'
    size_hint: 1, None
    BoxLayout:
        id: mangaDownloadInfo
        orientation: 'vertical'
        size_hint: 1, 1

        canvas:
            Color:
                rgba: 0.5, 0.5, 0.5, 1
            Rectangle:
                pos: self.pos
                size: self.size

        MangaDownloaderLabel:
            id: mangaName
            text: ctx.text

        MangaDownloaderLabel:
            id: mangaDownloadInfo
            text: ctx.mangaInfotext

        ProgressBar:
            id: mangaDownloadProgress
            value: ctx.mangaProgress

        MangaDownloaderLabel:
            id: chapterDownloadInfo
            text: ctx.chapterInfotext

        ProgressBar:
            id: chapterDownloadProgress
            value: ctx.chapterProgress

    Label:
        size_hint: 1, None
        height: 10



""")
