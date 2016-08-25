"""Utilities for meta-estimators"""
# Author: Joel Nothman
#         Andreas Mueller
# License: BSD

from operator import attrgetter
from functools import update_wrapper


__all__ = ['if_delegate_has_method']


class _IffHasAttrDescriptor(object):
    """Implements a conditional property using the descriptor protocol.

    Using this class to create a decorator will raise an ``AttributeError``
    if none of the items in ``delegate_names`` is an attribute of the base
    object or none of the items has an attribute ``method_name``.

    This allows ducktyping of the decorated method based on
    ``delegate.method_name`` where ``delegate`` is the first item in
    ``delegate_names`` that is an attribute of the base object

    See https://docs.python.org/3/howto/descriptor.html for an explanation of
    descriptors.
    """
    def __init__(self, fn, delegate_names, method_name):
        self.fn = fn
        self.delegate_names = delegate_names
        self.method_name = method_name

        # update the docstring of the descriptor
        update_wrapper(self, fn)

    def __get__(self, obj, type=None):
        # raise an AttributeError if the attribute is not present on the object
        if obj is not None:
            # delegate only on instances, not the classes.
            # this is to allow access to the docstrings.
            for item in self.delegate_names:
                if hasattr(obj, item):
                    attrgetter("{0}.{1}".format(item, self.method_name))(obj)
                    break
            else:
                attrgetter(self.delegate_names[-1])(obj)

        # lambda, but not partial, allows help() to work with update_wrapper
        out = lambda *args, **kwargs: self.fn(obj, *args, **kwargs)
        # update the docstring of the returned function
        update_wrapper(out, self.fn)
        return out


def if_delegate_has_method(delegate):
    """Create a decorator for methods that are delegated to a sub-estimator

    ``delegate`` can be a ``string`` or a ``tuple`` of ``string`` which
    included the name of the sub-estimators as an attribute of the base object
    Example:
    ``@if_delegate_has_method(delegate='sub_estimator')``
    ``@if_delegate_has_method(delegate=('best_sub_estimator_', 'sub_estimator')``
    If type is ``tuple``, decorated methods are assumed to be delegated to the
    first sub-estimator in ``delegate`` that is an attribute of the base object

    This enables ducktyping by hasattr returning True according to the
    sub-estimator.

    >>> from sklearn.utils.metaestimators import if_delegate_has_method
    >>>
    >>>
    >>> class MetaEst(object):
    ...     def __init__(self, sub_est, better_sub_est=None):
    ...         self.sub_est = sub_est
    ...         self.better_sub_est = better_sub_est
    ...
    ...     @if_delegate_has_method(delegate='sub_est')
    ...     def predict(self, X):
    ...         return self.sub_est.predict(X)
    ...
    ...     @if_delegate_has_method(delegate=('sub_est', 'better_sub_est'))
    ...     def predict_cond(self, X):
    ...         if self.better_sub_est is not None:
    ...             return self.better_sub_est.predict_cond(X)
    ...         else:
    ...             return self.sub_est.predict_cond(X)
    ...
    >>> class HasPredict(object):
    ...     def predict(self, X):
    ...         return X.sum(axis=1)
    ...
    ...     def predict_cond(self, X):
    ...         return X.sum(axis=0)
    ...
    >>> class HasNoPredict(object):
    ...     pass
    ...
    >>> hasattr(MetaEst(HasPredict()), 'predict')
    True
    >>> hasattr(MetaEst(HasNoPredict()), 'predict')
    False
    >>> hasattr(MetaEst(HasNoPredict(), HasNoPredict()), 'predict_cond')
    False
    >>> hasattr(MetaEst(HasPredict(), HasNoPredict()), 'predict_cond')
    True
    >>> hasattr(MetaEst(HasNoPredict(), HasPredict()), 'predict_cond')
    False
    >>> hasattr(MetaEst(HasPredict(), HasPredict()), 'predict_cond')
    True
    """
    if not isinstance(delegate, tuple):
        delegate = (delegate,)

    return lambda fn: _IffHasAttrDescriptor(fn, delegate, method_name=fn.__name__)

