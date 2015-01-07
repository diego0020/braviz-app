import braviz
#todo profile
from braviz import _test_arrow

reader = braviz.readAndFilter.BravizAutoReader()
test_model = "Brain-Stem"
#test_model = "Left-Hippocampus-SPHARM"

fibs = reader.get("fibers","093",waypoint=test_model)
model = reader.get("model","093",name=test_model)

viewer = simpleVtkViewer()
viewer.addPolyData(fibs)
viewer.addPolyData(model)
viewer.start()


__author__ = 'Diego'

