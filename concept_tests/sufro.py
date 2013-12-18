#from vtk import *
#
#reader1 = vtkXMLTreeReader()
#reader1.SetFileName("treetest.xml")
#reader1.Update()
#
#view = vtkTreeMapView()
#view.SetAreaSizeArrayName("size")
#view.SetAreaColorArrayName("level")
#view.SetAreaLabelArrayName("name")
#view.SetAreaLabelVisibility(False)
#view.SetAreaHoverArrayName("name")
#view.SetLayoutStrategyToSquarify()
#view.SetRepresentationFromInput(reader1.GetOutput())
#
## Apply a theme to the views
#theme = vtkViewTheme.CreateMellowTheme()
#view.ApplyViewTheme(theme)
#theme.FastDelete()
#
#view.ResetCamera()
#view.Render()
#
#view.GetInteractor().Start()



#from vtk import *
#
#reader1 = vtkXMLTreeReader()
#reader1.SetFileName("treetest.xml")
#reader1.Update()
#
#view = vtkTreeRingView()
#view.SetRepresentationFromInput(reader1.GetOutput())
#view.SetAreaSizeArrayName("size")
#view.SetAreaColorArrayName("level")
#view.SetAreaLabelArrayName("name")
#view.SetAreaLabelVisibility(True)
#view.SetAreaHoverArrayName("name")
#view.SetShrinkPercentage(0.05)
#view.Update()
#
## Apply a theme to the views
#theme = vtkViewTheme.CreateMellowTheme()
#view.ApplyViewTheme(theme)
#theme.FastDelete()
#
#view.ResetCamera()
#view.Render()
#
#view.GetInteractor().Start()



from vtk import *

reader1 = vtkXMLTreeReader()
reader1.SetFileName("jerarquiasTest.xml")
reader1.SetEdgePedigreeIdArrayName("tree edge")
reader1.GenerateVertexPedigreeIdsOff();
reader1.SetVertexPedigreeIdArrayName("id");

reader2 = vtkXMLTreeReader()
reader2.SetFileName("treetest.xml")
reader2.SetEdgePedigreeIdArrayName("graph edge")
reader2.GenerateVertexPedigreeIdsOff();
reader2.SetVertexPedigreeIdArrayName("id");

view = vtkTreeRingView()
view.SetTreeFromInputConnection(reader2.GetOutputPort())
view.SetGraphFromInputConnection(reader1.GetOutputPort())
view.SetAreaColorArrayName("level")
view.SetAreaHoverArrayName("id")
view.SetAreaLabelArrayName("id")
view.SetAreaLabelVisibility(True)
view.SetShrinkPercentage(0.02)
view.SetBundlingStrength(.5)
view.Update()
view.SetEdgeColorArrayName("level")
view.SetColorEdges(True)

# Apply a theme to the views
theme = vtkViewTheme.CreateMellowTheme()
view.ApplyViewTheme(theme)
theme.FastDelete()

view.ResetCamera()
view.Render()

view.GetInteractor().Start()