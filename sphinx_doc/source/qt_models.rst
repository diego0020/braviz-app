.. module:: braviz.interaction.qt_models


*************************************
Braviz Qt Models
*************************************

This module provides several classes that can be used in the
`Model / View <http://qt-project.org/doc/qt-4.8/model-view-programming.html>`_ Qt pattern,
so they inherit from `http://qt-project.org/doc/qt-4.8/qabstractitemmodel.html <QAbstractItemModel>`_.
Only methods that are not part of the Qt interface are shown here.


Generic models
---------------

This models are designed to be generic, and they don't make any assumptions about the data.

.. autoclass:: SimpleSetModel
    :members:

.. autoclass:: SimpleCheckModel
    :members:

Tabular Data Models
--------------------

These models are designed to work with the braviz database and to allow users to interact with the data stored
there through a graphical interface.

Variables
^^^^^^^^^^^^

.. autoclass:: VarListModel
    :members:

.. autoclass:: SubjectDetails
    :members:

.. autoclass:: ContextVariablesModel
    :members:

.. autoclass:: NewVariableValues
    :members:

.. autoclass:: NominalVariablesMeta
    :members:

Subjects and samples
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: SampleTree
.. autoclass:: SubjectsTable
.. autoclass:: SamplesFilterModel
.. autoclass:: SamplesSelectionModel
.. autoclass:: SubjectChecklist
.. autoclass:: SubjectCheckTable


Statistics
^^^^^^^^^^^

.. autoclass:: VarAndGiniModel
.. autoclass:: AnovaRegressorsModel
.. autoclass:: AnovaResultsModel

Bundles
-----------------------

.. autoclass:: SimpleBundlesList
.. autoclass:: BundlesSelectionList

Scenarios
-----------

.. autoclass:: ScenariosTableModel

.. module:: braviz.interaction.qt_structures_model

Structures model
-----------------

.. autoclass:: StructureTreeModel
.. autoclass:: StructureTreeNode

.. module:: braviz.interaction.logic_bundle_model

Logic bundle model
-------------------

.. autoclass:: LogicBundleQtTree
.. autoclass:: LogicBundleNode
.. autoclass:: LogicBundleNodeWithVTK
