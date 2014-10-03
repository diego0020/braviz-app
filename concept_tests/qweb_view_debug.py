import sys
from PyQt4 import QtCore, QtGui, QtWebKit

class WebPage(QtWebKit.QWebPage):
    def javaScriptConsoleMessage(self, msg, line, source):
        print '%s line %d: %s' % (source, line, msg)

url = 'http://127.0.0.1:8100/'
app = QtGui.QApplication([])
browser = QtWebKit.QWebView()
page = WebPage()
browser.setPage(page)
browser.load(QtCore.QUrl(url))
browser.show()
sys.exit(app.exec_())
