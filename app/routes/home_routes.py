from flask import Blueprint
from app.controllers.home_controller import home_index

home_bp = Blueprint("home", __name__, url_prefix="/api")

@home_bp.route("/")
def home():
    return home_index()
