from __future__ import division
import braviz
import vtk
import Tkinter as tk

from vtk.tk.vtkTkRenderWindowInteractor import \
    vtkTkRenderWindowInteractor


reader=braviz.readAndFilter.kmc40AutoReader()


#crear visualizador
renWin=vtk.vtkRenderWindow()
ren=vtk.vtkRenderer()
renWin.AddRenderer(ren)
ren.SetBackground(0.5,0,0.5)


##=========GUI============================
root = tk.Tk()
root.title('Tutorial Yoyis')

yoyis_frame=tk.Frame(root)
render_widget = vtkTkRenderWindowInteractor(yoyis_frame,
                                            rw=renWin, width=600,
                                            height=600)

render_widget.grid(sticky='nsew')
yoyis_frame.rowconfigure(0,weight=1)  # para que crezca cuando crece la ventana
yoyis_frame.columnconfigure(0,weight=1)

yoyis_frame.grid(sticky='ewsn')
root.rowconfigure(0,weight=1) # para que crezca cuando crece la ventana
root.columnconfigure(0,weight=1)

#para que no se queje al cerrar la ventana
def clean_exit():
    global renWin
    print "adios"
    renWin.Finalize()
    del renWin
    render_widget.destroy()
    root.quit()
    root.destroy()
root.protocol("WM_DELETE_WINDOW", clean_exit)
#=============================================

#leer putamen
putamen=reader.get('model','093',name='Left-Putamen')

#agregar putamen al visualizador
putamen_mapper=vtk.vtkPolyDataMapper()
putamen_mapper.SetInputData(putamen)
putamen_actor=vtk.vtkActor()
putamen_actor.SetMapper(putamen_mapper)
ren.AddActor(putamen_actor)


#Agregar amygdala
amygdala=reader.get('model','093',name='Right-Amygdala')
amydala_mapper=vtk.vtkPolyDataMapper()
amydala_mapper.SetInputData(amygdala)
amygdala_actor=vtk.vtkActor()
amygdala_actor.SetMapper(amydala_mapper)
ren.AddActor(amygdala_actor)


#Agregar imagen
mri=reader.get('mri','093',format='vtk')
image_plane=braviz.visualization.persistentImagePlane()
image_plane.SetInputData(mri)


#inicializar

interactor = render_widget.GetRenderWindow().GetInteractor()
interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
image_plane.SetInteractor(interactor)
image_plane.On()
interactor.Initialize()
interactor.Start()

root.mainloop()