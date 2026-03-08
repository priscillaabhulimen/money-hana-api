# app/utils/openapi.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="MoneyHana API",
        version="1.0.0",
        routes=app.routes,
    )

    for path in openapi_schema["paths"].values():
        for method in path.values():
            if "422" in method.get("responses", {}):
                method["responses"]["422"] = {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                }

    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "message": {"type": "string", "example": "Invalid category"}
        },
        "required": ["status", "message"]
    }

    for schema_name in ["HTTPValidationError", "ValidationError"]:
        openapi_schema["components"]["schemas"].pop(schema_name, None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema