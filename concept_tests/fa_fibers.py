from __future__ import division
import braviz

from braviz.utilities import configure_console_logger
configure_console_logger("fa_fibers")


subj="325"


reader=braviz.readAndFilter.BravizAutoReader()
fa_img=reader.get('md',subj,format='vtk',space="diff")
#fibers=reader.get('fibers','093',color='y')

#fibers=reader.get('fibers','093',color='fa')
#fibers=reader.get('fibers',subj,color='fa',space="diff")
fibers=reader.get('fibers',subj,scalars="md_p",space="diff")
lut = reader.get('fibers',subj,scalars="md_p",lut=True)
print fibers.GetNumberOfPoints()


viewer=braviz.visualization.simpleVtkViewer()
viewer.addImg(fa_img)
viewer.addPolyData(fibers,lut)
viewer.start()

