"""
    This is the hl7v2 dispatch mechanism. The purpose is to locate a function
    which is responsible for processing a request.


"""
import re

from django.conf import settings
from django.core.urlresolvers import get_callable
from django.utils.importlib import import_module

from hl7v2_django import responses


class pattern(object):
    def __init__(self, regex, view, kwargs=None):
        """
            regular expression to match
            path to view
            key word args passed through to view
        """
        self.regex_str = regex
        if kwargs:
            self.kwargs = kwargs
        else:
            self.kwargs = {}
        self.regex = re.compile(regex, re.UNICODE)
        self.view = view
        if callable(view):
            self._view = view
        else:
            self._view = None

    def __str__(self):
        return 'Pattern(%s, %s, %s)' % (self.regex_str, self.view, self.kwargs)

    def callback(self, request, args, kwargs):
        if self._view is None:
            self._view = get_callable(self.view)
        return self._view(request, *args, **kwargs)


class Dispatcher(object):
    def __init__(self):
        root = settings.ROOT_HL7_DISPATCH_CONFIG
        self.root = getattr(import_module(root), 'rules')

    def dispatch(self, request):
        path = '%s/%s/%s' % (unicode(request['MSH'][0][8]),
            request['MSH'][0][4], request['MSH'][0][5])
        for pattern in self.root:
            match = pattern.regex.search(path)
            if match:
                kwargs = match.groupdict()
                if kwargs:
                    args = ()
                else:
                    args = match.groups()
                # In both cases, pass any extra_kwargs as **kwargs.
                kwargs.update(pattern.kwargs)
                return pattern.callback(request, args, kwargs)

        return responses.hl7NAK('AE', 'No handler configured to handle request %s, app %s, facility %s' % 
            (unicode(request['MSH'][0][8]), request['MSH'][0][4], request['MSH'][0][5]))



