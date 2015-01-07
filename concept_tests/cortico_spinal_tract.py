from __future__ import division

import vtk

import braviz
from braviz import _test_arrow


__author__ = 'Diego'
left=True
subj='207'
if left is True:

    reader = braviz.readAndFilter.BravizAutoReader()
    viewer = simpleVtkViewer()

    tracts = reader.get('fibers', subj, space='dartel', waypoint=['ctx-lh-precentral', 'Brain-Stem'])

    plane_widget = vtk.vtkPlaneWidget()
    plane_widget.SetInteractor(viewer.iren)
    plane_widget.SetNormal(1, 0, 0)
    plane_widget.SetOrigin(6, -61, 80)
    plane_widget.SetPoint1(6, -61, -80)
    plane_widget.SetPoint2(6, 18, 80)
    plane_widget.SetResolution(20)

    plane_widget.On()
    viewer.addPolyData(tracts)
    viewer.start()

    implicit_plane = vtk.vtkPlane()
    #implicit_plane.SetOrigin(plane_widget.GetCenter())
    implicit_plane.SetOrigin(6, -61, 80)
    #implicit_plane.SetNormal(plane_widget.GetNormal())
    implicit_plane.SetNormal(1, 0, 0)
    extractor = vtk.vtkExtractPolyDataGeometry()
    extractor.SetImplicitFunction(implicit_plane)
    extractor.SetInputData(tracts)

    print plane_widget.GetOrigin()

    extractor.Update()
    tracts2 = extractor.GetOutput()

    plane_widget.SetOrigin(36.31049165648922, -77.57854727291647, 28.38018295355981)
    plane_widget.SetPoint1(-93.14570086200081, 3.985464590588772, -18.400220928124337)
    plane_widget.SetPoint2(52.883191506101454, -94.50026403038649, -46.9855992136296)
    #plane_widget.SetNormal(0.5489509727116981, 0.8332155694558181, -0.06636749486983169)

    viewer.clear_poly_data()
    viewer.addPolyData(tracts2)
    plane_widget.Off()
    viewer.renWin.Render()
    viewer.iren.Start()

    plane_widget.On()
    viewer.renWin.Render()
    viewer.iren.Start()


    #second cut

    print plane_widget

    implicit_plane2 = vtk.vtkPlane()
    #implicit_plane2.SetOrigin(plane_widget.GetOrigin())
    implicit_plane2.SetOrigin(36.31049165648922, -77.57854727291647, 28.38018295355981)
    #implicit_plane2.SetNormal(plane_widget.GetNormal())
    implicit_plane2.SetNormal(0.5489509727116981, 0.8332155694558181, -0.06636749486983169)
    extractor2 = vtk.vtkExtractPolyDataGeometry()
    extractor2.SetImplicitFunction(implicit_plane2)
    extractor2.SetInputConnection(extractor.GetOutputPort())
    #extractor2.SetExtractInside(1)
    extractor2.SetExtractInside(0)
    extractor2.Update()
    tracts3 = extractor2.GetOutput()

    viewer.clear_poly_data()
    viewer.addPolyData(tracts3)
    viewer.renWin.Render()

    viewer.iren.Start()
#======================================================
else:
    reader=braviz.readAndFilter.BravizAutoReader()
    viewer= simpleVtkViewer()

    tracts=reader.get('fibers',subj,space='dartel',waypoint=['ctx-rh-precentral','Brain-Stem'])

    plane_widget=vtk.vtkPlaneWidget()
    plane_widget.SetInteractor(viewer.iren)
    plane_widget.SetNormal(1,0,0)
    plane_widget.SetOrigin(-6,-61,80)
    plane_widget.SetPoint1(-6,-61,-80)
    plane_widget.SetPoint2(-6,18,80)
    plane_widget.SetResolution(20)

    plane_widget.On()
    viewer.addPolyData(tracts)
    viewer.start()

    implicit_plane=vtk.vtkPlane()
    #implicit_plane.SetOrigin(plane_widget.GetCenter())
    implicit_plane.SetOrigin(-6, -61, 80)
    #implicit_plane.SetNormal(plane_widget.GetNormal())
    implicit_plane.SetNormal(1, 0, 0)
    extractor=vtk.vtkExtractPolyDataGeometry()
    extractor.SetImplicitFunction(implicit_plane)
    extractor.SetInputData(tracts)
    extractor.SetExtractInside(0)

    print plane_widget.GetOrigin()

    extractor.Update()
    tracts2=extractor.GetOutput()

    plane_widget.SetOrigin(-16.328958156651115, -49.25892912169191, -107.77320322976459)
    plane_widget.SetPoint1(-84.59925728777262, -62.79875327966965, -12.94382075736059)
    plane_widget.SetPoint2(91.57401606225466, -49.24128524356309, -37.84708997215407)
    #plane_widget.SetNormal(    0.49003561308498134, -0.8694369219247264, -0.0628055467493394)

    viewer.clear_poly_data()
    viewer.addPolyData(tracts2)
    viewer.renWin.Render()
    viewer.iren.Start()

    #second cut
    print "============="
    print plane_widget.GetOrigin()
    print plane_widget.GetNormal()
    print plane_widget.GetPoint1()
    print plane_widget.GetPoint2()

    implicit_plane2=vtk.vtkPlane()
    #implicit_plane2.SetOrigin(plane_widget.GetOrigin())
    implicit_plane2.SetOrigin(-16.328958156651115, -49.25892912169191, -107.77320322976459)
    implicit_plane2.SetNormal(-0.0627833116822967, 0.993338233060421, 0.09663027742174941)
    #implicit_plane2.SetNormal(plane_widget.GetNormal())
    extractor2=vtk.vtkExtractPolyDataGeometry()
    extractor2.SetImplicitFunction(implicit_plane2)
    extractor2.SetInputConnection(extractor.GetOutputPort())
    extractor2.SetExtractInside(0)
    extractor2.Update()
    tracts3=extractor2.GetOutput()

    viewer.clear_poly_data()
    viewer.addPolyData(tracts3)
    viewer.renWin.Render()

    viewer.iren.Start()