from pydantic import BaseModel
from typing import Any, Optional

class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[Any] = None