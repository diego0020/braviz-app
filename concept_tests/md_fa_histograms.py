__author__ = 'Diego'

import seaborn as sns
from PyQt4 import QtGui, QtCore

import numpy as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from scipy import ndimage
#TODO

import braviz
import braviz.readAndFilter.tabular_data as braviz_tab


reader = braviz.readAndFilter.BravizAutoReader()

def load_data(image_type):
    #collect all data
    subject_codes = braviz_tab.get_data_frame_by_index(braviz_tab.IMAGE_CODE)
    scalar_list=[]
    for subj in subject_codes.index:
        code = subject_codes["Images_codes"][subj]
        code_str = "{:0>3g}".format(code)
        print code_str
        try:
            image = reader.get(image_type,code_str)
            fibers = reader.get("fibers",code_str,space="world")
        except Exception as e:
            print "not found"
            print e.message
        else:
            affine = image.get_affine()
            iaffine = np.linalg.inv(affine)
            data = image.get_data()
            npoints = fibers.GetNumberOfPoints()
            zeros = np.zeros((npoints,3))
            for i in xrange(npoints):
                coords = fibers.GetPoint(i) + (1,)
                coords = np.dot(iaffine,coords)
                coords = coords[:3]/coords[3]
                zeros[i]=coords
            image_vals = ndimage.map_coordinates(data,zeros.T,order=1)
            scalar_list.append(image_vals)
            print len(scalar_list)
    scalars_array=np.concatenate(scalar_list)
    print scalars_array.shape
    return scalars_array




class AppForm(QtGui.QMainWindow):
    def __init__(self, parent=None,image_type="FA"):
        QtGui.QMainWindow.__init__(self, parent)
        #self.x, self.y = self.get_data()
        self.create_main_frame()
        self.image_type = image_type
        self.data = None
        self.get_data()
        self.on_draw()

    def create_main_frame(self):
        self.main_frame = QtGui.QWidget()

        self.fig = Figure((5.0, 4.0), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.canvas.setFocus()

        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.canvas)  # the matplotlib canvas
        vbox.addWidget(self.mpl_toolbar)
        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)


    def on_draw(self):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        #self.axes.plot(self.x, self.y, 'ro')
        self.draw_histogram()
        #self.axes.plot([1,2,3])
        self.canvas.draw()

    def on_key_press(self, event):
        print('you pressed', event.key)
        # implement the default mpl key press events described at
        # http://matplotlib.org/users/navigation_toolbar.html#navigation-keyboard-shortcuts
        key_press_handler(event, self.canvas, self.mpl_toolbar)

    def get_data(self):
        image_type = self.image_type


        cache_key = "%s-histogram-in-fibers"%image_type
        #try to read from cache
        scalars_array=reader.load_from_cache(cache_key)

        #collect all data
        if scalars_array is None:
            scalars_array = load_data(image_type)
            reader.save_into_cache(cache_key,scalars_array)

        self.data = scalars_array

    def draw_histogram(self):

        scalars_array = self.data

        p1,p5,p95,p99 = np.percentile(scalars_array,(1, 5, 95, 99))

        print "max:", scalars_array.max()
        print "min:", scalars_array.min()
        print "5p:", p5
        print "95p:", p95

        fig = self.fig
        axes = fig.add_subplot(111)


        if self.image_type == "MD":
            axes.set_xlim(0,12e-10)
            sns.distplot(scalars_array,ax=axes,
                     kde_kws={"color": "seagreen", "lw": 3, "gridsize":200,"clip":(0,p99)},
                     hist_kws={"histtype": "stepfilled", "color": "slategray"})
        else:
            sns.distplot(scalars_array,ax=axes,
                     kde_kws={"color": "seagreen", "lw": 3,},
                     hist_kws={"histtype": "stepfilled", "color": "slategray"})




def main():
    import sys
    image_type = "MD"
    #image_type = "FA"
    app = QtGui.QApplication(sys.argv)
    form = AppForm(image_type=image_type)
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()