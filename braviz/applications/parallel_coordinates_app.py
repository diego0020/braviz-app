from __future__ import division


import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

from braviz.interaction.qt_guis.parallel_coordinates import Ui_parallel_coordinates

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection, get_data_frame_by_name
import braviz.readAndFilter.tabular_data as braviz_tab_data

import logging

__author__ = 'da.angulo39'

class ParallelCoordinatesApp(QtGui.QMainWindow):
    def __init__(self):
        super(ParallelCoordinatesApp, self).__init__()
        self.ui = None

        self.setup_ui()

    def setup_ui(self):
        self.ui = Ui_parallel_coordinates()
        self.ui.setupUi(self)
        self.ui.webView.load(QtCore.QUrl("http://127.0.0.1:8100/?vars=2014,1002,1003,1004,1005"))


if __name__ == "__main__":
    app = QtGui.QApplication([])
    main_window = ParallelCoordinatesApp()
    main_window.show()
    app.exec_()