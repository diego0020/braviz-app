from __future__ import division
__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow
import functools
import numpy as np

#load gui
from braviz.interaction.qt_guis.anova import Ui_Anova_gui
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog
from braviz.interaction.qt_guis.nominal_details_frame import Ui_nominal_details_frame
from braviz.interaction.qt_guis.rational_details_frame import Ui_rational_details

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection,get_data_frame

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class outcome_select_dialog(QtGui.QDialog):
    def __init__(self,params_dict):
        self.params_dict=params_dict
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
        self.matplot_widget=None
        self.create_matplotlib_frame()
        self.data=tuple()
        self.conn=get_connection()
        self.ui.save_button.pressed.connect(self.save_meta_data)
        self.model=None
        self.ui.select_button.pressed.connect(self.select_and_return)

    def update_right_side(self):
        curr_idx=self.ui.tableView.currentIndex()
        var_name=self.vars_list_model.data(curr_idx,QtCore.Qt.DisplayRole)
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
        self.matplot_widget.compute_scatter(data.get_values())
        self.ui.select_button.setEnabled(True)

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
            self.model=braviz_models.nominal_variables_meta(var_name)
        else:
            self.model.update_model(var_name)
        details_ui=Ui_nominal_details_frame()
        details_ui.setupUi(self.ui.details_frame)
        details_ui.labels_names_table.setModel(self.model)
        self.details_ui=details_ui
        QtCore.QTimer.singleShot(0 , self.update_limits_in_plot)
    def create_matplotlib_frame(self):
        target=self.ui.plot_frame
        layout=QtGui.QVBoxLayout()
        self.matplot_widget=matplotlib_widget()
        layout.addWidget(self.matplot_widget)
        target.setLayout(layout)
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
            self.conn.execute(query,
                              (self.var_name,self.rational["min"],
                               self.rational["max"],self.rational["opt"])
            )
            self.conn.commit()
        elif var_type==0:
            self.model.save_into_db()
        pass
    def select_and_return(self,*args):
        self.params_dict["selected_outcome"]=self.var_name
        self.done(self.Accepted)


class matplotlib_widget(FigureCanvas):
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
        self.jitter=tuple()
    def compute_scatter(self,data):
        self.axes.clear()
        jitter=np.random.rand(len(data))
        self.axes.scatter(data,jitter,color="#2ca25f")
        self.axes.tick_params('y',left='off',labelleft='off')
        self.draw()
        self.back_fig=self.copy_from_bbox(self.axes.bbox)
        self.xlim=self.axes.get_xlim()
        self.data=data
        self.jitter=jitter
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






class anova_app(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setup_gui()
        self.outcome_var_name=None
    def setup_gui(self):
        self.ui=Ui_Anova_gui()
        self.ui.setupUi(self)
        self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
    def dispatch_outcome_select(self):

        print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count()-1:
            print "dispatching dialog"
            params={}
            dialog=outcome_select_dialog(params)
            selection=dialog.exec_()
            if selection>0:
                self.set_outcome_var_type(params["selected_outcome"])
        else:
            self.set_outcome_var_type(self.ui.outcome_sel.itemText(self.ui.outcome_sel.currentIndex()))



    def set_outcome_var_type(self,new_var):
        if new_var == self.outcome_var_name:
            return
        print "succesfully selected %s"%self.outcome_var_name
        index=self.ui.outcome_sel.findText(new_var)
        if index<0:
            #insert
            pass
        self.ui.outcome_sel.setCurrentIndex(index)


        self.outcome_var_name=new_var


if __name__ == '__main__':
    import sys
    app=QtGui.QApplication(sys.argv)
    main_window=anova_app()
    main_window.show()
    app.exec_()
