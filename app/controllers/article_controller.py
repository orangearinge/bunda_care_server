"""
Article Controller Module

Handles article-related HTTP requests including:
- Admin endpoints (protected with JWT)
- Public endpoints for mobile app
- Validation and error handling
"""

from flask import request
from app.extensions import db
from app.utils.http import ok, error, json_body, arg_int
from app.services.article_service import (
    create_article,
    update_article,
    delete_article,
    get_article_by_id,
    get_article_by_slug,
    list_articles,
    list_public_articles
)


# ============================================================================
# Admin Handlers (Protected with JWT)
# ============================================================================

def create_article_handler():
    """
    Create a new article.
    
    Body Parameters:
        - title (required): Article title
        - content (required): Article content (TipTap JSON/HTML)
        - excerpt (optional): Short description
        - cover_image (optional): URL to cover image
        - status (optional): 'draft' or 'published' (default: draft)
    """
    data = json_body()
    
    # Validate required fields
    title = (data.get("title") or "").strip()
    content = data.get("content", "")
    
    if not title:
        return error("VALIDATION_ERROR", "Title is required", 400)
    
    if not content:
        return error("VALIDATION_ERROR", "Content is required", 400)
    
    try:
        result = create_article(
            title=title,
            content=content,
            excerpt=data.get("excerpt"),
            cover_image=data.get("cover_image"),
            status=data.get("status", "draft")
        )
        return ok(result, 201)
    except ValueError as e:
        return error("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def update_article_handler(article_id: int):
    """
    Update an existing article.
    
    Body Parameters (all optional):
        - title: Article title
        - content: Article content (TipTap JSON/HTML)
        - excerpt: Short description
        - cover_image: URL to cover image
        - status: 'draft' or 'published'
    """
    data = json_body()
    
    try:
        result = update_article(
            article_id=article_id,
            title=data.get("title"),
            content=data.get("content"),
            excerpt=data.get("excerpt"),
            cover_image=data.get("cover_image"),
            status=data.get("status")
        )
        
        if not result:
            return error("NOT_FOUND", "Article not found", 404)
        
        return ok(result)
    except ValueError as e:
        return error("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def delete_article_handler(article_id: int):
    """
    Soft delete an article.
    """
    try:
        success = delete_article(article_id)
        
        if not success:
            return error("NOT_FOUND", "Article not found", 404)
        
        return ok({"message": "Article deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def get_article_handler(article_id: int):
    """
    Get article detail by ID (admin view).
    Includes drafts and unpublished articles.
    """
    try:
        article = get_article_by_id(article_id)
        
        if not article:
            return error("NOT_FOUND", "Article not found", 404)
        
        return ok(article)
    except Exception as e:
        return error("UNKNOWN_ERROR", str(e), 500)


def list_articles_handler():
    """
    List articles with pagination and filtering (admin view).
    
    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10, max: 100)
        - status: Filter by status ('draft' or 'published')
        - sort_by: Field to sort by (default: created_at)
        - sort_order: 'asc' or 'desc' (default: desc)
    """
    page = arg_int("page", 1, min_value=1)
    limit = arg_int("limit", 10, min_value=1, max_value=100)
    status = (request.args.get("status") or "").strip() or None
    sort_by = (request.args.get("sort_by") or "created_at").strip()
    sort_order = (request.args.get("sort_order") or "desc").strip()
    
    try:
        result = list_articles(
            page=page,
            limit=limit,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return ok(result)
    except ValueError as e:
        return error("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        return error("UNKNOWN_ERROR", str(e), 500)


# ============================================================================
# Public Handlers (For Mobile App)
# ============================================================================

def list_public_articles_handler():
    """
    List published articles (public view).
    Only shows published articles.
    
    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10, max: 50)
        - sort_by: Field to sort by (default: published_at)
        - sort_order: 'asc' or 'desc' (default: desc)
    """
    page = arg_int("page", 1, min_value=1)
    limit = arg_int("limit", 10, min_value=1, max_value=50)
    sort_by = (request.args.get("sort_by") or "published_at").strip()
    sort_order = (request.args.get("sort_order") or "desc").strip()
    
    try:
        result = list_public_articles(
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return ok(result)
    except Exception as e:
        return error("UNKNOWN_ERROR", str(e), 500)


def get_public_article_handler(slug: str):
    """
    Get published article by slug (public view).
    Only returns published articles.
    """
    try:
        article = get_article_by_slug(slug)
        
        if not article:
            return error("NOT_FOUND", "Article not found", 404)
        
        return ok(article)
    except Exception as e:
        return error("UNKNOWN_ERROR", str(e), 500)
