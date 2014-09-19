from __future__ import division

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

from braviz.interaction.qt_guis.check_reg import Ui_check_reg_app
from braviz.visualization.checkerboard_view import QCheckViewer
from itertools import izip
import braviz

import logging

class CheckRegApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.ui = None
        self.vtk_viewer = None
        self.setup_gui()

    def setup_gui(self):
        self.ui = Ui_check_reg_app()
        self.ui.setupUi(self)
        self.vtk_viewer = QCheckViewer(self.reader,self.ui.vtk_frame)
        #view frame
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_viewer)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)

    def start(self):
        self.vtk_viewer.initialize_widget()
        #load initial
        self.vtk_viewer.viewer.load_test_view()



def run():
    from braviz.utilities import configure_console_logger
    configure_console_logger("check_reg")
    app = QtGui.QApplication([])
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = CheckRegApp()
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()