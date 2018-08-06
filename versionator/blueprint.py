from collections import defaultdict
from pprint import pprint

from flask import Blueprint, abort, request

from versionator.errors import (
    RouteNotFound,
    VersionNotSupported,
    InvalidVersioningScheme
)


class VersionableBlueprint(Blueprint):
    """A Blueprint subclass for enabling versioning of routes.

    This class operates similarly to a Flask blueprint but supports
    registration of routes per-version and dispatching requests based
    on Accept header or path prefix.
    """

    SCHEMES = ('path', 'header')

    def __init__(self, name, import_name, scheme='header', *args, **kwargs):
        """Initialize a new VersionBlueprint.

        This initializer also accepts one of 'path' or 'header' as a
        versioning scheme (default is 'header').
        """
        super(self.__class__, self).__init__(name, import_name, *args, **kwargs)

        if scheme not in VersionableBlueprint.SCHEMES:
            raise InvalidVersioningScheme(scheme)

        self.versioning_scheme = scheme
        self._routes = defaultdict(dict)

    def register_versions(self, versions):
        """Register multiple API versions, each supporting a list of routes."""
        for version, routes in versions.items():
            self.register_version(version, routes)

    def register_version(self, version, routes):
        """Register an API version supporting a list of routes."""
        for rule, endpoint, view_func, options in routes:
            opts = dict(options, **{'version': version})
            self.route(rule, **opts)(view_func)

    def get(self, rule, **options):
        """Define a GET route handler."""
        return self.route(rule, **dict(options, **{'methods': ('GET',)}))

    def post(self, rule, **options):
        """Define a POST route handler."""
        return self.route(rule, **dict(options, **{'methods': ('POST',)}))

    def add_url_rule(self, rule, endpoint, view_func, **options):
        """Register a route in the internal registry and add it to Blueprint
        deferred functions.
        """
        version = options.pop('version', '*/*')
        if version:
            endpoint = '_'.join([endpoint, version])

        self._register(rule, endpoint, view_func, version)
        super(self.__class__, self).add_url_rule(
            rule,
            endpoint,
            self._version_dispatch(rule),
            **options
        )

    @property
    def versions(self):
        """Generate a serializable dictionary mapping versions to rules to
        handlers.
        """
        return {
            version: {
                rule: {
                    k: str(v)
                    for k, v in route.items()
                }
                for rule, route in rules.items()
            }
            for version, rules in self._routes.items()
        }

    @property
    def rules(self):
        """Generate a dictionary mapping rules to versions to handlers."""
        rules = [
            (rule, version, route)
            for version, rules in self.versions.items()
            for rule, route in rules.items()
        ]

        every = defaultdict(dict)
        for rule, version, route in rules:
            every[rule][version] = route
        return dict(every)

    def _register(self, rule, endpoint, view_func, version):
        """Register a route in the internal routes dictionary."""
        print('Registering {} for {}'.format(rule, version))
        self._routes[version][rule] = {
            'endpoint': endpoint,
            'view_func': view_func
        }

    def _version_dispatch(self, rule):
        """Call a view function for the given rule appropriate for the version
        provided in the request.

        TODO: Add support for falling back to routes registered for */*
        """
        if self.versioning_scheme == 'header':
            lookup_route = self._by_header
        else:
            lookup_route = self._by_path

        def dispatch(*args, **kwargs):
            try:
                version, route = lookup_route(rule, request)
            except RouteNotFound:
                print('No route for {}'.format(rule))
                abort(404)
            except VersionNotSupported:
                print('Version is not supported for {}'.format(rule))
                abort(406)
            except Exception as e:
                print('Another error occurred: {}'.format(e))
                abort(500)

            endpoint = route['endpoint']
            view_func = route['view_func']

            print('Dispatching {} of {}'.format(version, endpoint))

            return view_func(*args, **kwargs)
        return dispatch

    def _by_header(self, rule, req):
        """Look up a route handler for a rule using the Accept header on the
        request.
        """
        accept = req.headers.get('Accept', '*/*')
        if not self._rule_exists(rule):
            raise RouteNotFound
        elif not self._rule_exists(rule, version=accept):
            raise VersionNotSupported

        return accept, self._routes[accept][rule]

    def _by_path(self, rule, req):
        """Look up a route handler for a rule using the request path."""
        print(request.path)
        return None, None

    def _rule_exists(self, rule, version=None):
        """Check whether a handler for the given rule has been registered for
        an optional version.
        """
        pprint(self.rules)
        if not version:
            return rule in self.rules
        return rule in self.versions.get(version, {})
