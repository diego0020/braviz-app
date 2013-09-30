import braviz

subject='093'

#Crear lector
r=braviz.readAndFilter.kmc40AutoReader()


#crear visualizador
v=braviz.visualization.simpleVtkViewer()

#Agregar Fibras
fibers=r.get('fibers',subject,space='talairach',waypoint='CC_Central',color='fa')
v.addPolyData(fibers)

#Agregar imagen
mri=r.get('mri',subject,format='vtk',space='talairach')
v.addImg(mri)

#Agregar Modelo
amygdala=r.get('model',subject,name='Right-Amygdala',space='talairach')
actor=v.addPolyData(amygdala)
#Cambiar color amygdala
actor.GetProperty().SetColor(0,1,0)

#Iniciar
v.start()



