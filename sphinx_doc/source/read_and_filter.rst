.. module:: braviz.readAndFilter

***********************************
Read And Filter
***********************************

Contents
---------

.. toctree::
   :maxdepth: 2

   reader
   braviz_db
   configuring
   low level functions <read_low_level>


Basic Usage
------------

There are three basic operations that the readAndFilter module provides.

- Read geometric data (images, surfaces, structures, fibers): Use :func:`BravizAutoReader` to get an appropriate
  project reader. Afterwards use its :meth:`~braviz.readAndFilter.base_reader.BaseReader.get` method to access the data.

- Read tabular data: This data is stored inside the braviz Data Base. Use the module
  :mod:`~braviz.readAndFilter.tabular_data` to access it.

- Read system configuration: User are able to configure the system using a configuration file. Applications should
  always honor this configuration. Use the module :mod:`~braviz.readAndFilter.config_file` to access
  this information.

Base Module Contents
---------------------
.. data:: PROJECT

   Name of the current project, read from the configuration file

.. class:: project_reader

    A :class:`~braviz.readAndFilter.base_reader.BaseReader` subclass appropriate for the current project

.. function:: BravizAutoReader

    Constructs a :class:`~braviz.readAndFilter.base_reader.BaseReader` instance based on the configuration file,
    the current host, and the hosts configuration file (see :doc:`configuring`).

.. function:: braviz_auto_data_root

    Gets the root for geometric data files from the hosts configuration file (see :doc:`configuring`) and the
    current host

.. function:: braviz_auto_dynamic_data_root

    Gets the root for braviz data files from the hosts configuration file (see :doc:`configuring`) and the
    current host

