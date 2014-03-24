from __future__ import division

__author__ = 'Diego'
import time
import threading

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from braviz.interaction.qt_guis.export_scalar_into_db import Ui_ExportScalar
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.bundles_db as braviz_fibers_db
import braviz.interaction.structure_metrics as braviz_struct_metrics


class ExportScalarToDataBase(QtGui.QDialog):
    def __init__(self, fibers=False, structures_list=tuple(), metric="Volume", db_id=None, operation=None):
        super(ExportScalarToDataBase, self).__init__()
        if (db_id is not None) and (operation is not None):
            raise Exception("Only db_id or operation should be None")
        self.ui = None
        self.progress = 0
        self.timer = None
        self.structs = structures_list
        self.fibers_mode = fibers
        self.metric = metric
        self.db_id = db_id
        self.fibers_operation = operation

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
            raise Exception("Unknown metric")

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
        self.ui.start_button.pressed.connect(self.start_calculations)
        self.ui.error_str.setText("")
        self.ui.var_name_input.textChanged.connect(self.check_name)
        self.ui.tip_label.setText("")

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

        self.reader = braviz.readAndFilter.kmc40AutoReader()
        all_subjects = braviz_tab_data.get_subjects()
        for i, subj in enumerate(all_subjects):
            value = self.get_scalar_value(subj)
            braviz_tab_data.updata_variable_value(self.var_idx, subj, value)
            self.progress = (i + 1) / len(all_subjects) * 100
            print "%s %s : %f"%(self.metric_code,subj,value)
        self.progress = 100

    def get_scalar_value(self, subj):
        image_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE, subj))
        if len(image_code) < 3:
            image_code = "0" + image_code
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
        raise Exception("Couldn't determine structure type")


    def poll_progress(self):
        #print "polling"
        self.ui.progressBar.setValue(self.progress)
        if self.progress == 100:
            self.ui.start_button.setText("Done")
            self.timer.stop()
            self.ui.start_button.pressed.connect(self.accept)
            self.ui.start_button.setEnabled(1)
            self.ui.tip_label.setText("")


def run(fibers=False, structures_list=tuple(), metric="volume", db_id=None, operation="and"):
    import sys

    app = QtGui.QApplication(sys.argv)
    main_window = ExportScalarToDataBase(fibers, structures_list, metric, db_id, operation)
    main_window.show()
    app.exec_()


if __name__ == "__main__":
    test = ["CC_Anterior", "CC_Posterior"]
    run(fibers=False, structures_list=test, metric="Volume")