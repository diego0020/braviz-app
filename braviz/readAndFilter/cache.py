##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


from collections import OrderedDict
import copy
import functools
import logging
import os
import time
import psutil


__author__ = 'diego'


def cache_function(cache_container):
    """
    Decorator which saves function results in memory to speed up repeated requests for the same information

    The decorator uses a :class:`CacheContainer` to store data, and to limit the amount of memory used. Last access
    time is also recorded, and in case that memory needs to be released, data with oldest access time is deleted.

    Args:
        cache_container (braviz.readAndFilter.cache.CacheContainer) : Object used to store data


    """

    def decorator(f):
        f.cache_container = cache_container
        f.cache = f.cache_container.cache
        # print "max cache is %d"%max_cache_size
        # cache will store tuples (output,date)

        @functools.wraps(f)
        def cached_f(*args, **kw_args):
            # print "cache size=%d"%len(cache)
            key = str(args) + str(kw_args)
            key = key.upper()
            if key not in f.cache:
                output = f(*args, **kw_args)
                if output is not None:
                    # new method to test memory in cache
                    process_id = psutil.Process(os.getpid())
                    mem = process_id.memory_info()[0] / (2 ** 20)
                    if mem >= f.cache_container.max_cache:
                        log = logging.getLogger(__name__)
                        log.info("freeing cache")
                        try:
                            while mem > 0.9 * f.cache_container.max_cache:
                                for i in xrange(len(f.cache) // 10 + 1):
                                    rem_key, val = f.cache.popitem(last=False)
                                    # print "removing %s with access time=
                                    # %s"%(rem_key,val[1])
                                mem = process_id.get_memory_info()[
                                    0] / (2 ** 20)
                        except KeyError:
                            log = logging.getLogger(__name__)
                            log.warning(
                                "Cache is empty and memory still too high! check your program for memory leaks")
                    f.cache[key] = (output, time.time())
            else:
                output, _ = f.cache[key]
                # update access time
                f.cache[key] = (output, time.time())
                # return a copy to keep integrity of objects in cache
            try:
                output_copy = output.NewInstance()
                output_copy.DeepCopy(output)
            except AttributeError:
                # not a vtk object
                try:
                    output_copy = copy.deepcopy(output)
                except Exception:
                    output_copy = output
            return output_copy

        return cached_f

    return decorator


class CacheContainer(object):

    """
    Class used to cache data, see :func:`cache_function`
    """

    def __init__(self, max_cache=500):
        """
        Class used to cache data, see :func:`cache_function`

        Args:
            max_cache (float) : Maximum amount of memory in Mb that should be used by the process
        """
        self.__cache = LastUpdatedOrderedDict()
        self.__max_cache = max_cache

    @property
    def max_cache(self):
        """
        Maximum amount of memory in Mb that should be used by the process
        """
        return self.__max_cache

    @max_cache.setter
    def max_cache(self, val):
        self.__max_cache = val

    @property
    def cache(self):
        """
        Data container
        """
        return self.__cache

    def clear(self):
        self.__cache.clear()


class LastUpdatedOrderedDict(OrderedDict):

    """Store items in the order the keys were last updated"""

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)


def memo_ten(f):
    """
    Simple wrapper that holds up to ten function calls in cache.
    """
    f.vals = {}

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in f.vals:
            val = f(*args, **kwargs)
            if len(f.vals) > 10:
                f.vals.clear()
            f.vals[key] = val
            return val
        else:
            return f.vals[key]

    return wrapped


def memoize(obj):
    """A wrapper that saves the return values for a function,
    and returns them if the function is called again with the same arguments.

    .. warning :: There is no limit to the size of the cache in this wrapper, consider using
        :func:`memo_ten`. For large data use func:`cache_function`.

    Args:
        obj (function) : function to wrap
    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if len(kwargs) > 0:
            raise NotImplementedError
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]
    return memoizer
