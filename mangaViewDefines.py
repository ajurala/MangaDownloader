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
    url: ctx.url
    previousDate: ctx.previousDate

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
    size_hint: 1, 1
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    padding_x: -10

<MangaDownloaderCheckBox@CheckBox>
    size_hint: None, None
    height: 40
    canvas:
        Clear:
        Color:
            rgba: 0, 1, 0, 1
        Rectangle:
            source: 'atlas://data/images/defaulttheme/checkbox%s_%s' % (('_radio' if self.group else ''), ('on' if self.active else 'off'))
            size: 32, 32
            pos: int(self.center_x - 16), int(self.center_y - 16)

[Chapter@BoxLayout]
    size_hint: 1, None
    height: chapterSelect.height

    MangaDownloaderCheckBox:
        id: chapterSelect
        on_active: ctx['on_active'](*args)
        url: ctx.url
        text: ctx.text
        active: ctx.active
        date: ctx.date

    MangaDownloaderLabel:
        id: chapterText
        text: ctx.text
        padding_x: 30
        color: ctx.color

[MangaDownload@BoxLayout]
    orientation: 'vertical'
    size_hint: 1, None

    disabled: ctx.disabled

    BoxLayout:
        id: mangaDownloadInfo
        orientation: 'vertical'
        size_hint: 1, 1
        padding: 10, 20, 10, 10

        canvas:
            Color:
                rgba: 0.5, 0.5, 0.5, 1
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            MangaDownloaderCheckBox:
                id: mangaDownloadSelect
                size_hint: None, 5
                active: ctx.active
                on_active: ctx['on_active'](*args)
                mangaName: ctx.mangaName
                downloadSessionId: ctx.downloadSessionId
                downloadCompleted: ctx.downloadCompleted

            MangaDownloaderLabel:
                id: mangaName
                size_hint_y: 5
                text: ctx.text
                padding_x: 30

        MangaDownloaderLabel:
            id: mangaDownloadInfo
            size_hint_y: 4
            text: ctx.mangaInfotext

        ProgressBar:
            id: mangaDownloadProgress
            value: ctx.mangaProgress

        MangaDownloaderLabel:
            id: chapterDownloadInfo
            size_hint_y: 4
            text: ctx.chapterInfotext
            markup: True

        ProgressBar:
            id: chapterDownloadProgress
            value: ctx.chapterProgress

    Label:
        size_hint: 1, None
        height: 10

""")
