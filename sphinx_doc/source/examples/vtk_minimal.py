import braviz
reader = braviz.readAndFilter.BravizAutoReader()
fibers = reader.get("fibers",119,space="Talairach",
                    waypoint=["CC_Anterior","CC_Mid_Anterior"],operation="or")
mri = reader.get("MRI",119,space="Talairach",format="vtk")
viewer = braviz.visualization.simpleVtkViewer()
viewer.addImg(mri)
viewer.addPolyData(fibers)
viewer.start()