from pydantic import BaseModel

class OpenAIFunctionParameterProperty(BaseModel):
    type: str
    description: str | None = None
    enum: list[str] | None = None

class OpenAIFunctionParameter(BaseModel):
    type: str = "object"
    properties: dict[str, OpenAIFunctionParameterProperty]
    required: list[str] = []

class OpenAIFunction(BaseModel):
    name: str
    description: str = ""
    parameters: OpenAIFunctionParameter
    
class OpenAITool(BaseModel):
    type: str = "function"
    function: OpenAIFunction