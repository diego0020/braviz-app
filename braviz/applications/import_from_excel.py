import braviz
import pandas as pd
from PyQt4 import QtGui, QtCore
from braviz.interaction.qt_guis.import_from_excel import Ui_import_from_excel
import logging

__author__ = 'Diego'

class ImportFromExcel(QtGui.QDialog):
    def __init__(self):
        super(ImportFromExcel,self).__init__()
        self.ui = None
        self.setup_gui()

    def setup_gui(self):
        self.ui = Ui_import_from_excel()
        self.ui.setupUi(self)

    def read_excel(self):
        df = pd.read_excel("TMS.xlsx",0,index_col=0)


def run():
    import sys
    from braviz.utilities import configure_console_logger

    # configure_logger("build_roi")
    configure_console_logger("import_from_excel")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    logging.basicConfig(level=logging.DEBUG)
    main_window = ImportFromExcel()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()
