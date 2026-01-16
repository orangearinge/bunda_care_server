from marshmallow import Schema, fields, validate

class IngredientSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    alt_names = fields.Str(load_default="")
    calories = fields.Int(validate=validate.Range(min=0))
    protein_g = fields.Float(validate=validate.Range(min=0))
    carbs_g = fields.Float(validate=validate.Range(min=0))
    fat_g = fields.Float(validate=validate.Range(min=0))

class IngredientQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    limit = fields.Int(load_default=10, validate=validate.Range(min=1, max=100))
    search = fields.Str(allow_none=True, load_default=None)
