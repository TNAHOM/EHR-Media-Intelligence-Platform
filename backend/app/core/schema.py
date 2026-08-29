from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """Base model enforcing strict Pydantic v2 validation rules across the app."""

    model_config = ConfigDict(
        from_attributes=True,
        # Forbids unknown extra JSON fields sent by clients
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        # Populate models using field names or aliases
        populate_by_name=True,
    )
