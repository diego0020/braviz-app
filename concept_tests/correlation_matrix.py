__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.axes
import matplotlib.pyplot as plt


import numpy as np
import seaborn as sns
import scipy.stats

from braviz.readAndFilter import tabular_data

variables = range(248,268)
df = tabular_data.get_data_frame_by_index(variables)

sns.set(style="darkgrid")

dpi = 200
#fig = Figure(figsize=(9, 9), tight_layout=True)


f, ax = plt.subplots(figsize=(9, 9))
canvas = FigureCanvas(f)
#f = fig
#ax = fig.add_subplot(111)
cmap = sns.blend_palette(["#00008B", "#6A5ACD", "#F0F8FF",
                          "#FFE6F8", "#C71585", "#8B0000"], as_cmap=True)
def draw():
    plt.sca(ax)
    sns.corrplot(df, annot=False, sig_stars=True, cmap_range="full",
             diag_names=False,sig_corr=False, cmap=cmap, ax=ax,cbar=True)
    print "hola"
    canvas.draw()

app = QtGui.QApplication([])


def get_x_name(x):
    return df.columns[x]
def get_y_name(y):
    return df.columns[y]

corr = df.corr()
p_mat = sns.algo.randomize_corrmat(df.values.T, "both", "True")
p_mat[np.isnan(p_mat)] = 1
p_mat = p_mat.astype(np.int)

def say_name(event):
    QtGui.QToolTip.hideText()
    if event.inaxes == ax:
        x_int , y_int = int(round(event.xdata)) , int(round(event.ydata))
        if y_int<=x_int:
            return
        x_name,y_name = get_x_name(x_int),get_y_name(y_int)
        r = corr.loc[x_name,y_name]
        message = "%s v.s. %s: r = %.2f"%(x_name,y_name,r)
        stars = p_mat[x_int,y_int]
        message+="*".join([""]*stars)
        _,height = canvas.get_width_height()
        point = QtCore.QPoint(event.x,height-event.y)

        g_point = canvas.mapToGlobal(point)
        QtGui.QToolTip.showText(g_point,message)

canvas.mpl_connect("motion_notify_event",say_name)
def update_scatter(event):
    if event.inaxes == ax:
        x_int , y_int = int(round(event.xdata)) , int(round(event.ydata))
        if y_int<=x_int:
            return
        x_name,y_name = get_x_name(x_int),get_y_name(y_int)
        draw_scatter(x_name,y_name)
        print x_name,y_name

canvas.mpl_connect("button_press_event",update_scatter)
#======================================

f2, ax2 = plt.subplots(figsize=(9, 9))
canvas2 = FigureCanvas(f2)

def draw_scatter(x_name,y_name):
    ax2.clear()
    x_vals=df[x_name].get_values()
    y_vals=df[y_name].get_values()
    ax2.scatter(x_vals,y_vals)
    ax2.set_xlabel(x_name)
    ax2.set_ylabel(y_name)
    mat = np.column_stack((x_vals,y_vals))
    mat = mat[np.all(np.isfinite(mat),1),]
    m,b,r,p,e = scipy.stats.linregress(mat)
    print e
    plot_title = "r=%.2f\np=%.5g"%(r,p)
    ax2.set_title(plot_title)
    canvas2.draw()



#=====================================

main_window = QtGui.QMainWindow()

big_frame = QtGui.QFrame()
big_layout = QtGui.QHBoxLayout()
big_frame.setLayout(big_layout)
big_layout.addWidget(canvas)
big_layout.addWidget(canvas2)



main_window.setCentralWidget(big_frame)



QtCore.QTimer.singleShot(0,draw)
main_window.show()
app.exec_()