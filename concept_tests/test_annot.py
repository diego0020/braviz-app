import os

import braviz
from braviz import _test_arrow

kmc_40_reader=braviz.readAndFilter.BravizAutoReader()
root_path=kmc_40_reader.get_data_root()
os.chdir(os.path.join(root_path,'232','Surf'))
#'c:/Users/da.angulo39/Documents/Kanguro/232/Surf/'
v= simpleVtkViewer()
surf=braviz.readAndFilter.surfer_input.surface2vtkPolyData('lh.inflated')
labels,ctab,names=braviz.readAndFilter.surfer_input.read_annot('lh.aparc.annot')
braviz.readAndFilter.surfer_input.addScalars(surf,labels)
lut=braviz.readAndFilter.surfer_input.surfLUT2VTK(ctab,names)
v.addPolyData(surf,lut)
v.start()
def color(n):
    l=[0,0,0]
    lut.GetColor(n,l)
    return l
for i in xrange(ctab.shape[0]):
    print i, color(i)