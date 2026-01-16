from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from app.utils.enums import UserRole, LactationPhase

class UserPreferenceSchema(Schema):
    name = fields.Str(allow_none=True)
    role = fields.Str(validate=validate.OneOf([e.value for e in UserRole]))
    height_cm = fields.Int(validate=validate.Range(min=50, max=300))
    weight_kg = fields.Float(validate=validate.Range(min=1, max=500))
    age_year = fields.Int(validate=validate.Range(min=0, max=120))
    age_month = fields.Int(validate=validate.Range(min=0, max=11))
    lila_cm = fields.Float(validate=validate.Range(min=0, max=100))
    hpht = fields.Date(allow_none=True)
    lactation_phase = fields.Str(validate=validate.OneOf([e.value for e in LactationPhase]), allow_none=True)
    food_prohibitions = fields.List(fields.Str(), load_default=[])
    allergens = fields.List(fields.Str(), load_default=[])

    @validates_schema
    def validate_role_requirements(self, data, **kwargs):
        role = data.get("role")
        if not role:
            return

        # Define requirements for each role
        requirements = {
            UserRole.IBU_HAMIL.value: ["weight_kg", "height_cm", "age_year", "hpht", "lila_cm"],
            UserRole.IBU_MENYUSUI.value: ["weight_kg", "height_cm", "age_year", "lactation_phase"],
            UserRole.ANAK_BATITA.value: ["weight_kg", "height_cm", "age_year", "age_month"],
            UserRole.ANAK_BALITA.value: ["weight_kg", "height_cm", "age_year"],
        }

        if role in requirements:
            missing = [field for field in requirements[role] if data.get(field) is None]
            if missing:
                raise ValidationError(
                    {field: ["Field is required for this role"] for field in missing}
                )

class UserProfileUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1))
    avatar = fields.Str(allow_none=True)

class AvatarUpdateSchema(Schema):
    avatar = fields.Str(required=False)
    avatar_url = fields.Str(required=False)

    @validates_schema
    def validate_avatar_present(self, data, **kwargs):
        if not data.get("avatar") and not data.get("avatar_url"):
            raise ValidationError("Avatar or avatar_url is required", field_name="avatar")
