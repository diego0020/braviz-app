from __future__ import division
import logging

import PyQt4.QtGui as QtGui
from PyQt4.QtGui import QMainWindow

import braviz
from braviz.interaction.qt_guis.roi_builder import Ui_RoiBuildApp
from braviz.visualization.subject_viewer import QOrthogonalPlanesWidget


__author__ = 'Diego'

class BuildRoiApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = None
        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__current_subject = self.reader.get("ids")[0]
        self.vtk_widget = QOrthogonalPlanesWidget(self.reader,parent=self)
        self.vtk_viewer = self.vtk_widget.subject_viewer

        self.setup_ui()

    def setup_ui(self):
        self.ui = Ui_RoiBuildApp()
        self.ui.setupUi(self)
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
    def start(self):
        self.vtk_widget.initialize_widget()

def run():
    import sys
    from braviz.utilities import configure_console_logger

    #configure_logger("build_roi")
    configure_console_logger("build_roi")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = BuildRoiApp()
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()