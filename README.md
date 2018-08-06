# versionator

versionator provides a versionable Blueprint for Flask, allowing
explicit definition of supported route handlers for multiple versions
of an API.

## Installation

This isn't in PyPI yet, so installation is done right from GitHub:

```shellsession
pip install git+https://github.com/picwell-trevor/versionator.git@dev
```

or by cloning this repository and installing from there, e.g.:

```shellsession
git clone -b dev picwell-trevor/versionator
cd versionator
pip install -e .
```

## Usage

Usage is quite simple and just involves the use of the included
`VersionableBlueprint` and `Router` classes. Route definition is done
in much the same way as Flask itself (with the exception of a couple
extra optional decorators). As a very simple example:

```python
# v1.py

from flask import jsonify, request

from versionator.router import Router

router = Router('v1')


@router.get('/hello')
def hello():
    return jsonify({'hello': 'there'})


@router.post('/foobar')
def foobar():
    return jsonify({
        'version': 1,
        'payload': request.json
    })


# v2.py

from flask import jsonify, request

from versionator.router import Router

router = Router('v2')


@router.post('/foobar')
def foobar():
    return jsonify({
        'version': 2,
        'payload': request.json
    })


# v3.py

from flask import jsonify

from versionator.router import Router

router = Router('v3')


@router.get('/barbaz')
def barbaz():
    return jsonify({'another': 'route', 'for': 'v3'})


# app.py

from flask import Flask, jsonify

from versionator.blueprint import VersionableBlueprint

from v1 import router as v1
from v2 import router as v2

app = Flask(__name__)

blueprint = VersionableBlueprint('foo', __name__)
blueprint.register_versions({
    # v1 provides GET /hello and POST /foobar
    'v1': [v1.hello, v1.foobar],

    # v2 inherits v1's /hello and a new /foobar
    'v2': [v1.hello, v2.foobar],

    # v3 removes /hello, uses v2's /foobar, and defines a new /barbaz
    'v3': [v2.foobar, v3.barbaz]
})

app.register_blueprint(blueprint, url_prefix='/api')
```

Once the application is running, you should be able to reach these
versioned endpoints by specifying the appropriate value inside the
request's `Accept` header:

```http
# GET v1 /hello
GET http://localhost:5432/hello
Accept: v1

# Response

{"hello": "there"}

# POST v1 /foobar
POST http://localhost:5432/foobar
Accept: v1
Content-Type: application/json

{"test": "body"}

# Response

{
  "payload": {
    "test": "body"
  },
  "version": 1
}

# GET v2 /hello
GET http://localhost:5432/hello
Accept: v2

# Response

{"hello": "there"}

# POST v2 /foobar
POST http://localhost:5432/foobar
Accept: v1
Content-Type: application/json

{"test": "body"}

# Response

{
  "payload": {
    "test": "body"
  },
  "version": 2
}

# GET unsupported /hello for v3
GET http://localhost:5432/hello
Accept: v3

# Response

HTTP/1.0 406 NOT ACCEPTABLE
```

## How it Works

TODO

### `VersionableBlueprint`

#### Version Dispatch

The `VersionableBlueprint` defaults to using the `Accept` header for
selecting routes. However, by specifying `scheme='path'`, the
Blueprint will (soon) extract the version from the beginning of the
path, e.g. `/api/v1/hello`.

### `Router`
