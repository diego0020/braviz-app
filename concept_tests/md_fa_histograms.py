__author__ = 'Diego'

import seaborn as sns
from PyQt4 import QtGui

import numpy as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

#TODO

import braviz
import braviz.readAndFilter.tabular_data as braviz_tab

image_type = "FA"
image_type = "MD"

reader = braviz.readAndFilter.kmc40AutoReader()
#collect all data
subject_codes = braviz_tab.get_data_frame_by_index(braviz_tab.IMAGE_CODE)
non_zeros=[]
for subj in subject_codes.index:
    code = subject_codes["Images_codes"][subj]
    code_str = "{:0>3g}".format(code)
    print code_str
    try:
        image = reader.get(image_type,code_str,space="diff")
    except Exception:
        pass
    else:
        data=image.get_data()
        non_zeros.extend(data[data!=0])

print len(non_zeros)
array = np.array(non_zeros)



fig = Figure()
widget = FigureCanvas(fig)
axes = fig.add_subplot(111)

#axes.hist(array,color=sns.desaturate("indianred", .75))
#axes.hist(array)
axes.set_xlim(0e-9,4e-9)

sns.distplot(array,ax=axes,
             kde_kws={"color": "seagreen", "lw": 3},
             hist_kws={"histtype": "stepfilled", "color": "slategray"})


app = QtGui.QApplication([])
widget.show()
widget.draw()

app.exec_()