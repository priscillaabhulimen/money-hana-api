
from uuid import UUID


ERROR_MESSAGES = {
    "missing": "This field is required",
    "value_error": "Invalid value provided",
    "type_error": "Invalid type provided",
    "string_too_short": "Value is too short",
    "greater_than": "Value must be greater than 0",
    "json_invalid": "Invalid JSON format",
    "extra_forbidden": "Unexpected field provided",
}

# TODO: Replace with real user management in Week 4
TEMP_USER_ID = UUID("ef73d89b-3d2d-4658-8b79-20a06c06d5cd")