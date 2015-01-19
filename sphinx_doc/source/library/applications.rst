.. module:: braviz.applications

Applications
=============

The applications module is where all end-user applications live. Python files in this modules should be
executable. This module also contains the configuration files used in :mod:`braviz.readAndFilter.config_file`.

This page will contain an overview of the scripts located in this module and some guidelines on creating new
applications. For documentation from the user point of view please look at

:doc:`../visual/applications`


.. module::braviz.applications.braviz_menu2

The braviz menu
----------------

The braviz menu is the main entry point for users. It provides an overview of the available tools and provides access
to them. But it also performs several important tasks on the background.

    - Check database integrity (see :doc:`braviz_db`)
    - Rebuild qt interfaces
    - Act as a message broker (see :doc:`communication`)

When an application icon is clicked in the menu, it spawns a new python interpreter with a command line similar to

.. code-block:: console

    python -m braviz.applications.<app_name> <scenario_id> <server_broadcast> <server_receive>

The parameters are

    - **app_name** : The application script
    - **scenario_id** : The id of the initial scenario to load in the application. It is 0 if called from the
      main icon, or the corresponding id if called from the *scenarios* dialog
    - **server_broadcast** : The address that will be used for broadcasting messages.
    - **server_receive** : The address in which the broker will receive messages

Notice that the broadcast and receive addresses will be printed when the server starts. You may use this addresses
to connect to the server from external applications.

For an overview of the menu from the user point of view see :doc:`../visual/menu`

Graphical applications
------------------------

Visualize geometry
^^^^^^^^^^^^^^^^^^^^

.. module:: braviz.applications.subject_overview

Subject Overview
"""""""""""""""""

.. image:: images/subj_overview.png
    :alt: Subject overview screenshot
    :width: 80%
    :align: center

This application provides access to geometrical and tabular data from a single subject.

See :doc:`User documentation <../visual/subject_overview>`.

.. ----------------------------------------------------------------------

.. module:: braviz.applications.sample_overview

Sample Overview
"""""""""""""""""

.. image:: images/sample_overview.png
    :alt: Sample overview screenshot
    :width: 80%
    :align: center

The sample_overview application can load geometric data for several subjects in the same display. Visualizations
are created as scenarios in the subject overview application. They are arranged in rows with respect to a nominal
variable and sorted from left to right with respect to a real variable.

See :doc:`User documentation <../visual/sample_overview>`.

.. ----------------------------------------------------------------------

.. module:: braviz.applications.fmri_explorer

Explore fMRI
"""""""""""""""""

.. image:: images/fmri.png
    :alt: Explore fmri screenshot
    :width: 80%
    :align: center

This application specializes in fMRI data. It shows a timeline with the experiment design and the raw bold signal at
the bottom.

See :doc:`User documentation <../visual/fmri_explore>`.

.. ----------------------------------------------------------------------

.. module:: braviz.applications.check_reg_app

Check Registration
""""""""""""""""""""

.. image:: images/check_reg.png
    :alt: Check registration screenshot
    :width: 80%
    :align: center

This application allows to compare two images in order to check if a registration algorithm was successful or
to compare images from different subjects.

See :doc:`User documentation <../visual/check_reg>`.


Create geometry
^^^^^^^^^^^^^^^^^^^^

Statistics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Command line applications
---------------------------

