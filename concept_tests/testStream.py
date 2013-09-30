import os

import nibabel as nib
import vtk

import braviz


kmc_40_reader=braviz.readAndFilter.kmc40AutoReader()
root_path=kmc_40_reader.getDataRoot()


os.chdir(os.path.join(root_path,'093','camino'))
#r'C:\Users\da.angulo39\Documents\Kanguro\093\camino')

viz=braviz.visualization.simpleVtkViewer()

fa_img=nib.load('FA.nii')

fa_vtk=braviz.readAndFilter.nibNii2vtk(fa_img)
fa=braviz.readAndFilter.applyTransform(fa_vtk,fa_img.get_affine())
viz.addImg(fa)

reader=vtk.vtkPolyDataReader()
reader.SetFileName('streams.vtk')
reader.Update()
pd=reader.GetOutput()
viz.addPolyData(pd)
viz.start()
del viz
viz=braviz.visualization.simpleVtkViewer()
viz.addImg(fa_vtk)
viz.start()
