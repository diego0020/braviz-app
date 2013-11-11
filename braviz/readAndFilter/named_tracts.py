__author__ = 'Diego'
# Functions to get special named tracts, All shoud have the signature tract_name(reader,subject,color)
# they return fibers,space tuples, where space is the space of the resulting fibers.. this is used to avoid unnecessary
# transformation of solution
# Try not to import modules into the main namespace in orer for indexing to work

def cortico_spinal_l(reader,subject,color):
    import vtk
    try:
        tracts = reader.get('fibers', subject, space='dartel', waypoint=['ctx-lh-precentral', 'Brain-Stem'],color=color)
    except Exception:
        print "Tracts not found for subject %s"%subject
        raise
        return None

    #first cut
    implicit_plane = vtk.vtkPlane()
    implicit_plane.SetOrigin(6, -61, 80)
    implicit_plane.SetNormal(1, 0, 0)
    extractor = vtk.vtkExtractPolyDataGeometry()
    extractor.SetImplicitFunction(implicit_plane)
    extractor.SetInputData(tracts)

    #second cut
    implicit_plane2 = vtk.vtkPlane()
    implicit_plane2.SetOrigin(36.31049165648922, -77.57854727291647, 28.38018295355981)
    implicit_plane2.SetNormal(0.5489509727116981, 0.8332155694558181, -0.06636749486983169)
    extractor2 = vtk.vtkExtractPolyDataGeometry()
    extractor2.SetImplicitFunction(implicit_plane2)
    extractor2.SetInputConnection(extractor.GetOutputPort())
    extractor2.SetExtractInside(0)
    extractor2.Update()
    tracts3 = extractor2.GetOutput()

    return tracts3,'dartel'


def cortico_spinal_r(reader,subject,color):
    import vtk
    from braviz.readAndFilter import extract_poly_data_subset
    try:
        tracts = reader.get('fibers', subject, space='dartel', waypoint=['ctx-rh-precentral', 'Brain-Stem'],color=color)
    except Exception:
        print "Tracts not found for subject %s" % subject
        return None

#first cut
    implicit_plane = vtk.vtkPlane()
    implicit_plane.SetOrigin(-6, -61, 80)
    implicit_plane.SetNormal(1, 0, 0)
    extractor = vtk.vtkExtractPolyDataGeometry()
    extractor.SetImplicitFunction(implicit_plane)
    extractor.SetInputData(tracts)
    extractor.SetExtractInside(0)

    #second cut
    implicit_plane2 = vtk.vtkPlane()
    implicit_plane2.SetOrigin(-16.328958156651115, -49.25892912169191, -107.77320322976459)
    implicit_plane2.SetNormal(-0.0627833116822967, 0.993338233060421, 0.09663027742174941)
    extractor2 = vtk.vtkExtractPolyDataGeometry()
    extractor2.SetImplicitFunction(implicit_plane2)
    extractor2.SetInputConnection(extractor.GetOutputPort())
    extractor2.SetExtractInside(0)
    extractor2.Update()
    tracts3 = extractor2.GetOutput()

    #move back to world coordinates
    #tracts3 = reader.transformPointsToSpace(tracts3, 'dartel', subject, inverse=True)
    return tracts3,'dartel'

def corpus_callosum(reader,subject,color):
    return reader.get('fibers',subject,operation = 'or',
                waypoint = ['CC_Anterior', 'CC_Central', 'CC_Mid_Anterior','CC_Mid_Posterior', 'CC_Posterior'],
                color=color)   ,  'world'