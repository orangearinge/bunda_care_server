from marshmallow import Schema, fields, validate
from app.utils.enums import MealType, TargetRole

class IngredientSchema(Schema):
    ingredient_id = fields.Int(allow_none=True)
    quantity_g = fields.Float(allow_none=True, validate=validate.Range(min=0))  # Now optional
    display_text = fields.Str(allow_none=True)  # Standardized name

class CreateMenuSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    meal_type = fields.Str(required=True, validate=validate.OneOf([e.value for e in MealType]))
    tags = fields.Str(load_default="")
    image_url = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    cooking_instructions = fields.Str(allow_none=True)
    cooking_time_minutes = fields.Int(allow_none=True)
    target_role = fields.Str(load_default=TargetRole.IBU.value, validate=validate.OneOf([e.value for e in TargetRole]))
    is_active = fields.Bool(load_default=True)
    ingredients = fields.List(fields.Nested(IngredientSchema), load_default=[])
    
    # Manual Nutrition Override fields
    nutrition_is_manual = fields.Bool(load_default=False)
    serving_unit = fields.Str(allow_none=True)
    manual_calories = fields.Int(allow_none=True, validate=validate.Range(min=0))
    manual_protein_g = fields.Float(allow_none=True, validate=validate.Range(min=0))
    manual_carbs_g = fields.Float(allow_none=True, validate=validate.Range(min=0))
    manual_fat_g = fields.Float(allow_none=True, validate=validate.Range(min=0))

class UpdateMenuSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1))
    meal_type = fields.Str(validate=validate.OneOf([e.value for e in MealType]))
    tags = fields.Str()
    image_url = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    cooking_instructions = fields.Str(allow_none=True)
    cooking_time_minutes = fields.Int(allow_none=True)
    target_role = fields.Str(validate=validate.OneOf([e.value for e in TargetRole]))
    is_active = fields.Bool()
    ingredients = fields.List(fields.Nested(IngredientSchema))
    
    # Manual Nutrition Override fields
    nutrition_is_manual = fields.Bool()
    serving_unit = fields.Str(allow_none=True)
    manual_calories = fields.Int(allow_none=True, validate=validate.Range(min=0))
    manual_protein_g = fields.Float(allow_none=True, validate=validate.Range(min=0))
    manual_carbs_g = fields.Float(allow_none=True, validate=validate.Range(min=0))
    manual_fat_g = fields.Float(allow_none=True, validate=validate.Range(min=0))

class CreateMealLogSchema(Schema):
    menu_id = fields.Int(required=True)
    servings = fields.Float(load_default=1.0, validate=validate.Range(min=0.1))
    is_consumed = fields.Bool(load_default=False)
    logged_at = fields.DateTime(allow_none=True)

class ListMenuQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    limit = fields.Int(load_default=10, validate=validate.Range(min=1, max=100))
    search = fields.Str(allow_none=True, load_default=None)
    meal_type = fields.Str(allow_none=True, load_default=None, validate=validate.OneOf([e.value for e in MealType] + ["", None]))
    is_active = fields.Bool(allow_none=True, load_default=None)
    target_role = fields.Str(allow_none=True, load_default=None, validate=validate.OneOf([e.value for e in TargetRole] + ["", None]))

