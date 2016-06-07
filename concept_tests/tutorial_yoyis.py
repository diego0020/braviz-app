import braviz
from braviz.visualization.simple_vtk import SimpleVtkViewer


reader=reader=braviz.readAndFilter.BravizAutoReader()
r=r=braviz.readAndFilter.BravizAutoReader()
#reader=braviz.readAndFilter.kmc40AutoReader()
#r=braviz.readAndFilter.kmc40AutoReader()

# Sacar lista de pacientes
subjects_list=reader.get('ids')

# Sacar lista de estructuras para el 093
model_list=reader.get('model','119',index=1)
print(model_list)

#leer putamen
putamen=reader.get('model','119',name='Left-Putamen')

#crear visualizador
viewer= SimpleVtkViewer()
#viewer=braviz.visualization.vtk.vtkImagePlaneWidget()

#agregar putamen al visualizador
viewer.addPolyData(putamen)

#iniciar visualizador
viewer.start()

#Agregar amygdala
amygdala=reader.get('model','119',name='Right-Amygdala')
viewer.addPolyData(amygdala)
viewer.start()

#Agregar imagen
mri=reader.get('mri','119',format='vtk')
viewer.addImg(mri)
viewer.start()



