# -*- coding: utf-8 -*-

from flask import Flask, make_response, request, render_template
from werkzeug.exceptions import HTTPException as WerkzeugHttpException
from inspect import signature
from pydantic import ValidationError
from pydantic.error_wrappers import ValidationError as RealValidationError
from pydantic.fields import FieldInfo
from pydantic.schema import schema
from typing import List

from .json import ORJSONEncoder, ORJSONDecoder
from .constants import HttpMethod
from .exceptions import BadRequestException, HttpException
from .schema import HttpErrorResponse, ValidationErrorResponse

import inspect
import logging
import orjson
import os.path
import re
import yaml

__version__ = "0.0.1"

logger = logging.getLogger(__name__)

base_dir =  os.path.dirname(__file__)
static_folder = os.path.join(base_dir, "static")
template_folder = os.path.join(base_dir, "templates")

def _serialize_json(data):
    data = orjson.dumps(data).decode("utf-8")

    callback = request.args.get('callback')

    if callback:
        data = '%s(%s)' % (callback, data)

    return data


serializers = {
    "application/json": _serialize_json,
    "application/javascript": _serialize_json,
    "application/x-yaml": yaml.dump,
}
deserializers = {
    "application/json": orjson.loads,
    "application/x-yaml": yaml.load,
}

supported_serializers = list(serializers.keys())
default_serializer = "application/json"

component_security = {
    "securitySchemes": {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        },
    },
}

openapi_security = [
    {
        "bearerAuth": [],
        "apiKeyAuth": [],
    },
]


class FlaskFastAPI(Flask):
    default_response_codes = {
        HttpMethod.GET: 200,
        HttpMethod.POST: 201,
        HttpMethod.PUT: 202,
        HttpMethod.PATCH: 202,
        HttpMethod.DELETE: 204,
    }

    def register_exception_reporter(self, reporter):
        self.exception_reporters.append(reporter)

    def _gen_content(self, ref, **extras):
        content = {
            "description": "",
            "content": {
                mime_type: {
                    "schema": {
                        "$ref": "#/components/schemas/" + ref,
                    },
                }
                for mime_type in serializers
            }
        }

        content.update(extras)

        return content

    def __init__(
            self,
            __name__,
            api_title,
            api_version,
            openapi_version='3.0.2',
        ):

        super().__init__(
            __name__,
            static_url_path="/static",
            static_folder=static_folder,
            template_folder=template_folder,
        )

        self.api_title = api_title
        self.api_version = api_version
        self.openapi_version = openapi_version
        self.schema_metadata = {}
        self.exception_reporters = []

        self.add_url_rule(
            "/openapi.yaml",
            "openapi_yaml",
            lambda: yaml.dump(self.openapi()),
            methods=[HttpMethod.GET],
        )

        self.add_url_rule(
            "/openapi.json",
            "openapi_json",
            lambda: self.openapi(),
            methods=[HttpMethod.GET],
        )

        self.add_url_rule(
            "/docs/",
            "swaggerui",
            lambda: self.swaggerui(),
            methods=[HttpMethod.GET],
        )

        self.add_url_rule(
            "/redoc/",
            "redoc",
            lambda: self.redoc(),
            methods=[HttpMethod.GET],
        )

        def error_handler(e):
            model = HttpErrorResponse(
                code=e.code,
                name=e.name,
                description=e.description,
            )

            return self.serialize_response(model, e.code)

        self._register_error_handler(None, WerkzeugHttpException, error_handler)

    def redoc(self):
        return render_template("redoc.html")

    def swaggerui(self):
        return render_template("swaggerui.html")

    def serialize_response(self, model, status_code):
        data = ""
        best_serializer = None

        if model is not None:
            data = model.dict()

            best_serializer = request.accept_mimetypes.best_match(list(serializers.keys())) or default_serializer

            data = serializers[best_serializer](data)

        response = make_response(data, status_code)

        if best_serializer:
            response.headers["Content-Type"] = best_serializer

        return response

    def openapi(self):
        paths = {}

        info = {
            "title": self.api_title,
            "version": self.api_version,
        }

        schemas = [
            ValidationErrorResponse,
            HttpErrorResponse,
        ]

        # these responses will be included with every request response in the
        # openapi
        default_responses = {
            "400": self._gen_content(
                "ValidationErrorResponse", description="Bad request"
            ),
            "401": {
                "description": "Unauthorized",
            },
            "403": {
                "description": "Forbidden",
            },
            "500": {
                "description": "Internal server error. Assume request failed. Please try again",
            },
        }

        default_parameters = [
            # {
            #     "in": "header",
            #     "name": "Accept-Language",
            #     "description": "Request content in the specific language.",
            #     "schema": {
            #         "type": "string",
            #         "default": default_language,
            #         "enum": supported_language_codes,
            #     },
            # },
            {
                "in": "header",
                "name": "Accept",
                "description": "Request use of a particular data serialization.",
                "schema": {
                    "type": "string",
                    "default": default_serializer,
                    "enum": supported_serializers,
                },
            },
        ]

        content_type_parameter = {
            "in": "header",
            "name": "Content-Type",
            "description": "The data format that the request body is serialized in.",
            "required": True,
            "schema": {"type": "string", "enum": list(serializers.keys())},
        }

        method_parameters = {
            HttpMethod.PATCH: [
                content_type_parameter,
            ],
            HttpMethod.GET: [],
            HttpMethod.DELETE: [],
            HttpMethod.PUT: [
                content_type_parameter,
            ],
            HttpMethod.POST: [
                content_type_parameter,
            ],
        }

        for rule in self.url_map.iter_rules():
            if rule.endpoint in self.schema_metadata:
                rule_normalised = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule)

                if rule_normalised not in paths:
                    paths[rule_normalised] = {}

                metadata = self.schema_metadata[rule.endpoint]

                sig = metadata["sig"]

                for method in rule.methods:
                    if method in method_parameters:
                        request_body = None

                        if "body" in metadata:
                            body = metadata["body"]

                            schemas.append(body)

                            request_body = self._gen_content(
                                body.__name__, required=True
                            )
                            # request_body = {
                            #     'required': True,
                            #     'content': {
                            #         'application/json': {
                            #             'schema': {
                            #                 '$ref': '#/definitions/' + body.__name__,
                            #             },
                            #         },
                            #     },
                            # }

                        parameters = default_parameters.copy()
                        parameters.extend(method_parameters.get(method))

                        for field, parameter in sig.parameters.items():
                            if field == 'body':
                                # body is a keyword used for json body
                                continue

                            param = {
                                "name": field,
                                # 'description': ...
                            }

                            if field in rule.arguments:
                                param["in"] = "path"
                                param["required"] = True

                            else:
                                param["in"] = "query"

                            if parameter.annotation:
                                type_map = {
                                    "str": "string",
                                    "UUID": "string",
                                    "int": "integer",
                                }

                                assert parameter.annotation.__name__ != '_empty', 'declare parameter %s with a type notation in function declaration %s %s' % (field, method, rule_normalised)

                                param["schema"] = {
                                    "type": type_map.get(parameter.annotation.__name__, parameter.annotation.__name__),
                                }

                            if parameter.default:
                                if isinstance(parameter.default, FieldInfo):
                                    param["description"] = parameter.default.description

                                    if parameter.default.default != Ellipsis:
                                        param["default"] = parameter.default.default

                                elif parameter.default not in (inspect._empty, Ellipsis):
                                    param["default"] = parameter.default

                            parameters.append(param)

                        response = None

                        if sig.return_annotation is not inspect._empty:
                            schemas.append(sig.return_annotation)

                            response = self._gen_content(
                                sig.return_annotation.__name__
                            )
                            # response = {
                            #     'description': '',
                            #     'content': {
                            #         'application/json': {
                            #             'schema': {
                            #                 '$ref': '#/definitions/' + sig.return_annotation.__name__,
                            #             },
                            #         },
                            #     },
                            # }

                        else:
                            response = {
                                "description": "No content",
                            }

                        responses = default_responses.copy()
                        response_code = metadata["response_code"] or FlaskFastAPI.default_response_codes[method]
                        responses[str(response_code)] = response

                        method_schema = {
                            "summary": metadata["summary"],
                            "tags": metadata["tags"],
                            "operationId": rule.endpoint,
                            "responses": responses,
                        }

                        if metadata["requires_auth"]:
                            method_schema["security"] = openapi_security

                        if metadata["doc"]:
                            method_schema["description"] = metadata["doc"]

                        if parameters:
                            method_schema["parameters"] = parameters

                        if request_body:
                            method_schema["requestBody"] = request_body

                        paths[rule_normalised][method.lower()] = method_schema

        server = request.url[0:request.url.index("/", 8)]

        # pydantic puts these in a sub-key "definitions", so lets just pull that out
        schemas = schema(schemas, ref_prefix='#/components/schemas/')

        openapi = {
            "openapi": self.openapi_version,
            "servers": [
                {
                    "url": server,
                },
            ],
            "paths": paths,
            "info": info,
            "components": {
                **component_security,
                "schemas": schemas["definitions"],
            },
        }

        return openapi

    def route(
        self,
        rule: str,
        methods: List[HttpMethod],
        tags: List[str] = [],
        summary: str = None,
        response_code: int = None,
        requires_auth: bool = True,
        private: bool = False,
        **kwargs,
    ):
        def decorator(func):
            func_sig = signature(func, follow_wrapped=True)
            body_class = None

            if "body" in func_sig.parameters:
                body_class = func_sig.parameters["body"].annotation

            def _decorated(*args, **kwargs):
                status_code = None
                response = None
                process = False

                try:
                    # TODO check api keys
                    if body_class is not None:
                        if request.content_type not in deserializers:
                            raise BadRequestException(
                                "Unknown content type %s" % (request.content_type)
                            )

                        data = deserializers[request.content_type](request.data)

                        # for now we simply ensure that everything that's
                        # submitted is a dict, because we don't handle
                        # anything else
                        if not isinstance(data, dict):
                            raise BadRequestException()

                        # validation failure will be caught below
                        kwargs["body"] = body_class(**data)

                    request_args = request.args.to_dict(flat=False)

                    for key, param in func_sig.parameters.items():
                        if key not in kwargs:
                            if key in request_args:
                                # TODO handle coercion
                                def default_handler(value):
                                    return param.annotation(value[0] if isinstance(value, list) else value)

                                handlers = {
                                    List[str]: lambda value: value if isinstance(value, list) else [value],
                                }

                                handler = handlers.get(param.annotation, default_handler)

                                try:
                                    kwargs[key] = handler(request_args[key])

                                except ValueError:
                                    # FIXME this should return a more useful error message
                                    raise BadRequestException('Invalid value for "%s"' % key)

                            elif param.default:
                                # FIXME this should really consider Ellipsis
                                # fields that aren't provided as a bad request
                                if isinstance(param.default, FieldInfo):
                                    if param.default.default != Ellipsis:
                                        kwargs[key] = param.default.default

                                elif param.default not in (inspect._empty, Ellipsis):
                                    kwargs[key] = param.default

                    process = True

                except orjson.JSONDecodeError:
                    response = ValidationErrorResponse(
                        code=400,
                        name="Bad request.",
                        # errors = e.errors(),
                    )

                    status_code = 400

                except ValidationError as e:
                    # TODO map these errors into something cleaner
                    response = ValidationErrorResponse(
                        code=400,
                        name="Bad request. See errors for details.",
                        errors=e.errors(),
                    )

                    status_code = 400

                except BadRequestException:
                    response = ValidationErrorResponse(
                        code=400,
                        name="Bad request.",
                    )

                    status_code = 400

                except HttpException as e:
                    response = HttpErrorResponse(
                        code=e.status_code,
                        name=e.message,
                    )

                    status_code = e.status_code

                if process:
                    try:
                        response = func(*args, **kwargs)
                        status_code = response_code or FlaskFastAPI.default_response_codes[request.method]

                    except RealValidationError as e:
                        # TODO map these errors into something cleaner
                        response = ValidationErrorResponse(
                            code=400,
                            name="Bad request. See errors for details.",
                            errors=e.errors(),
                        )

                        status_code = 400

                    except HttpException as e:
                        response = HttpErrorResponse(
                            code=e.status_code,
                            name=e.message,
                        )

                        status_code = e.status_code

                    except Exception as e:
                        # report error, but don't show the user
                        # TODO some sort of exception handler
                        # iterate over exception handlers and deliver to each
                        for reporter in self.exception_reporters:
                            reporter(self, e)

                        response = HttpErrorResponse(
                            code=500,
                            name="Internal server error. Assume request failed. Please try again",
                        )

                        status_code = 500

                return self.serialize_response(response, status_code)

            endpoint = func.__name__
            assert endpoint not in self.schema_metadata

            if not private:
                self.schema_metadata[endpoint] = {
                    "tags": tags,
                    "summary": summary,
                    "sig": func_sig,  # signature(func, follow_wrapped = True),
                    "doc": func.__doc__,
                    "response_code": response_code,
                    "requires_auth": requires_auth,
                }

                if body_class is not None:
                    self.schema_metadata[endpoint]["body"] = body_class

            self.add_url_rule(
                rule,
                endpoint,
                _decorated,
                methods=methods,
                **kwargs,
            )

            return _decorated

        return decorator

    def post(self, *args, **kwargs):
        return self.route(
            *args,
            methods=[HttpMethod.POST],
            **kwargs,
        )

    def patch(self, *args, **kwargs):
        return self.route(
            *args,
            methods=[HttpMethod.PATCH],
            **kwargs,
        )

    def put(self, *args, **kwargs):
        return self.route(
            *args,
            methods=[HttpMethod.PUT],
            **kwargs,
        )

    def delete(self, *args, **kwargs):
        return self.route(
            *args,
            methods=[HttpMethod.DELETE],
            **kwargs,
        )

    def get(self, *args, **kwargs):
        return self.route(
            *args,
            methods=[HttpMethod.GET],
            **kwargs,
        )


FlaskFastAPI.json_encoder = ORJSONEncoder
FlaskFastAPI.json_decoder = ORJSONDecoder
