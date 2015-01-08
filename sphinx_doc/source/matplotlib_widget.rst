.. module:: braviz.visualization.matplotlib_qt_widget

The matplotlib widget
======================

There are two main components for the widget. On top is a QWidget which can be added to Qt applications. This widget
is capable of displaying different types of plots, which are implemented separately.


Main Widget
-----------

.. autoclass:: MatplotWidget
    :members:

Plots
------

All plots should be subclasses of the abstract class

.. autoclass:: AbstractPlot
    :members:


The currently available plots are

.. autoclass:: MatplotBarPlot
.. autoclass:: CoefficientsPlot
.. autoclass:: ResidualsDiagnosticPlot
.. autoclass:: MessagePlot
.. autoclass:: ScatterPlot
.. autoclass:: InterceptPlot