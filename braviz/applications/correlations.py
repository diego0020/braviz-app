"""
Exploring correlations between two variables
"""
__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import matplotlib

import braviz.readAndFilter.tabular_data as tab_data
from braviz.interaction.qt_models import VarListModel


matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from braviz.interaction.qt_guis.correlations import Ui_correlation_app

import numpy as np
import seaborn as sns
import scipy.stats
import pandas as pd

class CorrelationMatrixFigure(FigureCanvas):
    SquareSelected = QtCore.pyqtSignal(pd.DataFrame)

    def __init__(self):
        self.f, self.ax = plt.subplots(figsize=(9, 9))
        plt.tight_layout()
        super(CorrelationMatrixFigure, self).__init__(self.f)
        palette = self.palette()
        self.f.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.df = None
        self.corr = None
        self.cmap = sns.blend_palette(["#00008B", "#6A5ACD", "#F0F8FF",
                                       "#FFE6F8", "#C71585", "#8B0000"], as_cmap=True)
        self.mpl_connect("motion_notify_event", self.get_tooltip_message)
        self.mpl_connect("button_press_event",self.square_clicked)
        self.on_draw()

    def on_draw(self):
        plt.sca(self.ax)
        plt.clf()
        self.ax = plt.axes()
        if self.df is None:
            message = "Select two or more variables from list"
            self.ax.text(0.5, 0.5, message, horizontalalignment='center',
                         verticalalignment='center', fontsize=16)
        else:
            plt.sca(self.ax)
            sns.corrplot(self.df, annot=False, sig_stars=True, cmap_range="full",
                         diag_names=False, sig_corr=False, cmap=self.cmap, ax=self.ax, cbar=True)
        plt.tight_layout()
        self.draw()

    def set_variables(self, vars_list):
        print vars_list
        if len(vars_list) < 2:
            self.df = None
            self.corr = None
        else:
            self.df = tab_data.get_data_frame_by_name(vars_list)
            self.corr = self.df.corr()
        self.on_draw()

    def get_tooltip_message(self, event):
        QtGui.QToolTip.hideText()
        if event.inaxes == self.ax and self.df is not None:
            x_int, y_int = int(round(event.xdata)), int(round(event.ydata))
            if y_int <= x_int:
                return
            x_name, y_name = self.df.columns[x_int], self.df.columns[y_int]
            r = self.corr.loc[x_name, y_name]
            message = "%s v.s. %s: r = %.2f" % (x_name, y_name, r)
            _, height = self.get_width_height()
            point = QtCore.QPoint(event.x, height - event.y)

            g_point = self.mapToGlobal(point)
            QtGui.QToolTip.showText(g_point, message)

    def square_clicked(self,event):
        if event.inaxes == self.ax and self.df is not None:
            x_int , y_int = int(round(event.xdata)) , int(round(event.ydata))
            if y_int<=x_int:
                return
            x_name,y_name = self.df.columns[x_int],self.df.columns[y_int]
            df2 = self.df[[x_name,y_name]]
            self.SquareSelected.emit(df2)

class RegFigure(FigureCanvas):
    def __init__(self):
        self.f, self.ax = plt.subplots(figsize=(9, 9))
        super(RegFigure, self).__init__(self.f)
        palette = self.palette()
        self.f.set_facecolor(palette.background().color().getRgbF()[0:3])
        self.draw_initial_message()


    def draw_initial_message(self):
        message = "Click in the correlation matrix"
        self.ax.text(0.5, 0.5, message, horizontalalignment='center',
                     verticalalignment='center', fontsize=16)
        plt.sca(self.ax)
        plt.tight_layout()
        self.draw()
    def draw_reg(self,df):
        assert df.shape[1] == 2
        #print df
        self.ax.clear()
        plt.sca(self.ax)
        y_name,x_name = df.columns
        x_vals=df[x_name].get_values()
        y_vals=df[y_name].get_values()
        plt.sca(self.ax)
        sns.regplot(y_name,x_name,df,ax=self.ax)
        mat = np.column_stack((x_vals,y_vals))
        mat = mat[np.all(np.isfinite(mat),1),]
        m,b,r,p,e = scipy.stats.linregress(mat)
        #print e
        plot_title = "r=%.2f\np=%.5g"%(r,p)
        self.ax.set_title(plot_title)
        plt.tight_layout()
        self.draw()

class CorrelationsApp(QtGui.QMainWindow):
    def __init__(self):
        super(CorrelationsApp, self).__init__()
        self.ui = None
        self.cor_mat = CorrelationMatrixFigure()
        self.reg_plot = RegFigure()
        self.vars_model = VarListModel(checkeable=True)
        self.setup_ui()

    def setup_ui(self):
        self.ui = Ui_correlation_app()
        self.ui.setupUi(self)
        self.ui.variables_list.setModel(self.vars_model)

        self.ui.cor_layout = QtGui.QHBoxLayout()
        self.ui.cor_mat_frame.setLayout(self.ui.cor_layout)
        self.ui.cor_layout.addWidget(self.cor_mat)
        self.vars_model.CheckedChanged.connect(self.cor_mat.set_variables)

        self.ui.reg_layout = QtGui.QHBoxLayout()
        self.ui.reg_frame.setLayout(self.ui.reg_layout)
        self.ui.reg_layout.addWidget(self.reg_plot)

        self.cor_mat.SquareSelected.connect(self.reg_plot.draw_reg)



if __name__ == "__main__":
    app = QtGui.QApplication([])
    main_window = CorrelationsApp()
    main_window.show()
    app.exec_()

