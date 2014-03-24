__author__ = 'Diego'
import time
import threading

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from braviz.interaction.qt_guis.export_scalar_into_db import Ui_ExportScalar


class ExportScalarToDataBase(QtGui.QDialog):
    def __init__(self,fibers=False,structures_list=tuple(),metric="volume"):
        super(ExportScalarToDataBase,self).__init__()
        self.ui=None
        self.progress = 0
        self.timer = None
        self.structs = structures_list
        self.fibers_mode = fibers
        self.metric = metric
        self.progress_thread = None

        self.setupUI()


    def setupUI(self):
        self.ui = Ui_ExportScalar()
        self.ui.setupUi(self)
        self.ui.progressBar.setValue(self.progress)

        if self.fibers_mode is False:
            self.ui.struct_name_label.setText(" + ".join(self.structs))
        self.ui.metric_label.setText(self.metric)
        self.ui.start_button.pressed.connect(self.start_calculations)
        self.ui.error_str.setText("")
        self.ui.var_name_input.textChanged.connect(self.check_name)

    def start_calculations(self):
        self.ui.var_name_input.setEnabled(0)
        self.ui.var_description.setEnabled(0)
        self.timer = QtCore.QTimer()
        self.timer.start(1000)
        self.timer.timeout.connect(self.poll_progress)
        self.progress_thread = threading.Thread(target=self.slowly_make_progress)
        self.progress_thread.start()

    def check_name(self):
        name_str = str(self.ui.var_name_input.text())
        if len(name_str)>2:
            self.ui.start_button.setEnabled(1)


    def slowly_make_progress(self):
        while self.progress < 100:
            self.progress +=1
            print self.progress
            time.sleep(0.1)

    def poll_progress(self):
        print "polling"
        self.ui.progressBar.setValue(self.progress)
        if self.progress == 100:
            self.ui.start_button.setText("Done")
            self.timer.stop()
            self.ui.start_button.pressed.connect(self.accept)


def run(fibers=False,structures_list=tuple(),metric="volume"):
    import sys
    app = QtGui.QApplication(sys.argv)
    main_window = ExportScalarToDataBase(fibers,structures_list,metric)
    main_window.show()
    app.exec_()

if __name__ == "__main__":
    test=["CC_Anterior","CC_Posterior","CC_Mid"]
    run(fibers=False,structures_list=test,metric="volume")