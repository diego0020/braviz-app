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

class ListValidator(QtGui.QValidator):
    def __init__(self,valid_options):
        super(ListValidator,self).__init__()
        self.valid = frozenset(valid_options)

    def validate(self, QString, p_int):
        str_value = str(QString)
        if str_value in self.valid:
            return QtGui.QValidator.Acceptable,p_int
        else:
            if len(str_value) == 0:
                return QtGui.QValidator.Intermediate,p_int
            try:
                i = int(str_value)
            except Exception:
                return QtGui.QValidator.Invalid,p_int
            else:
                return QtGui.QValidator.Intermediate,p_int

class FmriExplorer(QtGui.QMainWindow):
    def __init__(self,scenario,server_broadcast_address,server_receive_address):
        super(FmriExplorer,self).__init__()

        self.__reader = braviz.readAndFilter.BravizAutoReader()

        self.__valid_ids = frozenset(str(i) for i in self.__reader.get("ids"))
        self.__current_subject = None
        self.__current_paradigm = None
        self.__current_contrast = 1

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
        self.ui.contrast_combo.clear()
        self.ui.contrast_combo.activated.connect(self.update_fmri_data_view)
        self.ui.paradigm_combo.activated.connect(self.update_fmri_data_view)

        self.ui.subj_completer = QtGui.QCompleter(list(self.__valid_ids))
        self.ui.subject_edit.setCompleter(self.ui.subj_completer)
        self.ui.subj_validator = ListValidator(self.__valid_ids)
        self.ui.subject_edit.setValidator(self.ui.subj_validator)
        self.ui.subject_edit.editingFinished.connect(self.update_fmri_data_view)


    def start(self):
        self.three_d_widget.initialize_widget()


    def load_initial_view(self):
        self.__current_subject = self.__reader.get("ids")[0]
        self.ui.subject_edit.setText(self.__current_subject)
#        self.__current_paradigm = str(self.ui.paradigm_combo.currentText())
#        self.__current_contrast = 1
        self.update_fmri_data_view()

    def update_fmri_data_view(self):
        log = logging.getLogger(__file__)
        subj = str(self.ui.subject_edit.text())
        if subj in self.__valid_ids:
            self.__current_subject = subj
        self.__current_paradigm = str(self.ui.paradigm_combo.currentText())
        self.__current_contrast = self.ui.contrast_combo.currentIndex()+1

        try:
            spm_data = self.__reader.get("fmri",self.__current_subject,name=self.__current_paradigm,spm=True)
            contrasts = spm_data.get_contrast_names()
        except Exception:
            log.warning("Couldn't read spm file")
            spm_data = None
        else:
            self.ui.contrast_combo.clear()
            for i in xrange(len(contrasts)):
                self.ui.contrast_combo.addItem(contrasts[i+1])
            if 1<=self.__current_contrast <= len(contrasts):
                self.ui.contrast_combo.setCurrentIndex(self.__current_contrast-1)
            else:
                self.ui.contrast_combo.setCurrentIndex(0)
                self.__current_contrast = 1  # 0+1
        try:
            self.image_view.set_all(self.__current_subject,self.__current_paradigm,self.__current_contrast)
            bold_image = self.__reader.get("BOLD",self.__current_subject,name=self.__current_paradigm)
        except Exception:
            message = "%s not available for subject %s"%(self.__current_paradigm,self.__current_subject)
            log.warning(message)
            self.statusBar().showMessage(message,500)
            bold_image = None
        #todo update contrasts combo
        self.time_plot.clear()
        self.time_plot.set_spm_and_bold(spm_data,bold_image)
        self.time_plot.set_contrast(self.__current_contrast)
        self.time_plot.draw_bold_signal(self.image_view.current_position())

    def handle_cursor_move(self,coords):
        self.statusBar().showMessage(str(coords))
        self.time_plot.draw_bold_signal(coords)

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
