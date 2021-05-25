# -*- coding: utf-8 -*-

from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class HttpErrorResponse(BaseModel):
    code: int
    name: str
    # description: str


class ValidationError(BaseModel):
    loc: List[str]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    code: int
    name: str
    errors: Optional[List[ValidationError]]
