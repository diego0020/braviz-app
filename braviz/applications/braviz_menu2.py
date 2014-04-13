__author__ = 'Diego'

import subprocess
import sys

from PyQt4 import QtGui
from PyQt4 import QtCore

from braviz.interaction.qt_guis.menu2 import Ui_BavizMenu
import braviz.interaction.qt_dialogs
import braviz.interaction.qt_sample_select_dialog


class BravizMenu2(QtGui.QMainWindow):
    def __init__(self):
        super(BravizMenu2,self).__init__()
        self.reader = None

        self.ui = None
        self.setup_gui()
        self.setWindowTitle("Braviz Menu")

    def setup_gui(self):
        self.ui = Ui_BavizMenu()
        self.ui.setupUi(self)
        self.ui.anova.clicked.connect(self.make_application_launcher("anova",self.ui.anova))
        self.ui.sample_overview.clicked.connect(self.make_application_launcher("sample_overview",
                                                                              self.ui.sample_overview))
        self.ui.subject_overview.clicked.connect(self.make_application_launcher("subject_overview",
                                                                               self.ui.subject_overview))
        self.ui.variables.clicked.connect(self.launch_variable_management_dialog)
        self.ui.scenarios.clicked.connect(self.launch_scenarios_dialog)
        self.ui.samples.clicked.connect(self.launch_samples_dialog)

    __applications = {
        "subject_overview" : "subject_overview",
        "sample_overview" : "sample_overview",
        "anova" : "anova_task"
    }

    def make_application_launcher(self,app,icon):
        interpreter = sys.executable
        module = self.__applications[app]
        args = [interpreter,"-m","braviz.applications.%s"%module]
        def restore_icon():
            icon.setEnabled(True)

        def launch_app():
            subprocess.Popen(args)
            icon.setEnabled(False)
            QtCore.QTimer.singleShot(3000,restore_icon)
        return launch_app

    def launch_variable_management_dialog(self):
        dialog = braviz.interaction.qt_dialogs.OutcomeSelectDialog(None)
        dialog.setWindowTitle("Variables")
        dialog.ui.select_button.setText("Done")
        dialog.exec_()

    def launch_samples_dialog(self):
        dialog = braviz.interaction.qt_sample_select_dialog.SampleLoadDialog()
        dialog.exec_()

    def launch_scenarios_dialog(self):
        if self.reader is None:
            self.reader = braviz.readAndFilter.kmc40AutoReader()
        params = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(None,params,self.reader)
        ret = dialog.exec_()
        if ret==QtGui.QDialog.Accepted:
            print params
            app = params["meta"]["application"]
            scn_id = params["meta"]["scn_id"]
            interpreter = sys.executable
            args = [interpreter,"-m","braviz.applications.%s"%app,str(scn_id)]
            subprocess.Popen(args)



def run():
    import sys
    app = QtGui.QApplication(sys.argv)
    main_window = BravizMenu2()
    main_window.show()
    app.exec_()

if __name__ == '__main__':
    run()
