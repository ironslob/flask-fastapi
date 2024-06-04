# -*- coding: utf-8 -*-


class HttpException(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)

        self.message = message
        self.status_code = status_code


class ConflictException(HttpException):
    def __init__(self, message="Conflict"):
        super().__init__(message, 409)


class NotFoundException(HttpException):
    def __init__(self, message="Not Found"):
        super().__init__(message, 404)


class BadRequestException(HttpException):
    def __init__(self, message="Bad Request"):
        super().__init__(message, 400)


class UnauthorizedException(HttpException):
    def __init__(self, message="Unauthorized"):
        super().__init__(message, 401)


class ForbiddenException(HttpException):
    def __init__(self, message="Forbidden"):
        super().__init__(message, 403)
