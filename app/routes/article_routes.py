"""
Article Routes Module

Defines URL mappings for article endpoints:
- Admin routes (protected with JWT)
- Public routes (for mobile app)
"""

from flask import Blueprint
from app.utils.auth import require_admin
from app.controllers.article_controller import (
    create_article_handler,
    update_article_handler,
    delete_article_handler,
    get_article_handler,
    list_articles_handler,
    list_public_articles_handler,
    get_public_article_handler
)

article_bp = Blueprint("articles", __name__, url_prefix="/api")


# ============================================================================
# Admin Routes (Protected with JWT)
# ============================================================================

@article_bp.post("/articles")
@require_admin
def create_article():
    """Create a new article (Admin only)"""
    return create_article_handler()


@article_bp.put("/articles/<int:id>")
@require_admin
def update_article(id):
    """Update an article (Admin only)"""
    return update_article_handler(id)


@article_bp.delete("/articles/<int:id>")
@require_admin
def delete_article(id):
    """Delete an article (Admin only)"""
    return delete_article_handler(id)


@article_bp.get("/articles")
@require_admin
def list_articles():
    """List all articles with filtering (Admin only)"""
    return list_articles_handler()


@article_bp.get("/articles/<int:id>")
@require_admin
def get_article(id):
    """Get article detail by ID (Admin only)"""
    return get_article_handler(id)


# ============================================================================
# Public Routes (For Mobile App)
# ============================================================================

@article_bp.get("/public/articles")
def list_public_articles():
    """List published articles (Public)"""
    return list_public_articles_handler()


@article_bp.get("/public/articles/<slug>")
def get_public_article(slug):
    """Get published article by slug (Public)"""
    return get_public_article_handler(slug)
