# -*- coding: utf-8 -*-

import orjson
import logging

logger = logging.getLogger(__name__)


class ORJSONDecoder:
    def __init__(self, **kwargs):
        # eventually take into consideration when deserializing
        self.options = kwargs
        logger.debug(kwargs)

    def decode(self, obj):
        return orjson.loads(obj)


class ORJSONEncoder:
    def __init__(self, **kwargs):
        # eventually take into consideration when serializing
        # DEBUG:__main__:{'skipkeys': False, 'ensure_ascii': True, 'check_circular': True, 'allow_nan': True, 'indent': 2, 'separators': (', ', ': '), 'default': None, 'sort_keys': True}
        self.options = kwargs

    def encode(self, obj):
        # decode back to str, as orjson returns bytes
        params = 0

        if self.options.get("indent", None):
            params |= orjson.OPT_INDENT_2

        # if self.options.get('sortkeys'):
        #     params |= orjson.OPT_SORT_KEYS

        encoded = orjson.dumps(obj)

        if self.options.get("ensure_ascii", False):
            encoded = encoded.decode("utf-8")

        return encoded
