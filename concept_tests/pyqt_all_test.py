
from __future__ import division

__author__ = 'Diego'

import sys
import sip
sip.setapi('QString',2)
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
import braviz.readAndFilter.read_csv
import numpy as np

class vtk_widget(QVTKRenderWindowInteractor):
    def __init__(self,parent):
        QVTKRenderWindowInteractor.__init__(self,parent)
        self.vtk_render_widget=None
        self.ren=None
        self.renWin=None
        self.initRender()
        self.setMinimumSize(200,200)
    def initRender(self):
        self.Initialize()
        self.Start()
        self.ren=vtk.vtkRenderer()
        self.renWin=self.GetRenderWindow()
        self.renWin.AddRenderer(self.ren)
        cone=vtk.vtkConeSource()
        cone_map=vtk.vtkPolyDataMapper()
        cone_act=vtk.vtkActor()

        cone_act.SetMapper(cone_map)
        cone_map.SetInputConnection(cone.GetOutputPort())
        self.ren.AddActor(cone_act)

        #self.vtk_render_widget.show()
    #def sizeHint(self):
    #    return QtCore.QSize(200, 200)



class matplot_widget(FigureCanvas):
    def __init__(self,parent=None,dpi=100):
        fig=Figure(figsize=(5,5),dpi=dpi)
        self.axes=fig.add_subplot(111)
        #self.axes.hold(False)
        FigureCanvas.__init__(self,fig)


        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
        self.file_name=r"C:\Users\Diego\Documents\kmc40-db\KAB-db\test_small.csv"
        self.group_dict=braviz.readAndFilter.read_csv.get_tuples_dict(self.file_name,"code","UBIC3")
        self.compute_histogram()
    def compute_histogram(self,var_name="VCIIQ"):
        self.axes.clear()
        self.var_dict=braviz.readAndFilter.read_csv.get_tuples_dict(self.file_name,"code",var_name,numeric=True)
        data=[]
        for group in ("1","2","3"):
            data.append(np.array([self.var_dict[i] for i in self.var_dict.iterkeys() if self.group_dict[i] == group
                                 and  not np.isnan(self.var_dict[i]) ]))
        colors=['red', 'green', 'blue']
        n,bins,patches=self.axes.hist(data, normed=True, stacked=True,color=colors)
        self.draw()



class variable_table(QtCore.QAbstractTableModel):
    def __init__(self):
        super(variable_table,self).__init__()
        self.data=None
        self.headers=('Variable','Importance')
    def load_from_csv(self):
        self.data=[]
        with open(r"C:\Users\Diego\Documents\kmc40-db\KAB-db\var_importance.csv") as csv_file:
            for i,line in enumerate(csv_file):
                if i==0:
                    continue  # Headers
                values=line.split(',')
                self.data.append((values[0][1:-1],values[5]))

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data)
    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2
    def data(self, QModelIndex, int_role=None):
        line=QModelIndex.row()
        col=QModelIndex.column()
        if 0 <= line < len(self.data) and 0<=col<2 and int_role==QtCore.Qt.DisplayRole:
            return self.data[line][col]
        else:
            return QtCore.QVariant()
    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        if Qt_Orientation==QtCore.Qt.Vertical:
            return p_int
        else:
            return self.headers[p_int]
    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse=True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse=False
        #self.layoutAboutToBeChanged.emit()
        self.data.sort(key=lambda x:x[p_int],reverse=reverse)
        print "sorting"
        top_left=self.index(0,0)
        button_right=self.index(self.rowCount()-1,self.columnCount()-1)
        #self.layoutChanged.emit()
        #self.dataChanged.emit(top_left,button_right)
        self.modelReset.emit()
    def get_var_name(self,index):
        return self.data[index][0]



class table_widget(QtGui.QTableView):
    def __init__(self,parent=None):
        super(table_widget,self).__init__(parent)
        model=variable_table()
        model.load_from_csv()
        self.setModel(model)
        self.setSortingEnabled(True)
        self.internal_model=model
    def get_var_name(self,index):
        return self.internal_model.get_var_name(index)


class three_widgets(QtGui.QWidget):
    def __init__(self):
        super(three_widgets,self).__init__()
        self.matplot=None
        self.table=None
        self.initUI()


    def initUI(self):
        top_layout=QtGui.QHBoxLayout()

        layout=QtGui.QVBoxLayout()
        vtk_window=vtk_widget(None)
        layout.addWidget(vtk_window,1)

        matplotlib_w=matplot_widget(None)
        layout.addWidget(matplotlib_w,1)
        #layout.setSpacing(0)
        #layout.setContentsMargins(0,0,0,0)
        layout.setMargin(0)
        table=table_widget()
        table.sortByColumn(1,QtCore.Qt.AscendingOrder)
        table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        top_layout.addWidget(table)
        table.setMinimumWidth(200)
        table.activated.connect(self.detect_selection)

        top_layout.addLayout(layout,2)
        self.setLayout(top_layout)
        self.setMinimumSize(200,100)
        self.setBaseSize(800,300)
        #palette=self.palette()
        #palette.setColor(Qt.QPalette.Background,Qt.QColor("blue"))
        #self.setPalette(palette)
        self.setWindowTitle("QtTest")
        self.show()
        self.matplot=matplotlib_w
        self.table=table

    def detect_selection(self,index):
        print "ayayayayay"
        var_name=self.table.get_var_name(index.row())
        print var_name
        self.matplot.compute_histogram(var_name)



def main():
    app=QtGui.QApplication(sys.argv)
    window=three_widgets()
    #window=vtk_widget(None)
    window.show()
    return_code=app.exec_()
    print "app returned %s"%return_code

if __name__ == "__main__":
    main()