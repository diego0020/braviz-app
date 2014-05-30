from __future__ import division
import braviz



reader=braviz.readAndFilter.BravizAutoReader()
fa_img=reader.get('fa','093',format='vtk')
#fibers=reader.get('fibers','093',color='y')

#fibers=reader.get('fibers','093',color='fa')
fibers=reader.get('fibers','325',color='fa',waypoint='CC_Central')
print fibers.GetNumberOfPoints()


viewer=braviz.visualization.simpleVtkViewer()
viewer.addImg(fa_img)
viewer.addPolyData(fibers)
viewer.start()

