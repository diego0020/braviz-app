from __future__ import division
__author__ = 'Diego'

from mpltools import style

style.use('ggplot')

from braviz.interaction.qt_guis.sample_select_dialog import Ui_SampleSelectDialog
from braviz.interaction.qt_guis.add_filter_dialog import Ui_AddFilterDialog
from braviz.interaction.qt_guis.rational_details_frame_filtering import Ui_rational_details
from braviz.interaction.qt_models import SimpleSetModel
from braviz.readAndFilter import tabular_data as braviz_tab_data
from PyQt4 import QtGui, QtCore
from braviz.interaction.qt_dialogs import VariableSelectDialog
import braviz.interaction.qt_models as braviz_models

import numpy as np
import sys

class SampleSelectDilog(QtGui.QDialog):
    def __init__(self):
        super(SampleSelectDilog,self).__init__()

        self.working_model = SimpleSetModel()
        self.output_model = SimpleSetModel()
        self.base_sample = []
        self.filtered_sample = set()

        self.ui = None
        self.setup_ui()

        self.get_base_sample()


    def setup_ui(self):
        self.ui = Ui_SampleSelectDialog()
        self.ui.setupUi(self)
        self.ui.working_set_view.setModel(self.working_model)
        self.ui.current_view.setModel(self.output_model)
        self.ui.add_filter_button.clicked.connect(self.show_add_filter_dialog)

    def get_base_sample(self,sample_id=None):
        if sample_id is None:
            sample = braviz_tab_data.get_subjects()
        else:
            sample = []
        self.base_sample = sample
        self.update_filters()

    def update_filters(self):
        output_sample = self.base_sample
        output_set = set(output_sample)
        self.filtered_sample = output_set
        self.working_model.set_elements(output_set)

    def show_add_filter_dialog(self):
        params = {}
        dialog = AddFilterDialog(params)
        ret = dialog.exec_()
        if ret == dialog.Accepted:
            filter_name = get_filter_name(params)
            filter_func = get_filter_function()
            #TODO add to model


def get_filter_name(params):
    if params["var_real"] is True:
        name = "%s %s %f"%(params["filter_var"],params["operation"],params["threshold"])
    else:
        name = "%s in {%s}"%(params["filter_var"],", ".join(params["checked_names"]))
    return name

def get_filter_function(params):
    if params["var_real"] is True:
        op = params["operation"]
        if op == "<":
            return lambda x:x<params["threshold"]
        elif op == ">":
            return lambda x:x>params["threshold"]
        else:
            return lambda x:x==params["threshold"]
    else:
        return lambda x:x in params["checked_labels"]


class AddFilterDialog(VariableSelectDialog):
    def __init__(self,params):
        super(AddFilterDialog,self).__init__()
        self.params_dict=params
        self.ui = None
        self.setup_ui()
        self.vars_list_model = braviz_models.VarListModel(checkeable=False)
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.activated.connect(self.update_right_side)

        self.data = None
        self.data_vals = None
        self.jitter = None


        self.finish_ui_setup()


    def setup_ui(self):
        self.ui = Ui_AddFilterDialog()
        self.ui.setupUi(self)
        self.ui.select_button.clicked.connect(self.save_and_accept)

    def update_right_side(self, var_name=None):
        curr_idx = self.ui.tableView.currentIndex()
        var_name = self.vars_list_model.data(curr_idx, QtCore.Qt.DisplayRole)
        self.ui.select_button.setEnabled(True)
        super(AddFilterDialog, self).update_right_side(var_name)

    def create_real_details(self):
        #print "creating real details"
        details_ui = Ui_rational_details()
        details_ui.setupUi(self.ui.details_frame)
        self.details_ui = details_ui
        self.details_ui.optimum_val.valueChanged.connect(self.update_optimum_real_value)
        #try to read values from DB
        db_values = braviz_tab_data.get_min_max_opt_values_by_name(self.var_name)
        if db_values is None:
            self.guess_max_min()
        else:
            self.rational["min"] = db_values[0]
            self.rational["max"] = db_values[1]
            self.rational["opt"] = db_values[2]
        self.set_real_controls()
        self.details_ui.optimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.minimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.maximum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.th_spin.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.th_spin.setValue(self.rational["opt"])
        self.details_ui.th_spin.setMaximum(self.rational["max"])
        self.details_ui.operation_combo.currentIndexChanged.connect(self.update_limits_in_plot)
        self.update_plot(self.data)
        QtCore.QTimer.singleShot(20, self.update_limits_in_plot)

    def create_nominal_details(self):
        super(AddFilterDialog,self).create_nominal_details()
        self.nominal_model.set_checkeable(1)
        self.nominal_model.dataChanged.connect(self.update_limits_in_plot)
        self.connect(self.nominal_model,QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"),self.update_limits_in_plot)

    def update_limits_in_plot(self, *args):
        if self.ui.var_type_combo.currentIndex() != 0:
            self.matplot_widget.add_max_min_opt_lines(None, None, None)
            self.filter_plot()
            return
        mini = self.details_ui.minimum_val.value()
        maxi = self.details_ui.maximum_val.value()
        opti = self.details_ui.optimum_val.value()
        opti = mini + opti * (maxi - mini) / 100
        self.rational["max"] = maxi
        self.rational["min"] = mini
        self.rational["opt"] = opti
        self.matplot_widget.add_max_min_opt_lines(mini, opti, maxi)
        threshold = self.details_ui.th_spin.value()
        self.matplot_widget.add_threshold_line(threshold)
        self.filter_plot()

    def filter_plot(self):
        if self.ui.var_type_combo.currentIndex() != 0:
            unchecked_labels = self.nominal_model.get_unchecked()
            unchecked_indices = np.zeros((len(self.data_vals)),np.bool)
            for i,x in enumerate(self.data_vals):
                if x in unchecked_labels:
                    unchecked_indices[i]=1
            unchecked_data = self.data_vals[unchecked_indices]
            unchecked_jitter = self.jitter[unchecked_indices]
            self.matplot_widget.add_grayed_scatter(unchecked_data,unchecked_jitter)
        else:
            th = self.details_ui.th_spin.value()
            operation = self.details_ui.operation_combo.currentText()
            if operation == "<":
                unselected = (self.data_vals>=th)
            elif operation ==">":
                unselected = (self.data_vals<=th)
            else:
                unselected = (self.data_vals!=th)
            un_data = self.data_vals[unselected]
            un_jitter =self.jitter[unselected]
            self.matplot_widget.add_grayed_scatter(un_data,un_jitter)

    def update_plot(self, data,direct=True):
        np.random.seed(982356032)
        jitter = np.random.rand(len(data))

        self.data = data
        self.data_vals = np.squeeze(data.get_values())
        #print self.data_vals.shape
        self.jitter = jitter

        self.matplot_widget.compute_scatter(data.get_values(), jitter,
                                            x_lab=self.var_name, y_lab="jitter",
                                            urls=data.index.get_values())

    def save_and_accept(self):
        if self.var_name is not None:
            self.save_meta_data()
        if self.params_dict is not None:
            self.params_dict["filter_var"] = self.var_name
            self.params_dict["var_real"] = self.ui.var_type_combo.currentIndex()==0
            if self.params_dict["var_real"]:
                self.params_dict["operation"] = self.details_ui.operation_combo.currentText()
                self.params_dict["threshold"] = self.details_ui.th_spin.value()
            else:
                self.params_dict["checked_labels"] = self.nominal_model.get_checked()
                self.params_dict["checked_names"] = [self.nominal_model.names_dict[l]
                                                     for l in self.params_dict["checked_labels"]]

        self.accept()


if __name__ == "__main__":
    app = QtGui.QApplication([])
    main_window = SampleSelectDilog()
    main_window.show()
    main_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    sys.exit(app.exec_())
