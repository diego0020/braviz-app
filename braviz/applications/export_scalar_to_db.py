from __future__ import division

__author__ = 'Diego'
import time
import threading

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from braviz.interaction.qt_guis.export_scalar_into_db import Ui_ExportScalar
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data
import braviz.readAndFilter.bundles_db as braviz_fibers_db
import braviz.interaction.structure_metrics as braviz_struct_metrics
import logging

class ExportScalarToDataBase(QtGui.QDialog):
    def __init__(self, fibers=False, structures_list=tuple(), metric="Volume", db_id=None,
                 operation=None, scenario_id=None):
        super(ExportScalarToDataBase, self).__init__()
        if (db_id is not None) and (operation is not None):
            raise Exception("Only db_id or operation should be None")
        flags = QtCore.Qt.Window | QtCore.Qt.MSWindowsOwnDC | QtCore.Qt.WindowSystemMenuHint | \
                QtCore.Qt.WindowMinimizeButtonHint
        self.setWindowFlags(flags)
        self.ui = None
        self.progress = 0
        self.timer = None
        if structs is not None:
            self.structs = list(set(structures_list)) # remove duplicates
        log = logging.getLogger(__name__)
        log.info(structures_list)
        self.fibers_mode = fibers
        self.metric = metric
        self.db_id = db_id
        self.fibers_operation = operation
        self.scenario_id = scenario_id
        log.info("GOT SCENARIO ID %s", scenario_id)

        #Copied from applications/subject overview
        metrics_dict = {"Volume": "volume",
                        "Area": "area",
                        "FA inside": "fa_inside",
                        "MD inside": "md_inside", }

        #Copied from applications/subject overview
        fiber_metrics_dict = {"Count": "number",
                              "Mean L": "mean_length",
                              "Mean FA": "mean_fa"}

        if self.fibers_mode is False:
            self.metric_code = metrics_dict.get(self.metric)
        else:
            self.metric_code = fiber_metrics_dict.get(self.metric)

        if self.metric_code is None:
            log.error("Unknown metric %s",self.metric)
            raise Exception("Unknown metric %s",self.metric)

        self.progress_thread = None
        self.reader = None
        self.var_name = None
        self.var_desc = None
        self.var_idx = None

        self.setupUI()


    def setupUI(self):
        self.ui = Ui_ExportScalar()
        self.ui.setupUi(self)
        self.ui.progressBar.setValue(self.progress)

        if self.fibers_mode is False:
            self.ui.struct_name_label.setText(" + ".join(self.structs))
        else:
            if self.fibers_operation is not None:
                label = "Fibers passing through " + self.fibers_operation.join(self.structs)
                self.ui.struct_name_label.setText(label)
            else:
                fib_name = braviz_fibers_db.get_bundle_name(self.db_id)
                self.ui.struct_name_label.setText(fib_name)

        self.ui.metric_label.setText(self.metric)
        self.ui.start_button.clicked.connect(self.start_calculations)
        self.ui.error_str.setText("")
        self.ui.var_name_input.textChanged.connect(self.check_name)
        self.ui.tip_label.setText("")
        self.ui.var_description.setPlainText("From Braviz")

    def start_calculations(self):
        self.ui.var_name_input.setEnabled(0)
        self.ui.var_description.setEnabled(0)
        self.var_name = str(self.ui.var_name_input.text())

        #create variable
        potential_conflict = braviz_tab_data.get_var_idx(self.var_name)
        if potential_conflict is None:
            try:
                new_index = braviz_tab_data.register_new_variable(self.var_name, is_real=True)
            except Exception:
                potential_conflict = True
        if potential_conflict is not None:
            self.ui.error_str.setText("Variable name exists, pleas try with a different name")
            self.ui.var_name_input.setEnabled(1)
            self.ui.var_description.setEnabled(1)
            return
        self.var_idx = new_index
        self.ui.start_button.setText("Processing..")
        self.ui.error_str.setText("")
        self.ui.start_button.setEnabled(0)


        #add description
        desc_str = str(self.ui.var_description.toPlainText())
        braviz_tab_data.save_var_description(new_index, desc_str)
        self.ui.tip_label.setText("Note: You can minimize this dialog and continue working")

        #update scenario
        if self.scenario_id is not None:
            name = "<AUTO_%s>"%self.var_name
            description = "Created automatically when recording variable %s"%self.var_name
            braviz_user_data.update_scenario(self.scenario_id,name=name,description=description)
            #link scenario
            braviz_user_data.link_var_scenario(self.var_idx,self.scenario_id)

        #add values
        self.timer = QtCore.QTimer()
        self.timer.start(1000)
        self.timer.timeout.connect(self.poll_progress)
        self.progress_thread = threading.Thread(target=self.save_variables_function)
        self.progress_thread.start()

    def check_name(self):
        name_str = str(self.ui.var_name_input.text())
        if len(name_str) > 2:
            self.ui.start_button.setEnabled(1)


    def slowly_make_progress(self):
        """
        Useful for tests, slowly fill progress bar
        """
        while self.progress < 100:
            self.progress += 1
            #print self.progress
            time.sleep(0.1)

    def save_variables_function(self):
        import braviz

        self.reader = braviz.readAndFilter.BravizAutoReader()
        all_subjects = braviz_tab_data.get_subjects()
        for i, subj in enumerate(all_subjects):
            try:
                value = self.get_scalar_value(subj)
            except Exception:
                value = float("nan")
            braviz_tab_data.updata_variable_value(self.var_idx, subj, value)
            self.progress = (i + 1) / len(all_subjects) * 100
            log = logging.getLogger(__name__)
            log.debug("%s %s : %f"%(self.metric_code,subj,value))
        self.progress = 100

    def get_scalar_value(self, subj):
        image_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE, subj))
        if self.fibers_mode is False:
            val = braviz_struct_metrics.get_mult_struct_metric(self.reader, self.structs, image_code, self.metric_code)
            return val
        else:
            if self.db_id is not None:
                val = braviz_struct_metrics.get_fiber_scalars_from_db(self.reader,
                                                                      image_code, self.db_id, self.metric_code)
                return val
            elif self.fibers_operation is not None:
                val = braviz_struct_metrics.get_fiber_scalars_from_waypoints(self.reader, image_code,
                                                                             self.structs, self.fibers_operation,
                                                                             self.metric_code)
                return val
        log = logging.getLogger(__name__)
        log.error("Couldn't determine structure type")
        raise Exception("Couldn't determine structure type")


    def poll_progress(self):
        #print "polling"
        self.ui.progressBar.setValue(self.progress)
        if self.progress == 100:
            self.ui.start_button.setText("Done")
            self.timer.stop()
            self.ui.start_button.clicked.connect(self.accept)
            self.ui.start_button.setEnabled(1)
            self.ui.tip_label.setText("")


def run(fibers=False, structures_list=tuple(), metric="volume", db_id=None, operation="and",scenario_id=None):
    app = QtGui.QApplication([])
    main_window = ExportScalarToDataBase(fibers, structures_list, metric, db_id, operation,scenario_id=scenario_id)
    main_window.show()
    log = logging.getLogger(__name__)
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == "__main__":
    #arguments <scn_id> <fibers=True> <metric>  <operation> <db_id=x>
    #arguments <scn_id> <fibers=True> <metric>  <operation> <db_id=0> <structs0> <struct1> ....
    #arguments <scn_id> <fibers=False> <metric> <structs0> <struct1> ....
    #            1           2           3         4          5         6
    import sys
    from braviz.utilities import configure_console_logger
    configure_console_logger("export_scalars_to_db")
    log = logging.getLogger(__name__)
    log.info(sys.argv)
    if len(sys.argv)<4:
        log.error("Non enough arguments")
        raise Exception("Not enough arguments")
    args = sys.argv
    scenario_id = args[1]
    fibers = int(args[2])
    if fibers>0:
        fibers = True
    else:
        fibers = False
    metric = args[3]
    if not fibers:
        log.info(args)
        structs = args[4:]
        log.info(structs)
        run(fibers=fibers, structures_list=structs, metric=metric,scenario_id=scenario_id)
    else:
        #Fibers
        operation = args[4]
        db_id = args[5]
        if db_id == "0":
            db_id = None
            structs = args[6:]
        else:
            operation = None
            structs = None

        run(fibers=fibers, structures_list=structs, metric=metric, db_id=db_id, operation=operation,
            scenario_id=scenario_id)
