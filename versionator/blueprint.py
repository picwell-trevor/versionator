from collections import defaultdict

from flask import Blueprint, abort, request

from versionator.errors import (
    RouteNotFound,
    MethodNotSupported,
    VersionNotSupported,
    InvalidVersioningScheme
)


def _dd_defaultdict():
    return defaultdict(_dd_defaultdict)


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
        super(VersionableBlueprint, self).__init__(name, import_name, *args, **kwargs)

        if scheme not in VersionableBlueprint.SCHEMES:
            raise InvalidVersioningScheme(scheme)

        self.versioning_scheme = scheme
        self._routes = defaultdict(list)

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
            endpoint = '_'.join([endpoint, version.replace('.', '_')])

        self._register(
            rule,
            endpoint,
            view_func,
            options.get('methods'),
            version
        )

        super(VersionableBlueprint, self).add_url_rule(
            rule,
            endpoint,
            self._version_dispatch(rule),
            **options
        )

    @property
    def rules(self):
        """Group all registered routes by rule, version, and request method.

        TODO: Make this less nasty
        """
        rules = _dd_defaultdict()
        for rule, routes in self._routes.items():
            for endpoint, view_func, methods, version in routes:
                for method in methods:
                    rules[rule][version][method] = {
                        'endpoint': endpoint,
                        'view_func': view_func
                    }
        return dict(rules)

    def _register(self, rule, endpoint, view_func, methods, version):
        """Register a route in the internal routes dictionary."""
        methods = methods or ('ANY',)
        for method in methods:
            print(
                'Registering {} for {} {}'.format(rule, method, version)
            )
            route = (endpoint, view_func, methods, version)
            self._routes[rule].append(route)

    def _version_dispatch(self, rule):
        """Call a view function for the given rule appropriate for the version
        provided in the request.

        TODO: Add support for falling back to routes registered for */*
        """
        def req_version(req):
            if self.versioning_scheme == 'header':
                return req.headers.get('Accept', '*/*')
            return None

        def dispatch(*args, **kwargs):
            try:
                version = req_version(request)
                route = self._resolve_route(
                    rule,
                    version=version,
                    method=request.method.upper()
                )
            except RouteNotFound:
                print('No route for {}'.format(rule))
                abort(404)
            except VersionNotSupported:
                print('Version is not supported for {}'.format(rule))
                abort(406)
            except MethodNotSupported:
                print('Method {} is not supported for {}'.format(
                    request.method,
                    rule
                ))
                abort(405)
            except Exception as e:
                print('Got another exception: {}'.format(e))
                abort(500)

            endpoint = route['endpoint']
            view_func = route['view_func']

            print('Dispatching {} of {}'.format(version, endpoint))

            return view_func(*args, **kwargs)
        return dispatch

    def _resolve_route(self, rule, version='*/*', method='ANY'):
        """Look up a route for a rule with an optional version and method.

        This method will attempt to find a matching route record for
        the given criteria. Failing that, one of several Exceptions
        will be thrown:
          - RouteNotFound if no route is registered for the rule
          - VersionNotSupported if no handler is registered for the
            given version
          - MethodNotSupported if no handler exists for the given method
           (or one for ANY)

        TODO: Shouldn't all routes be specific about supported request
        methods?
        """
        if rule not in self.rules:
            raise RouteNotFound
        elif version not in self.rules[rule]:
            raise VersionNotSupported

        handlers = self.rules[rule][version]
        if method in handlers:
            return handlers[method]
        elif 'ANY' in handlers:
            return handlers['ANY']
        raise MethodNotSupported
