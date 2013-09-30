import Tkinter as tk

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor
from numpy.linalg import inv

import braviz.readAndFilter

#reader=braviz.readAndFilter.kmc40.kmc40Reader(r'C:\Users\da.angulo39\Documents\Kanguro')
reader=braviz.readAndFilter.kmc40AutoReader()
niiImg=reader.get('MRI','093')
img=braviz.readAndFilter.nibNii2vtk(niiImg)
img2=braviz.readAndFilter.applyTransform(img, inv(niiImg.get_affine()))

picker = vtk.vtkCellPicker()
picker.SetTolerance(0.005)

#Visualization
ren=vtk.vtkRenderer()
renWin=vtk.vtkRenderWindow()
renWin.AddRenderer(ren)
ren.SetBackground(0.1, 0.1, 0.2)
#interactor=vtk.vtkRenderWindowInteractor()
#interactor.SetRenderWindow(renWin)
#interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
planeWidget=vtk.vtkImagePlaneWidget()
planeWidget.SetInputData(img2)
planeWidget.SetResliceInterpolateToNearestNeighbour() # Sin interpolar
#planeWidget.SetInteractor(interactor)
planeWidget.SetPlaneOrientationToXAxes()
planeWidget.SetSliceIndex(138)
planeWidget.UpdatePlacement()
planeWidget.DisplayTextOn()
planeWidget.SetPicker(picker)
renWin.SetSize(600, 600)
#renWin.Render()
#interactor.Initialize()

#interactor.Start()

# An outline is shown for context.
outline = vtk.vtkOutlineFilter()
outline.SetInputData(img2)

outlineMapper = vtk.vtkPolyDataMapper()
outlineMapper.SetInputConnection(outline.GetOutputPort())

outlineActor = vtk.vtkActor()
outlineActor.SetMapper(outlineMapper)
ren.AddActor(outlineActor)

#==============================Text Actor=========================

text2=vtk.vtkTextActor()
cor=text2.GetPositionCoordinate()
cor.SetCoordinateSystemToNormalizedDisplay()
text2.SetPosition([0.99,0.01])
text2.SetInput('probando')
tprop=text2.GetTextProperty()
tprop.SetJustificationToRight()
tprop.SetFontSize(18)
ren.AddActor(text2)
print img2.GetOrigin()
def interactTest(obj,event):
    #print event
    x,y,z=planeWidget.GetCurrentCursorPosition()
    img2=planeWidget.GetInput()
    x0,y0,z0=img2.GetOrigin()
    dx,dy,dz=img2.GetSpacing()
    x1=x0+dx*x
    y1=y0+dy*y
    z1=z0+dz*z
    message='(%d, %d, %d)' % (x1,y1,z1)
    text2.SetInput(message)

planeWidget.AddObserver('InteractionEvent',interactTest)
planeWidget.AddObserver('StartInteractionEvent',interactTest)
#===============================Inteface=====================================

root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
display_frame = tk.Frame(top)
display_frame.pack(side="top", anchor="n", fill="both", expand="true")
renderer_frame = tk.Frame(display_frame)
renderer_frame.pack(padx=3, pady=3,side="left", anchor="n",
                    fill="both", expand="true")

render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                            rw=renWin,width=600,
                                            height=600)

render_widget.pack(fill='x', expand='false')                                            
display_frame.pack(side="top", anchor="n", fill="both", expand="true")
iact = render_widget.GetRenderWindow().GetInteractor()

planeWidget.SetInteractor(iact)
planeWidget.On()

cam1 = ren.GetActiveCamera()
cam1.Elevation(80)
cam1.SetViewUp(0, 0, 1)
cam1.Azimuth(80)
ren.ResetCameraClippingRange()
render_widget.Render()

def clean_exit():
    global renWin
    print "adios"
    renWin.Finalize()
    del renWin
    render_widget.destroy()
    root.quit()
    root.destroy()
top.protocol("WM_DELETE_WINDOW", clean_exit)



iact.Initialize()
renWin.Render()
iact.Start()

# Start Tkinter event loop
root.mainloop()