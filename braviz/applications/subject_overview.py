from __future__ import division
__author__ = 'Diego'

import PyQt4.QtGui as QtGui
from PyQt4.QtGui import QMainWindow
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

import braviz
from braviz.interaction.qt_guis.subject_overview import Ui_subject_overview
from braviz.visualization.subject_viewer import SubjectViewer


class SubjectOverviewApp(QMainWindow):
    def __init__(self,initial_vars=None):
        #Super init
        QMainWindow.__init__(self)
        #Internal initialization
        self.reader=braviz.readAndFilter.kmc40AutoReader()
        if initial_vars is None:
            #GENRE LAT Weight at birth VCIIQ
            initial_vars=(11,6,17,1)
        self.clinical_vars=initial_vars
        self.vtk_widget=QVTKRenderWindowInteractor()
        self.vtk_viewer=SubjectViewer(self.vtk_widget,self.reader)
        #Init gui
        self.ui=None
        self.setup_gui()
        self.vtk_viewer.show_cone()

    def setup_gui(self):
        self.ui=Ui_subject_overview()
        self.ui.setupUi(self)
        self.ui.vtk_frame_layout=QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0,0,0,0)



def run():
    import sys
    app = QtGui.QApplication(sys.argv)
    main_window = SubjectOverviewApp()
    main_window.show()
    app.exec_()

if __name__ == '__main__':
    run()