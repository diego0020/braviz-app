Reader
==================

.. currentmodule:: braviz.readAndFilter.base_reader


.. autoclass:: BaseReader

Constructors
------------

    .. automethod:: BaseReader.__init__(self,max_cache=100)
    .. automethod:: BaseReader.get_auto_reader(**kw_args)

The get method
--------------

    .. automethod:: BaseReader.get(self,data, subj_id=None, *args, **kwargs)

Coordinate systems
------------------

    .. automethod:: BaseReader.move_img_to_world(self,img,source_space,subj,interpolate=False)
    .. automethod:: BaseReader.move_img_from_world(self,img,target_space,subj,interpolate=False)
    .. automethod:: BaseReader.transform_points_to_space(self, point_set, space, subj, inverse=False)

Cache
-----

    .. automethod:: BaseReader.clear_mem_cache(self)
    .. automethod:: BaseReader.save_into_cache(self, key, data)
    .. automethod:: BaseReader.load_from_cache(self, key)
    .. automethod:: BaseReader.clear_cache_dir(self,last_word=False)

File System
-----------

    .. automethod:: BaseReader.get_data_root(self)
    .. automethod:: BaseReader.get_dyn_data_root(self)
    .. automethod:: BaseReader.get_auto_data_root()
    .. automethod:: BaseReader.get_auto_dyn_data_root()
    .. automethod:: BaseReader.initialize_dynamic_data_dir(dir_name=None)
    .. automethod:: BaseReader.clear_dynamic_data_dir(dir_name)





