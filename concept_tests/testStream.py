import os

import nibabel as nib
import vtk

import braviz
from braviz.readAndFilter.images import write_vtk_image
from braviz.readAndFilter.transforms import applyTransform


kmc_40_reader=braviz.readAndFilter.BravizAutoReader()
root_path=kmc_40_reader.get_data_root()


os.chdir(os.path.join(root_path,'093','camino'))
#r'C:\Users\da.angulo39\Documents\Kanguro\093\camino')

viz=braviz.visualization.simpleVtkViewer()

fa_img=nib.load('FA.nii')

fa_vtk= nibNii2vtk(fa_img)
fa= applyTransform(fa_vtk,fa_img.get_affine())
viz.addImg(fa)
reader=vtk.vtkPolyDataReader()

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
