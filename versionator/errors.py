class VersioningError(Exception):
    """A base exception for versioning errors."""
    pass


class RouteNotFound(VersioningError):
    """Raised when a route is not registered for any version."""
    pass


class VersionNotSupported(VersioningError):
    """Raised when a route is not supported for the version in the
    request.
    """
    pass


class InvalidVersioningScheme(VersioningError):
    """Raised when an unsupported versioning scheme (path or header) is
    provided during initialization.
    """
    pass


class MethodNotSupported(Exception):
    """Raised when no handler has been registered for a request method."""
    pass
