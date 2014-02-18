__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow


#load gui
from braviz.interaction.qt_guis.anova import Ui_Anova_gui
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog
import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection

class outcome_select_dialog(QtGui.QDialog):
    def __init__(self):
        super(outcome_select_dialog,self).__init__()
        self.ui=Ui_SelectOutcomeDialog()
        self.ui.setupUi(self)
        self.vars_list_model=braviz_models.var_list_model()
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.activated.connect(self.update_right_side)
    def update_right_side(self):
        curr_idx=self.ui.tableView.currentIndex()
        var_name=self.vars_list_model.data(curr_idx,QtCore.Qt.DisplayRole)
        print "lalalalala: %s"%var_name
        self.ui.var_name.setText(var_name)
        self.ui.save_button.setEnabled(True)
        self.ui.var_type_combo.setEnabled(True)
        conn=get_connection()
        cur=conn.cursor()
        cur.execute("SELECT is_real from variables where var_name=?",(var_name,))
        is_real=cur.fetchone()[0]
        if is_real is not None:
            print is_real
        else:
            print "unknown type, assuming real"
            is_real=False
        if not is_real:
            self.create_nominal_details(var_name)
        conn.close()
    def create_real_details(self):
        pass
    def create_nominal_details(self,var_name):
        print "creating details"
        nom_table_view=QtGui.QTableView()
        model=braviz_models.nominal_variables_meta(var_name)
        nom_table_view.setModel(model)
        details_layout=QtGui.QVBoxLayout()
        details_layout.addWidget(nom_table_view)
        self.ui.details_frame.setLayout(details_layout)




class anova_app(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setup_gui()
    def setup_gui(self):
        self.ui=Ui_Anova_gui()
        self.ui.setupUi(self)
        self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
    def dispatch_outcome_select(self):

        print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count()-1:
            print "dispatching dialog"
            dialog=outcome_select_dialog()
            selection=dialog.exec_()



if __name__ == '__main__':
    import sys
    app=QtGui.QApplication(sys.argv)
    main_window=anova_app()
    main_window.show()
    app.exec_()
