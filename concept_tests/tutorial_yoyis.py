import braviz

#reader=braviz.readAndFilter.kmc40.kmc40Reader(reader'K:\JohanaForero\KAB-db')
#r=braviz.readAndFilter.kmc40.kmc40Reader(r'K:\JohanaForero\KAB-db')
#reader=braviz.readAndFilter.kmc40.kmc40Reader(r'C:\Users\imagine\Documents\juanibarral\yoyis\KAB-db')
from braviz import _test_arrow

reader=reader=braviz.readAndFilter.BravizAutoReader()
r=r=braviz.readAndFilter.BravizAutoReader()
#reader=braviz.readAndFilter.kmc40AutoReader()
#r=braviz.readAndFilter.kmc40AutoReader()

# Sacar lista de pacientes
subjects_list=reader.get('ids')

# Sacar lista de estructuras para el 093
model_list=reader.get('model','144',index=1)
print(model_list)

#leer putamen
putamen=reader.get('model','144',name='Left-Putamen')

#crear visualizador
viewer= simpleVtkViewer()
#viewer=braviz.visualization.vtk.vtkImagePlaneWidget()

#agregar putamen al visualizador
viewer.addPolyData(putamen)

#iniciar visualizador
viewer.start()

#Agregar amygdala
amygdala=reader.get('model','144',name='Right-Amygdala')
viewer.addPolyData(amygdala)
viewer.start()

#Agregar imagen
mri=reader.get('mri','144',format='vtk')
viewer.addImg(mri)
viewer.start()



