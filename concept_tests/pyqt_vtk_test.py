__author__ = 'Diego'
"""
A simple example that uses the QVTKRenderWindowInteractor
class.
Based on the following gist
https://gist.github.com/fmorency/2596951
"""

#from PySide import QtGui
from PyQt4 import QtGui
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
import sys

if __name__ == '__main__':
    # every QT app needs an app
    app = QtGui.QApplication(['QVTKRenderWindowInteractor'])

    # create the widget
    widget = QVTKRenderWindowInteractor()
    widget.Initialize()
    widget.Start()

    # if you dont want the 'q' key to exit comment this.
    widget.AddObserver("ExitEvent", lambda o, e, a=app: a.quit())

    ren = vtk.vtkRenderer()
    widget.GetRenderWindow().AddRenderer(ren)

    surface = vtk.vtkConeSource()
    surface.SetResolution(8)

    coneMapper = vtk.vtkPolyDataMapper()
    coneMapper.SetInputConnection(surface.GetOutputPort())

    coneActor = vtk.vtkActor()
    coneActor.SetMapper(coneMapper)

    ren.AddActor(coneActor)

    widget.SetPicker(vtk.vtkPointPicker())

    # show the widget
    widget.show()

    # start event processing
    sys.exit(app.exec_())