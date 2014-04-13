class MangaConfig():

    def __init__(self):
        self.config = None
        self.config_section = "proxy"
        self.config_proxy_url = "proxy_url"
        self.config_proxy_port = "proxy_port"
        self.config_proxy_enable = "toggle_proxy"

    def setConfig(self, config):
        self.config = config
