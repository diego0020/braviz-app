from __future__ import division, print_function

from braviz.utilities import configure_logger_from_conf
from braviz.readAndFilter import BravizAutoReader, config_file
from braviz.readAndFilter.filter_fibers import FilterBundleWithSphere, extract_poly_data_subset

import vtk
import numpy as np

configure_logger_from_conf()
cfg = config_file.get_apps_config()
subj = cfg.get_default_subject()
reader = BravizAutoReader()


fibs = reader.get("FIBERS", subj)
ctr = fibs.GetCenter()
b = fibs.GetBounds()
d = np.linalg.norm(np.array((b[0], b[2], b[4])) - np.array((b[1], b[3], b[5])))

win = vtk.vtkRenderWindow()
iren = vtk.vtkRenderWindowInteractor()
ren = vtk.vtkRenderer()

ren.GradientBackgroundOn()
ren.SetBackground2((0.5, 0.5, 0.5))
ren.SetBackground((0.2, 0.2, 0.2))

win.AddRenderer(ren)
iren.SetRenderWindow(win)
iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

iren.Initialize()

# context

img = reader.get("IMAGE",subj,name="MRI", format="VTK")
img_plane_widget = vtk.vtkImagePlaneWidget()
img_plane_widget.SetInteractor(iren)
img_plane_widget.SetInputData(img)
img_plane_widget.SetPlaneOrientation(1)
img_plane_widget.SetSliceIndex(img.GetDimensions()[1]//2)
img_plane_widget.On()

# sphere widget
sphere_w = vtk.vtkSphereWidget2()
sphere_w.SetPriority(10)
sphere_w.SetInteractor(iren)
sphere_w.CreateDefaultRepresentation()
sphere_r = sphere_w.GetRepresentation()
sphere_r.SetCenter(ctr)
sphere_r.SetRadius(d/32)
sphere_w.On()

sphere_r.HandleVisibilityOn()
handle_prop = sphere_r.GetHandleProperty()
radius_prop = sphere_r.GetRadialLineProperty()
radius_prop.SetColor(0., 0., 0.)
fibs_mapper = vtk.vtkPolyDataMapper()
fibs_actor = vtk.vtkActor()
fibs_actor.SetMapper(fibs_mapper)
ren.AddActor(fibs_actor)
ren.ResetCamera()

sphere_filter = FilterBundleWithSphere()
sphere_filter.set_bundle(fibs)

fibs2 = sphere_filter.filter_bundle_with_sphere(sphere_r.GetCenter(),sphere_r.GetRadius())
fibs_mapper.SetInputData(fibs2)

def update_fibs(object=None,event=None):
    radius = sphere_r.GetRadius()
    center = sphere_r.GetCenter()
    fib_ids_center = sphere_filter.filter_bundle_with_sphere(center, radius, get_ids=True)
    ctr2 = 2*np.array(sphere_r.GetHandlePosition()) - center
    fib_ids_side = sphere_filter.filter_bundle_with_sphere(ctr2, radius/2, get_ids=True)
    final_ids = fib_ids_center.intersection(fib_ids_side)
    fibs2 = extract_poly_data_subset(fibs, final_ids)
    fibs_mapper.SetInputData(fibs2)

update_fibs()
sphere_w.AddObserver("InteractionEvent",update_fibs)

iren.Start()
