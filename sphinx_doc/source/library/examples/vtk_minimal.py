import braviz
from braviz.visualization.simple_vtk import SimpleVtkViewer

reader = braviz.readAndFilter.BravizAutoReader()
fibers = reader.get("fibers",119,space="Talairach",
                    waypoint=["CC_Anterior","CC_Mid_Anterior"],operation="or")
mri = reader.get("IMAGE",119,space="Talairach",format="vtk", name="MRI")
viewer = SimpleVtkViewer()
viewer.addImg(mri)
viewer.addPolyData(fibers)
viewer.start()