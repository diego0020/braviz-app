from __future__ import division
from PyQt4 import QtCore,QtGui
import braviz
import braviz.visualization.subject_viewer
import braviz.visualization.fmri_timeseries
from braviz.readAndFilter import user_data as braviz_user_data

from braviz.interaction.qt_guis.fmri_explore import Ui_fMRI_Explorer
import logging

import numpy as np


__author__ = 'Diego'

class FmriExplorer(QtGui.QMainWindow):
    def __init__(self,scenario,server_broadcast_address,server_receive_address):
        super(FmriExplorer,self).__init__()

        self.__reader = braviz.readAndFilter.BravizAutoReader()

        self.__current_subject = None
        self.__current_paradigm = None
        self.__current_contrast = None

        self.ui = None
        self.three_d_widget = None
        self.image_view = None
        self.time_plot = None
        self.start_ui()
        if scenario is None:
            QtCore.QTimer.singleShot(0, self.load_initial_view)

    def start_ui(self):
        self.ui = Ui_fMRI_Explorer()
        self.ui.setupUi(self)

        #image frame
        self.three_d_widget = braviz.visualization.subject_viewer.QFmriWidget(self.__reader,self.ui.vtk_frame)
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout(self.ui.vtk_frame)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.addWidget(self.three_d_widget)
        self.ui.vtk_frame_layout.setContentsMargins(0,0,0,0)
        self.image_view = self.three_d_widget.viewer
        self.three_d_widget.cursor_moved.connect(self.handle_cursor_move)

        #timeserios frame
        self.time_plot = braviz.visualization.fmri_timeseries.TimeseriesPlot(self.ui.timeline_frame)
        self.ui.timeline_frame_layout = QtGui.QVBoxLayout(self.ui.timeline_frame)
        self.ui.timeline_frame.setLayout(self.ui.timeline_frame_layout)
        self.ui.timeline_frame_layout.addWidget(self.time_plot)
        self.ui.timeline_frame_layout.setContentsMargins(0,0,0,0)

        #controls
        paradigms = sorted(self.__reader.get("fmri",None,index=True))
        for p in paradigms:
            self.ui.paradigm_combo.addItem(p)
        self.ui.paradigm_combo.setCurrentIndex(0)

    def start(self):
        self.three_d_widget.initialize_widget()


    def load_initial_view(self):
        self.__current_subject = self.__reader.get("ids")[0]
        self.__current_paradigm = str(self.ui.paradigm_combo.currentText())
        self.__current_contrast = 1
        self.update_fmri_data_view()

    def update_fmri_data_view(self):
        self.image_view.set_all(self.__current_subject,self.__current_paradigm,self.__current_contrast)
        bold_image = self.__reader.get("BOLD",self.__current_subject,name=self.__current_paradigm)
        self.time_plot.set_bold(bold_image)
        spm_data = self.__reader.get("fmri",self.__current_subject,name=self.__current_paradigm,spm=True)
        contrasts = spm_data.get_contrast_names()
        #todo update contrasts combo
        self.time_plot.set_spm(spm_data)

    def handle_cursor_move(self,coords):
        self.statusBar().showMessage(str(coords))

def run():
    import sys
    from braviz.utilities import configure_logger,configure_console_logger
    configure_console_logger("fmri")
    args = sys.argv
    scenario = None
    server_broadcast_address = None
    server_receive_address = None
    if len(args)>1:
        scenario = int(args[1])
        if len(args)>2:
            server_broadcast_address = args[2]
            if len(args)>3:
                server_receive_address = args[3]
    qt_args = args[4:]
    app = QtGui.QApplication(qt_args)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = FmriExplorer(scenario,server_broadcast_address,server_receive_address)
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()
