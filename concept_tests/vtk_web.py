# based on vtk_web_cone.py

r"""
    This module is a VTK Web server application.
    The following command line illustrate how to use it::

        $ vtkpython .../vtk_web_cone.py

    Any VTK Web executable script come with a set of standard arguments that
    can be overriden if need be::
        --host localhost
             Interface on which the HTTP server will listen on.

        --port 8080
             Port number on which the HTTP server will listen to.

        --content /path-to-web-content/
             Directory that you want to server as static web content.
             By default, this variable is empty which mean that we rely on another server
             to deliver the static content and the current process only focus on the
             WebSocket connectivity of clients.

        --authKey vtk-secret
             Secret key that should be provided by the client to allow it to make any
             WebSocket communication. The client will assume if none is given that the
             server expect "vtk-secret" as secret key.
"""

# import to process args
import sys
import os


# import vtk modules.
import vtk
import vtk.web
from vtk.web import protocols, server
from vtk.web import wamp as vtk_wamp

import braviz

import argparse


# =============================================================================
# Create custom File Opener class to handle clients requests
# =============================================================================

class _WebCone(vtk_wamp.ServerProtocol):

    # Application configuration
    view    = None
    authKey = "vtkweb-secret"

    def initialize(self):
        global renderer, renderWindow, renderWindowInteractor, surface, mapper, actor

        # Bring used components
        self.registerVtkWebProtocol(protocols.vtkWebMouseHandler())
        self.registerVtkWebProtocol(protocols.vtkWebViewPort())
        self.registerVtkWebProtocol(protocols.vtkWebViewPortImageDelivery())
        self.registerVtkWebProtocol(protocols.vtkWebViewPortGeometryDelivery())
        self.reader = braviz.readAndFilter.BravizAutoReader()

        # Create default pipeline (Only once for all the session)
        if not _WebCone.view:
            # VTK specific code
            renderer = vtk.vtkRenderer()
            renderWindow = vtk.vtkRenderWindow()
            renderWindow.AddRenderer(renderer)

            renderWindowInteractor = vtk.vtkRenderWindowInteractor()
            renderWindowInteractor.SetRenderWindow(renderWindow)
            renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()



            surface = self.reader.get("SURF","093",hemi="l",name="pial",scalars="curv")
            lut = self.reader.get("SURF_SCALAR","093",hemi="l",scalars="curv",lut=True)
            mapper = vtk.vtkPolyDataMapper()
            actor = vtk.vtkActor()

            mapper.SetInputData(surface)
            mapper.SetLookupTable(lut)
            mapper.UseLookupTableScalarRangeOn()
            mapper.SetColorModeToMapScalars()
            actor.SetMapper(mapper)

            actor.GetProperty().SetOpacity(0.5)

            renderer.AddActor(actor)

            fibs = self.reader.get("FIBERS","093")
            fib_mapper = vtk.vtkPolyDataMapper()
            fib_mapper.SetInputData(fibs)
            fib_actor=vtk.vtkActor()
            fib_actor.SetMapper(fib_mapper)
            renderer.AddActor(fib_actor)

            renderer.ResetCamera()
            renderWindow.Render()

            # VTK Web application specific
            _WebCone.view = renderWindow
            self.Application.GetObjectIdMap().SetActiveObject("VIEW", renderWindow)

# =============================================================================
# Main: Parse args and start server
# =============================================================================

if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(description="VTK/Web Cone web-application")

    # Add default arguments
    server.add_arguments(parser)

    # Exctract arguments
    args = parser.parse_args()
    #default contents dir

    args.content = os.path.join(os.path.dirname(__name__),"vtk_web_content")
    print args

    # Configure our current application
    _WebCone.authKey = args.authKey

    # Start server
    server.start_webserver(options=args, protocol=_WebCone)
