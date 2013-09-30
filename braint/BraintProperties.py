import ConfigParser

class BraintProperties:
    def __init__(self):
        config = ConfigParser.ConfigParser()
        config.read('File\\properties.ini')
        self.lang = config.get('LANG', 'lang')
        self.repoServer = config.get('REPO', 'server')
        self.repoId = config.get('REPO', 'id')
        
        self.configLang = ConfigParser.ConfigParser()
        self.configLang.read('File\\'+self.lang)
        

