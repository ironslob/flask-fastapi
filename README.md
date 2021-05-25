# Flast-FastAPI

Extended version of Flask to offer FastAPI inspired functionality. I wanted a
way to offer similar functionality but run under AWS Lambda (and othre
non-async environments).

Flask-FastAPI uses python type hints extensively to understand request and
response data, and not including them will cause problems. Some examples below.

Pydantic is used extensively.

## This is unfinished software

This software was extracted from another project that I built and retired. This
portion of the software was of some use and so I thought I would rip it out and
give it to the world for free. It is:

- messy
- buggy
- incomplete
- poorly documented
- imperfect
- amazing
- working for me
- a complete strange to automated testing

As I find time to improve the quality of this code, the documentation, and the
test coverage I will aim to improve things a little. In the meantime please
consider adding in your own fixes, tests, etc.

## Decorators for common API methods

For each of the main HTTP requests there is an appropriate decorator. These
decorators share some common parameters:

### Route parameters

- tags - array used in OpenAPI to categorise endpoint
- summary - string used in OpenAPI to describe endpoint
- response_code - used to override default response codes for each HTTP method, 
- requires_auth - boolean, whether this endpoint requires authentication, defaults to true
- private - boolean, if set to true will not include endpoint in public documentation, defaults to false

### Function

- Python function __doc__ - used as description in OpenAPI
- A parameter called "body" will be considered as the POST request, and type hints determine how it's parsed
- Parameter type hints will be used to coerce query parameters
- A parameter which defaults to a Pydantic Field type will take further validation and details (such as description) from the information provided (more below)
- Function response type hint will be used to determine response schema

### Default response codes

Response code can be specified using the `response_code` route parameter, or the default will be used.

- GET returns 200
- POST returns 201
- PUT returns 202
- PATCH returns 202
- DELETE returns 204, without content

## Examples

### GET

```
@api.get('/path/to/<id>', summary="Endpoint summary", tags=["tags","about","endpoint"])
def get_resource(
        id: int = Field(..., description="Unique identifier")
    ) -> ResponseSchema:

    ''' This documentation will be included to describe the endpoint.
    '''
    # this would return a Pydantic ResponseSchema in a real world example
    return ResponseSchema(...)
```

### POST, PUT, and PATCH

```
@api.post('/path/to/entity', summary="...")
def post_resource(body: RequestSchema) -> ResponseSchema:
    ''' Request schema is automatically picked up from the name of the parameter.
    '''
    # this would return a Pydantic ResponseSchema in a real world example
    return ResponseSchema(...)
```

### DELETE

```
@api.delete('/path/to/<id>', summary="Endpoint summary", tags=["tags","about","endpoint"])
def get_resource(
        id: int = Field(..., description="Unique identifier")
    ):

    ''' No return type hint is needed here, as delete does not return content by default
    '''
    pass
```

## Exceptions

The exceptions defined in flask_fastapi.exceptions handle the most common cases
encountered, but extension of exceptions.HttpException is trivial and can be
used to manage different non-OK responses.

## Automatic OpenAPI documentation

An openapi.json file will be generated from the routes that are created and can
be downloaded by visiting the /openapi.json endpoint. There will also be an
/openapi.yaml file available for anybody who wants it.

## Documentation serving

Through automated generation of the OpenAPI documentation you also have serving
of documentation through either Redoc of SwaggerUI, both of which have
templates bundled with this package.

### Redoc

Can be seen by navigating to $base_url/redoc/, e.g. http://localhost:5000/redoc/.

Github repo for redoc- https://github.com/Redocly/redoc

### SwaggerUI

Can be seen by navigating to $base_url/docs/, e.g. http://localhost:5000/docs/.

Website for SwaggerUI - https://swagger.io/tools/swagger-ui/

# To document

- Security
