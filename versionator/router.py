class Router(object):
    """A simple route collector.

    This class just exposes a few decorators for adding route handlers
    to a dictionary keyed by endpoint. When used with the
    VersionableBlueprint, they are merged together to create a
    version/rule map.
    """

    def __init__(self, name):
        """Initialize a new Router with a name and empty routes dictionary."""
        self.name = name
        self.routes = {}

    def route(self, rule, **options):
        """Decorate a route handler for a rule."""
        def wrapper(f):
            endpoint = options.pop('endpoint', f.__name__)
            self._register(rule, endpoint, f, **options)
            return f
        return wrapper

    def get(self, rule, **options):
        """Create a GET handler."""
        return self.route(rule, **dict(options, **{'methods': ('GET',)}))

    def post(self, rule, **options):
        """Create a POST handler."""
        return self.route(rule, **dict(options, **{'methods': ('POST',)}))

    def _register(self, rule, endpoint, view_func, **options):
        """Register a tuple of route details to the internal registry."""
        self.routes[endpoint] = (rule, endpoint, view_func, options)

    def __getattr__(self, x):
        """Enable direct access to routes as attributes.

        If the route is not defined, this raises an AttributeError.
        """
        if x in self.routes:
            return self.routes[x]
        raise AttributeError
