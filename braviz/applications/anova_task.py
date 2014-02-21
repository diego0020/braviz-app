from __future__ import division
__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow
import numpy as np

#load gui
from braviz.interaction.qt_guis.anova import Ui_Anova_gui
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog
from braviz.interaction.qt_guis.nominal_details_frame import Ui_nominal_details_frame
from braviz.interaction.qt_guis.rational_details_frame import Ui_rational_details
from braviz.interaction.qt_guis.regressors_select import Ui_AddRegressorDialog
from braviz.interaction.qt_guis.interactions_dialog import Ui_InteractionsDiealog


import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection,get_data_frame

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure



class VariableSelectDialog(QtGui.QDialog):
    """Implement common features for Oucome and Regressor Dialogs"""
    def __init__(self):
        "remember to call finish_ui_setup() after setting up ui"
        super(VariableSelectDialog,self).__init__()
        self.conn=get_connection()
        self.var_name=None
        self.details_ui=None
        self.rational={}
        self.matplot_widget=None
        self.data=tuple()
        self.model=None


    def update_plot(self,data):
        pass

    def update_right_side(self,var_name):

        #print "lalalalala: %s"%var_name
        self.ui.var_name.setText(var_name)
        self.ui.save_button.setEnabled(True)
        self.ui.var_type_combo.setEnabled(True)
        conn=self.conn
        cur=conn.cursor()
        cur.execute("SELECT is_real from variables where var_name=?",(var_name,))
        is_real=cur.fetchone()[0]
        self.var_name=var_name
        data=get_data_frame(self.var_name)
        self.data=data
        #update scatter
        self.update_plot(data)


        #update gui
        if is_real is not None:
            pass
        else:
            #print "unknown type, assuming real"
            is_real=True
        if is_real:
            self.ui.var_type_combo.setCurrentIndex(0)
            self.update_details(0)
        else:
            self.ui.var_type_combo.setCurrentIndex(1)
            self.update_details(1)
    def update_details(self,index):
        #is_real=self.ui.var_type_combo.currentIndex()
        #print index
        #print "===="
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
        data=self.data
        mini=data.min()[0]
        maxi=data.max(skipna=True)[0]
        medi=data.median()[0]
        self.rational["max"]=maxi
        self.rational["min"]=mini
        self.rational["opt"]=medi
    def set_real_controls(self):
        maxi=self.rational["max"]
        mini=self.rational["min"]
        medi=self.rational["opt"]
        self.details_ui.maximum_val.setValue(maxi)
        self.details_ui.minimum_val.setValue(mini)
        self.details_ui.optimum_val.setValue(int((medi-mini)/(maxi-mini)))
        self.update_optimum_real_value()



    def update_optimum_real_value(self,perc_value=None):
        if perc_value is None:
            perc_value = self.details_ui.optimum_val.value()
        real_value=perc_value/100*(self.rational["max"]-self.rational["min"])+self.rational["min"]
        self.details_ui.optimum_real_value.setNum(real_value)

    def create_real_details(self):
        #print "creating real details"
        details_ui=Ui_rational_details()
        details_ui.setupUi(self.ui.details_frame)
        self.details_ui=details_ui
        self.details_ui.optimum_val.valueChanged.connect(self.update_optimum_real_value)
        #try to read values from DB
        query="SELECT * FROM ratio_meta WHERE var_idx = (SELECT var_idx FROM variables WHERE var_name=?)"
        cur=self.conn.cursor()
        cur.execute(query,(self.var_name,))
        db_values=cur.fetchone()
        if db_values is None:
            self.guess_max_min()
        else:
            self.rational["min"]=db_values[1]
            self.rational["max"]=db_values[2]
            self.rational["opt"]=db_values[3]
        self.set_real_controls()
        self.details_ui.optimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.minimum_val.valueChanged.connect(self.update_limits_in_plot)
        self.details_ui.maximum_val.valueChanged.connect(self.update_limits_in_plot)
        QtCore.QTimer.singleShot(0 , self.update_limits_in_plot)

    def create_nominal_details(self):
        var_name=self.var_name
        #print "creating details"
        if self.model is None:
            self.model=braviz_models.NominalVariablesMeta(var_name)
        else:
            self.model.update_model(var_name)
        details_ui=Ui_nominal_details_frame()
        details_ui.setupUi(self.ui.details_frame)
        details_ui.labels_names_table.setModel(self.model)
        self.details_ui=details_ui
        QtCore.QTimer.singleShot(0 , self.update_limits_in_plot)

    def finish_ui_setup(self):
        target=self.ui.plot_frame
        layout=QtGui.QVBoxLayout()
        self.matplot_widget=MatplotWidget()
        layout.addWidget(self.matplot_widget)
        target.setLayout(layout)
        self.ui.save_button.pressed.connect(self.save_meta_data)
        self.ui.var_type_combo.currentIndexChanged.connect(self.update_details)

    def update_limits_in_plot(self,*args):
        if self.ui.var_type_combo.currentIndex()!=0:
            self.matplot_widget.add_max_min_opt_lines(None,None,None)
            return
        mini=self.details_ui.minimum_val.value()
        maxi=self.details_ui.maximum_val.value()
        opti=self.details_ui.optimum_val.value()
        opti=mini+opti*(maxi-mini)/100
        self.rational["max"]=maxi
        self.rational["min"]=mini
        self.rational["opt"]=opti
        self.matplot_widget.add_max_min_opt_lines(mini,opti,maxi)

    def save_meta_data(self):
        var_type=0 #nominal should be 1
        if self.ui.var_type_combo.currentIndex()==0:
            var_type=1 #real should be 1

        #save variable type
        query="UPDATE variables SET is_real = ? WHERE var_name = ?"
        self.conn.execute(query,(var_type,self.var_name))
        self.conn.commit()


        #save other values
        if var_type==1:
            #real
            query="""INSERT OR REPLACE INTO ratio_meta
            VALUES(
            (SELECT var_idx FROM variables WHERE var_name = ?),
            ? , ? , ? );
            """
            try:
                self.conn.execute(query,
                              (self.var_name,self.rational["min"],
                               self.rational["max"],self.rational["opt"])
                )
            except (KeyError,ValueError):
                pass
            else:
                self.conn.commit()
        elif var_type==0:
            self.model.save_into_db()

class OutcomeSelectDialog(VariableSelectDialog):
    def __init__(self,params_dict):
        super(OutcomeSelectDialog,self).__init__()
        self.ui=Ui_SelectOutcomeDialog()
        self.ui.setupUi(self)
        self.finish_ui_setup()

        self.params_dict=params_dict

        self.vars_list_model=braviz_models.VarListModel()
        self.ui.tableView.setModel(self.vars_list_model)
        self.ui.tableView.activated.connect(self.update_right_side)

        self.ui.select_button.pressed.connect(self.select_and_return)
    def update_right_side(self,var_name=None):
        curr_idx=self.ui.tableView.currentIndex()
        var_name=self.vars_list_model.data(curr_idx,QtCore.Qt.DisplayRole)
        self.ui.select_button.setEnabled(True)
        super(OutcomeSelectDialog,self).update_right_side(var_name)

    def update_plot(self,data):
        self.matplot_widget.compute_scatter(data.get_values(),
                                            x_lab=self.var_name,y_lab="jitter")




    def select_and_return(self,*args):
        self.save_meta_data()
        self.params_dict["selected_outcome"]=self.var_name
        self.done(self.Accepted)


class MatplotWidget(FigureCanvas):
    def __init__(self,parent=None,dpi=100):
        fig=Figure(figsize=(5,5),dpi=dpi,tight_layout=True)
        self.fig=fig
        self.axes=fig.add_subplot(111)
        #self.axes.hold(False)
        FigureCanvas.__init__(self,fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        palette=self.palette()
        fig.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.compute_scatter(tuple())
        self.back_fig=self.copy_from_bbox(self.axes.bbox)
        self.xlim=self.axes.get_xlim()
        self.data=tuple()
        self.data2=tuple()
    def compute_scatter(self,data,data2=None,x_lab=None,y_lab=None):
        self.axes.clear()
        self.axes.yaxis.set_label_position("right")
        if data2 is None:
            data2=np.random.rand(len(data))
            self.axes.tick_params('y',left='off',labelleft='off',labelright='off')
        if x_lab is not None:
            self.axes.set_xlabel(x_lab)
        if y_lab is not None:
            self.axes.set_ylabel(y_lab)

        self.axes.scatter(data,data2,color="#2ca25f")

        self.draw()
        self.back_fig=self.copy_from_bbox(self.axes.bbox)
        self.xlim=self.axes.get_xlim()
        self.data=data
        self.data2=data2
    def add_max_min_opt_lines(self,mini,opti,maxi):

        self.restore_region(self.back_fig)
        if mini is None:
            self.blit(self.axes.bbox)
            return
        opt_line=self.axes.axvline(opti,color="#8da0cb")
        min_line=self.axes.axvline(mini,color="#fc8d62")
        max_line=self.axes.axvline(maxi,color="#fc8d62")
        self.axes.set_xlim(self.xlim)
        self.axes.draw_artist(min_line)
        self.axes.draw_artist(max_line)
        self.axes.draw_artist(opt_line)
        self.blit(self.axes.bbox)

class RegressorSelectDialog(VariableSelectDialog):
    def __init__(self,outcome_var,regressors_model):
        super(RegressorSelectDialog,self).__init__()
        self.outcome_var=outcome_var
        self.ui=Ui_AddRegressorDialog()
        self.ui.setupUi(self)
        self.vars_model=braviz_models.VarAndGiniModel(outcome_var)
        self.ui.tableView.setModel(self.vars_model)
        self.finish_ui_setup()
        self.ui.tableView.activated.connect(self.update_right_side)
        self.ui.add_button.pressed.connect(self.add_regressor)
        self.regressors_table_model=regressors_model
        self.ui.current_regressors_table.setModel(self.regressors_table_model)
        self.ui.current_regressors_table.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.done_button.pressed.connect(self.finish_close)

    def update_right_side(self,name=None):
        curr_idx=self.ui.tableView.currentIndex()
        idx2=self.vars_model.index(curr_idx.row(),0)
        var_name=self.vars_model.data(idx2,QtCore.Qt.DisplayRole)
        self.ui.add_button.setEnabled(True)
        super(RegressorSelectDialog,self).update_right_side(var_name)
    def add_regressor(self):
        self.regressors_table_model.add_regressor(self.var_name)
    def show_context_menu(self, pos):
        globalPos=self.ui.current_regressors_table.mapToGlobal(pos)
        selection=self.ui.current_regressors_table.currentIndex()
        remove_action=QtGui.QAction("Remove",None)
        menu=QtGui.QMenu()
        menu.addAction(remove_action)
        def remove_item(*args):
            self.regressors_table_model.removeRows(selection.row(),1)
        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        selected_item=menu.exec_(globalPos)
        #print selected_item



    def update_plot(self,data):
        regressor_data=data
        if self.outcome_var is not None:
            outcome_data=get_data_frame(self.outcome_var)
            self.matplot_widget.compute_scatter(regressor_data.get_values(),outcome_data.get_values(),
                                                x_lab=self.var_name,y_lab=self.outcome_var)
        else:
            self.matplot_widget.compute_scatter(data.get_values())


    def finish_close(self):
        self.done(self.Accepted)


class InteractionSelectDialog(QtGui.QDialog):
    def __init__(self,regressors_model):
        super(InteractionSelectDialog,self).__init__()
        self.full_model=regressors_model
        regressors=regressors_model.get_regressors()
        self.only_regs_model=braviz_models.AnovaRegressorsModel(regressors)

        self.ui=Ui_InteractionsDiealog()
        self.ui.setupUi(self)
        self.ui.reg_view.setModel(self.only_regs_model)
        self.full_model.show_regressors(False)
        self.ui.full_view.setModel(self.full_model)



class AnovaApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.outcome_var_name=None
        self.regressors_model=braviz_models.AnovaRegressorsModel()
        self.setup_gui()

    def setup_gui(self):
        self.ui=Ui_Anova_gui()
        self.ui.setupUi(self)
        self.ui.outcome_sel.insertSeparator(1)
        self.ui.outcome_sel.setCurrentIndex(2)
        self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        #self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.pressed.connect(self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(self.launch_regressors_context_menu)
        self.ui.add_interaction_button.pressed.connect(self.dispatch_interactions_dialog)


    def dispatch_outcome_select(self):

        #print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count()-1:
            #print "dispatching dialog"
            params={}
            dialog=OutcomeSelectDialog(params)
            selection=dialog.exec_()
            if selection>0:
                self.set_outcome_var_type(params["selected_outcome"])
            else:
                self.set_outcome_var_type(None)
        else:
            self.set_outcome_var_type(self.ui.outcome_sel.itemText(self.ui.outcome_sel.currentIndex()))

    def dispatch_interactions_dialog(self):
        interaction_dialog=InteractionSelectDialog(self.regressors_model)
        interaction_dialog.exec_()
        self.full_model.show_regressors(True)

    def set_outcome_var_type(self,new_bar):
        if new_bar is None:
            var_type_text="Type"
            self.ui.outcome_type.setText(var_type_text)
            self.outcome_var_name=None
            #self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
            return
        new_bar=unicode(new_bar)
        if new_bar == self.outcome_var_name:
            return
        print "succesfully selected %s"%new_bar
        index=self.ui.outcome_sel.findText(new_bar)
        if index<0:
            self.ui.outcome_sel.setCurrentIndex(index)
            self.ui.outcome_sel.insertItem(0,new_bar)
            index=0
            pass
        self.outcome_var_name=new_bar
        self.ui.outcome_sel.setCurrentIndex(index)
        conn=get_connection()
        try:
            var_is_real=conn.execute("SELECT is_real FROM variables WHERE var_name = ? ;",(new_bar,)).fetchone()[0]
        except TypeError:
            var_type_text="Type"
        else:
            var_type_text="Real" if var_is_real else "Nominal"
        self.ui.outcome_type.setText(var_type_text)
        self.check_if_ready()

    def launch_add_regressor_dialog(self):
        reg_dialog=RegressorSelectDialog(self.outcome_var_name,self.regressors_model)
        result=reg_dialog.exec_()
        self.check_if_ready()
    def check_if_ready(self):
        if (self.outcome_var_name is not None) and (self.regressors_model.rowCount()>0):
            self.ui.calculate_button.setEnabled(True)
        else:
            self.ui.calculate_button.setEnabled(False)
    def launch_regressors_context_menu(self,pos):
        globalPos=self.ui.reg_table.mapToGlobal(pos)
        selection=self.ui.reg_table.currentIndex()
        remove_action=QtGui.QAction("Remove",None)
        menu=QtGui.QMenu()
        menu.addAction(remove_action)
        def remove_item(*args):
            self.regressors_model.removeRows(selection.row(),1)
        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        selected_item=menu.exec_(globalPos)




if __name__ == '__main__':
    import sys
    app=QtGui.QApplication(sys.argv)
    main_window=AnovaApp()
    main_window.show()
    app.exec_()
