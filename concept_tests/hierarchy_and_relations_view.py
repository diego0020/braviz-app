
from vtk import *

reader1 = vtkXMLTreeReader()
reader1.SetFileName("treetest2.xml")
reader1.SetEdgePedigreeIdArrayName("tree edge")
reader1.GenerateVertexPedigreeIdsOff();
reader1.SetVertexPedigreeIdArrayName("name");

reader2 = vtkXMLTreeReader()
reader2.SetFileName("treetest.xml")
reader2.SetEdgePedigreeIdArrayName("graph edge")
reader2.GenerateVertexPedigreeIdsOff();
reader2.SetVertexPedigreeIdArrayName("name");

view = vtkTreeRingView()
view.SetTreeFromInputConnection(reader2.GetOutputPort())
view.SetGraphFromInputConnection(reader1.GetOutputPort())
view.SetAreaColorArrayName("level")
view.SetAreaHoverArrayName("name")
view.SetAreaLabelArrayName("name")
view.SetAreaLabelVisibility(True)
view.SetShrinkPercentage(0.02)
view.SetBundlingStrength(.5)
view.Update()
view.SetEdgeColorArrayName("tree edge")
view.SetColorEdges(True)

annotation_link = vtk.vtkAnnotationLink()
view.GetRepresentation(0).SetAnnotationLink(annotation_link)


def handler(caller, event):
    print 'hola'
    sel = caller.GetCurrentSelection()
    for nn in range(sel.GetNumberOfNodes()):
        sel_ids = sel.GetNode(nn).GetSelectionList()
        field_type = sel.GetNode(nn).GetFieldType()
        #print 'sel ids: ', sel_ids, 'number of tuples', sel_ids.GetNumberOfTuples()
        print sel_ids.GetValue(0)
        #print 'fieldType: ', field_type

        #if field_type == 3:
        #    print "Vertex selection Pedigree IDs"
        #if field_type == 4:
        #    print "Edge selection Pedigree IDs"
        #if sel_ids.GetNumberOfTuples() > 0:
        #    for ii in range(sel_ids.GetNumberOfTuples()):
        #        print int(sel_ids.GetTuple1(ii))
        #else:
        #    print "-- empty"
    #print sel
    #print 'paso algo'

annotation_link.AddObserver("AnnotationChangedEvent", handler)

# Apply a theme to the views
theme = vtkViewTheme.CreateOceanTheme()
theme.SetSelectedCellColor(0.0, 0.0, 0.0)#Cambiar el colorde las lineas
theme.SetSelectedPointColor(0.0, 0.0, 0.0)#Cambiar el color de la celda seleccionada
#print theme.GetCellLookupTable ()
#theme.SetSelectedCellColor(1.0, 0.95, 0.75)
view.ApplyViewTheme(theme)
theme.FastDelete()

view.ResetCamera()
view.Render()


view.GetInteractor().Start()

