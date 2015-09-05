from __future__ import division

import braviz

from braviz.utilities import configure_console_logger
from braviz.visualization.simple_vtk import SimpleVtkViewer

__author__ = 'da.angulo39'

configure_console_logger("test_tracula")
v= SimpleVtkViewer()

reader=braviz.readAndFilter.BravizAutoReader()
tracks = reader.get("TRACULA",119,index=True)
img2 =  reader.get("MRI",119,format="vtk",space="subject")
for t0 in tracks:
    #img =  reader.get("TRACULA",119,name=t0,map=True,format="vtk",space="world")
    cont =  reader.get("TRACULA",119,name=t0,space="subject")
    col = reader.get("TRACULA",119,name=t0,color=True)
    ac=v.addPolyData(cont)
    mp = ac.GetMapper()
    mp.ScalarVisibilityOff()
    ac.GetProperty().SetColor(col)


v.addImg(img2)
v.start()