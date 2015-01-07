import braviz
import vtk
from braviz import _test_arrow
from braviz.readAndFilter.color_fibers import scalars_from_image_int
import numpy as np
from braviz.readAndFilter import filter_fibers
from braviz.readAndFilter.filter_fibers import iter_id_list
from braviz.readAndFilter.images import write_vtk_image
from braviz.readAndFilter.transforms import applyTransform

__author__ = 'Diego'
SUBJ = "119"

reader = braviz.readAndFilter.BravizAutoReader()
fibs1 = reader.get("fibers",SUBJ,space="workd",waypoint=["CC_Anterior"])


aparc = reader.get("APARC",SUBJ,space="diff")
fibs = reader.get("fibers",SUBJ,space="diff")



pd = reader.get("fibers",SUBJ)
img = reader.get("aparc",SUBJ)
#s = filter_fibers.filter_polylines_with_img_numpy_slow(pd,img,251)
#print s


scalars_from_image_int(fibs,aparc)
aparc_vtk = nibNii2vtk(aparc)
aparc_vtk = applyTransform(aparc_vtk,np.linalg.inv(aparc.get_affine()),interpolate=False)

lut = reader.get("APARC",SUBJ,lut=True)


def select_label(fibs,l):
    selection = vtk.vtkSelection()
    selection_node = vtk.vtkSelectionNode()
    selection_node.GetProperties().Set(vtk.vtkSelectionNode.CONTENT_TYPE(), vtk.vtkSelectionNode.THRESHOLDS)
    selection_node.GetProperties().Set(vtk.vtkSelectionNode.FIELD_TYPE(), vtk.vtkSelectionNode.POINT)
    selection.AddNode(selection_node)

    array = vtk.vtkDoubleArray()
    array.SetNumberOfComponents(1)
    array.InsertNextValue(l-.5)
    array.InsertNextValue(l+.5)
    selection_node.SetSelectionList(array)
    extract_lines = vtk.vtkExtractSelection()
    extract_lines.SetInputData(1, selection)
    extract_lines.SetInputData(0, fibs)
    extract_lines.PreserveTopologyOff()
    extract_lines.Update()
    out = extract_lines.GetOutput()
    out_ids = out.GetPointData().GetScalars("vtkOriginalPointIds")

    valid_cell_ids = set()
    for i in xrange(out_ids.GetNumberOfTuples()):
        pt_id = int(out_ids.GetTuple(i)[0])
        id_list2 = vtk.vtkIdList()
        fibs.GetPointCells(pt_id,id_list2)
        valid_cell_ids.update(iter_id_list(id_list2))

    return valid_cell_ids
LBL = 251
valid_cell_ids = select_label(fibs,LBL)

#validate
valid_cell_ids2 = filter_fibers.filter_polylines_with_img(fibs,aparc,LBL)


fibs2 = filter_fibers.extract_poly_data_subset(fibs,valid_cell_ids)
v = simpleVtkViewer()
v.addImg(aparc_vtk)
#v.addPolyData(fibs,lut)
ac = v.addPolyData(fibs2)
#ac.GetProperty().SetColor(1.0,1.0,1.0)
v.start()
