from __future__ import division
__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow


#load gui
from braviz.interaction.qt_guis.anova import Ui_Anova_gui
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog
from braviz.interaction.qt_guis.nominal_details_frame import Ui_nominal_details_frame
from braviz.interaction.qt_guis.rational_details_frame import Ui_rational_details

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection,get_data_frame

class outcome_select_dialog(QtGui.QDialog):
    def __init__(self):
        super(outcome_select_dialog,self).__init__()
        self.ui=Ui_SelectOutcomeDialog()
        self.ui.setupUi(self)
        self.vars_list_model=braviz_models.var_list_model()
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.activated.connect(self.update_right_side)
        self.ui.var_type_combo.currentIndexChanged.connect(self.update_details)
        self.var_name=None
        self.details_ui=None
        self.rational={}
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
        self.var_name=var_name
        if is_real is not None:
            print is_real
        else:
            print "unknown type, assuming real"
            is_real=True
        conn.close()
        if is_real:
            self.ui.var_type_combo.setCurrentIndex(0)
            self.update_details(0)
        else:
            self.ui.var_type_combo.setCurrentIndex(1)
            self.update_details(1)

    def update_details(self,index):
        #is_real=self.ui.var_type_combo.currentIndex()
        print index
        print "===="
        self.clear_details_frame()
        if index==0:
            QtCore.QTimer.singleShot(0 , self.create_real_details)
        else:
            QtCore.QTimer.singleShot(0 , self.create_nominal_details)
    def clear_details_frame(self,layout=None):
        if layout is None:
            layout=self.ui.details_frame.layout()
        if layout is None:
            return
        for i in reversed(xrange(layout.count())):
            item = layout.itemAt(i)
            if isinstance(item, QtGui.QWidgetItem):
                item.widget().close()
            elif isinstance(item, QtGui.QSpacerItem):
                pass
            else:
                self.clearLayout(item.layout())
            layout.removeItem(item)
        layout.deleteLater()
    def guess_max_min(self):
        data=get_data_frame(self.var_name)
        mini=data.min()[0]
        maxi=data.max(skipna=True)[0]
        medi=data.median()[0]
        self.rational["max"]=maxi
        self.rational["min"]=mini
        self.rational["opt"]=medi
        self.details_ui.maximum_val.setValue(maxi)
        self.details_ui.minimum_val.setValue(mini)
        self.details_ui.optimum_val.setValue(medi)

        self.update_slider_position(medi)

    def update_slider_position(self,value):
        mini=self.rational.get("min",0)
        maxi=self.rational.get("max",100)
        self.details_ui.horizontalSlider.setValue(int((value-mini)/(maxi-mini)*100))

    def update_optimum(self,value):
        mini=self.rational.get("min",0)
        maxi=self.rational.get("max",100)
        real_value=mini+(maxi-mini)*value/100
        self.details_ui.optimum_val.setValue(real_value)

    def create_real_details(self):
        print "creating real details"
        details_ui=Ui_rational_details()
        details_ui.setupUi(self.ui.details_frame)
        self.details_ui=details_ui
        self.details_ui.optimum_val.valueChanged.connect(self.update_slider_position)
        self.details_ui.horizontalSlider.sliderMoved.connect(self.update_optimum)
        self.guess_max_min()
    def create_nominal_details(self):
        var_name=self.var_name
        print "creating details"
        model=braviz_models.nominal_variables_meta(var_name)
        details_ui=Ui_nominal_details_frame()
        details_ui.setupUi(self.ui.details_frame)
        details_ui.labels_names_table.setModel(model)
        self.details_ui=details_ui





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
