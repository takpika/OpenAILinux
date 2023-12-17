from pydantic import BaseModel

class RunResult(BaseModel):
    returncode: int
    output: str