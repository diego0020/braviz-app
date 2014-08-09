__author__ = 'Diego'

import subprocess
import sys
import logging

from PyQt4 import QtGui
from PyQt4 import QtCore

from braviz.interaction.connection import MessageServer


try:
    from braviz.interaction.qt_guis.menu2_light import Ui_BavizMenu
    import braviz.interaction.qt_dialogs
    import braviz.interaction.qt_sample_select_dialog
except ImportError:
    import braviz.interaction.generate_qt_guis
    braviz.interaction.generate_qt_guis.update_guis()
    print "please try again"
    sys.exit()



class BravizMenu2(QtGui.QMainWindow):
    def __init__(self):
        super(BravizMenu2,self).__init__()
        self.reader = None

        self.ui = None
        self.setWindowTitle("Braviz Menu")
        self.messages_server = MessageServer(local_only=True)
        print "Server Started"
        print "Broadcast address: %s"%self.messages_server.broadcast_address
        print "Receive address: %s"%self.messages_server.receive_address

        self.messages_server.message_received.connect(self.print_messages)
        self.setup_gui()

    def setup_gui(self):
        self.ui = Ui_BavizMenu()
        self.ui.setupUi(self)
        self.connect_application_launcher("anova",self.ui.anova)
        self.connect_application_launcher("correlations",self.ui.correlations)
        self.connect_application_launcher("linear_model",self.ui.linear_model)
        self.connect_application_launcher("logic_bundles",self.ui.logic_bundles)
        self.connect_application_launcher("build_roi",self.ui.roi_builder)
        self.connect_application_launcher("sample_overview", self.ui.sample_overview)
        self.connect_application_launcher("subject_overview", self.ui.subject_overview)
        self.connect_application_launcher("fmri_explorer", self.ui.fmri_explorer)
        self.connect_application_launcher("measure", self.ui.measure_app)
        self.connect_application_launcher("excel", self.ui.excel)
        self.connect_application_launcher("export", self.ui.export_2)

        #self.connect_application_launcher("braviz_menu_classic", self.ui.braviz_menu_classic))
        self.ui.variables.clicked.connect(self.launch_variable_management_dialog)
        self.ui.scenarios.clicked.connect(self.launch_scenarios_dialog)
        self.ui.samples.clicked.connect(self.launch_samples_dialog)
        self.ui.help_button.clicked.connect(self.open_help)


    __applications = {
        "subject_overview" : "subject_overview",
        "sample_overview" : "sample_overview",
        "anova" : "anova_task",
        "braviz_menu_classic" : "braviz_menu",
        "correlations":"correlations",
        "linear_model": "lm_task",
        "logic_bundles":"logic_bundles",
        "build_roi":"build_roi",
        "excel":"import_from_excel",
        "export":"export_vars",
        "fmri_explorer":"fmri_explorer",
        "measure":"measure_task"
    }

    def connect_application_launcher(self,app,button):
        interpreter = sys.executable
        module = self.__applications[app]
        # python -m <module> scenario=0 <broadcast_address> <receive_address>
        args = [interpreter,"-m","braviz.applications.%s"%module,"0",
                self.messages_server.broadcast_address,self.messages_server.receive_address]
        def restore_icon():
            button.setEnabled(True)

        def launch_app():
            subprocess.Popen(args)
            button.setEnabled(False)
            QtCore.QTimer.singleShot(3000,restore_icon)
        button.clicked.connect(launch_app)


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
            self.reader = braviz.readAndFilter.BravizAutoReader()
        params = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(None,params,self.reader)
        ret = dialog.exec_()
        if ret==QtGui.QDialog.Accepted:
            log = logging.getLogger(__name__)
            log.info(params)
            app = params["meta"]["application"]
            scn_id = params["meta"]["scn_id"]
            interpreter = sys.executable
            args = [interpreter,"-m","braviz.applications.%s"%app,str(scn_id)]
            subprocess.Popen(args)

    def open_help(self):
        import webbrowser
        import os
        my_path = os.path.dirname(__file__)
        doc_path = os.path.join(my_path,"..","..","doc")
        help_file = os.path.join(doc_path,"faq.html")
        url = "file://%s"%help_file
        webbrowser.open(url,2)

    def print_messages(self,msg):
        #for testing
        print "RECEIVED: %s"%msg

def run():
    import sys
    from braviz.utilities import configure_logger
    configure_logger("menu2")
    log = logging.getLogger(__name__)
    app = QtGui.QApplication(sys.argv)
    main_window = BravizMenu2()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    import braviz.interaction.generate_qt_guis
    braviz.interaction.generate_qt_guis.update_guis()
    run()
