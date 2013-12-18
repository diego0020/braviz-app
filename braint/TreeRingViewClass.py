__author__ = 'jc.forero47'

from vtk import *

class TreeRingViewClass:
    def __init__(self, relations_xml, hierarchies_xml):
        #reader1 = vtkXMLTreeReader()
        #reader1.SetFileName(relations_xml)
        #reader1.SetEdgePedigreeIdArrayName("tree edge")
        #reader1.GenerateVertexPedigreeIdsOff();
        #reader1.SetVertexPedigreeIdArrayName("name");
        
        reader2 = vtkXMLTreeReader()
        reader2.SetFileName(hierarchies_xml)
        reader2.SetEdgePedigreeIdArrayName("graph edge")
        reader2.GenerateVertexPedigreeIdsOff();
        reader2.SetVertexPedigreeIdArrayName("name");



        FILENAME_VERT_TABLE = "testfilenodes.csv"
        FILENAME_EDGE_TABLE = "testfilerelations.csv"


        # Load the vertex table from CSV file
        csv_vert_source = vtkDelimitedTextReader()
        csv_vert_source.SetFieldDelimiterCharacters(",")
        csv_vert_source.DetectNumericColumnsOn()
        csv_vert_source.SetHaveHeaders(True)
        csv_vert_source.SetFileName(FILENAME_VERT_TABLE)

        # Load the edge table from CSV
        csv_edge_source = vtkDelimitedTextReader()
        csv_edge_source.SetFieldDelimiterCharacters(",")
        csv_edge_source.DetectNumericColumnsOn()
        csv_edge_source.SetHaveHeaders(True)
        csv_edge_source.SetFileName(FILENAME_EDGE_TABLE)

        tbl2graph = vtkTableToGraph()
        tbl2graph.SetDirected(True)
        tbl2graph.AddInputConnection(csv_edge_source.GetOutputPort())
        tbl2graph.AddLinkVertex("source", "label", False)
        tbl2graph.AddLinkVertex("target", "label", False)
        tbl2graph.AddLinkEdge("source", "target")
        tbl2graph.SetVertexTableConnection(csv_vert_source.GetOutputPort())


        self.view = vtkTreeRingView()
        self.view.SetTreeFromInputConnection(reader2.GetOutputPort())
        self.view.SetGraphFromInputConnection(tbl2graph.GetOutputPort())
        self.view.SetAreaColorArrayName("level")
        self.view.SetAreaHoverArrayName("label")
        self.view.SetAreaLabelArrayName("name")
        self.view.SetAreaLabelVisibility(True)
        self.view.SetShrinkPercentage(0.02)
        self.view.SetBundlingStrength(.5)
        self.view.Update()
        self.view.SetEdgeColorArrayName("tree edge")
        self.view.SetColorEdges(True)

        #print tbl2graph
        #print reader2

        self.annotation_link = vtk.vtkAnnotationLink()
        self.view.GetRepresentation(0).SetAnnotationLink(self.annotation_link)
        #annotation_link.AddObserver("AnnotationChangedEvent", self.handler)

        theme = vtkViewTheme.CreateOceanTheme()
        theme.SetSelectedCellColor(0.8, 0.8, 0.8)#Cambiar el colorde las lineas
        theme.SetSelectedPointColor(0.8, 0.8, 0.8)#Cambiar el color de la celda seleccionada
        #print theme.GetCellLookupTable()
        #theme.SetSelectedCellColor(1.0, 0.95, 0.75)
        #theme.SetCellLookupTable(1)
        self.view.ApplyViewTheme(theme)
        theme.FastDelete()


        self.renderer = self.view.GetRenderer()
        self.renderer.SetBackground(1.0, 1.0, 1.0)
        self.render_window = vtk.vtkRenderWindow()
        #self.render_window.AddRenderer(self.renderer)

    def set_handler(self, handler):
        self.annotation_link.AddObserver("AnnotationChangedEvent", handler)

    def handler(self, caller, event):
        print 'hola'
        sel = caller.GetCurrentSelection()
        for nn in range(sel.GetNumberOfNodes()):
            sel_ids = sel.GetNode(nn).GetSelectionList()
            print sel_ids.GetValue(0)

    def get_view(self):
        return self.view

    def get_render_window(self):
        return self.render_window


    def init_render(self, render_widget):
        self.view.SetRenderWindow(render_widget.GetRenderWindow())
        self.interactor = render_widget.GetRenderWindow().GetInteractor()
        self.interactor.Initialize()
        self.interactor.Start()

        self.view.ResetCamera()
        self.view.Render()

