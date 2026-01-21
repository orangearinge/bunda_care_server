"""
Article Service Module

Handles all article-related business logic including:
- CRUD operations
- Slug generation
- Pagination
- Filtering by status
- Soft delete
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import re
from app.extensions import db
from app.models.article import Article


def generate_slug(title: str) -> str:
    """
    Generate URL-friendly slug from title.
    Converts to lowercase, replaces spaces with hyphens, removes special characters.
    """
    # Convert to lowercase
    slug = title.lower()
    
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    
    # Remove special characters (keep alphanumeric and hyphens)
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Ensure uniqueness by appending timestamp if slug already exists
    base_slug = slug
    counter = 1
    while Article.query.filter_by(slug=slug, is_deleted=False).first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


def create_article(
    title: str,
    content: str,
    excerpt: Optional[str] = None,
    cover_image: Optional[str] = None,
    status: str = "draft"
) -> Dict[str, Any]:
    """
    Create a new article.
    
    Args:
        title: Article title (required)
        content: Article content in TipTap format (required)
        excerpt: Short description (optional)
        cover_image: URL to cover image (optional)
        status: Article status - 'draft' or 'published' (default: draft)
    
    Returns:
        Dictionary with created article data
    
    Raises:
        ValueError: If validation fails
    """
    # Validation
    if not title or not title.strip():
        raise ValueError("Title is required")
    
    if not content or not content.strip():
        raise ValueError("Content is required")
    
    if status not in ["draft", "published"]:
        raise ValueError("Status must be 'draft' or 'published'")
    
    # Generate slug
    slug = generate_slug(title)
    
    # Create article
    article = Article(
        title=title.strip(),
        slug=slug,
        excerpt=excerpt.strip() if excerpt else None,
        content=content.strip(),
        cover_image=cover_image.strip() if cover_image else None,
        status=status,
        published_at=datetime.utcnow() if status == "published" else None
    )
    
    db.session.add(article)
    db.session.commit()
    
    return article.to_dict()


def update_article(
    article_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    excerpt: Optional[str] = None,
    cover_image: Optional[str] = None,
    status: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Update an existing article.
    
    Args:
        article_id: ID of the article to update
        title: New title (optional)
        content: New content (optional)
        excerpt: New excerpt (optional)
        cover_image: New cover image URL (optional)
        status: New status (optional)
    
    Returns:
        Updated article data or None if not found
    
    Raises:
        ValueError: If validation fails
    """
    article = Article.query.filter_by(id=article_id, is_deleted=False).first()
    
    if not article:
        return None
    
    # Update fields if provided
    if title is not None and title.strip():
        article.title = title.strip()
        # Regenerate slug if title changed
        article.slug = generate_slug(title)
    
    if content is not None and content.strip():
        article.content = content.strip()
    
    if excerpt is not None:
        article.excerpt = excerpt.strip() if excerpt else None
    
    if cover_image is not None:
        article.cover_image = cover_image.strip() if cover_image else None
    
    if status is not None:
        if status not in ["draft", "published"]:
            raise ValueError("Status must be 'draft' or 'published'")
        
        old_status = article.status
        article.status = status
        
        # Set published_at timestamp when first published
        if status == "published" and old_status == "draft":
            article.published_at = datetime.utcnow()
        elif status == "draft":
            article.published_at = None
    
    article.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return article.to_dict()


def delete_article(article_id: int) -> bool:
    """
    Soft delete an article.
    
    Args:
        article_id: ID of the article to delete
    
    Returns:
        True if deleted, False if not found
    """
    article = Article.query.filter_by(id=article_id, is_deleted=False).first()
    
    if not article:
        return False
    
    article.is_deleted = True
    article.deleted_at = datetime.utcnow()
    
    db.session.commit()
    
    return True


def get_article_by_id(article_id: int) -> Optional[Dict[str, Any]]:
    """
    Get article by ID (admin view - includes drafts).
    
    Args:
        article_id: Article ID
    
    Returns:
        Article data or None if not found
    """
    article = Article.query.filter_by(id=article_id, is_deleted=False).first()
    
    if not article:
        return None
    
    return article.to_dict()


def get_article_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """
    Get published article by slug (public view).
    
    Args:
        slug: Article slug
    
    Returns:
        Article data or None if not found or not published
    """
    article = Article.query.filter_by(
        slug=slug,
        status="published",
        is_deleted=False
    ).first()
    
    if not article:
        return None
    
    return article.to_dict()


def list_articles(
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Dict[str, Any]:
    """
    List articles with pagination and filtering (admin view).
    
    Args:
        page: Page number (starting from 1)
        limit: Items per page
        status: Filter by status ('draft' or 'published')
        sort_by: Field to sort by (default: created_at)
        sort_order: Sort order 'asc' or 'desc' (default: desc)
    
    Returns:
        Dictionary containing items, pagination info
    """
    # Build query
    query = Article.query.filter_by(is_deleted=False)
    
    # Filter by status if provided
    if status:
        if status not in ["draft", "published"]:
            raise ValueError("Status must be 'draft' or 'published'")
        query = query.filter_by(status=status)
    
    # Filter by search term if provided
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            db.or_(
                Article.title.ilike(search_term),
                Article.excerpt.ilike(search_term)
            )
        )
    
    # Sorting
    sort_field = getattr(Article, sort_by, Article.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())
    
    # Pagination
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return {
        "items": [article.to_dict(include_content=False) for article in pagination.items],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": pagination.total,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    }


def list_public_articles(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    sort_by: str = "published_at",
    sort_order: str = "desc"
) -> Dict[str, Any]:
    """
    List published articles (public view).
    
    Args:
        page: Page number (starting from 1)
        limit: Items per page
        sort_by: Field to sort by (default: published_at)
        sort_order: Sort order 'asc' or 'desc' (default: desc)
    
    Returns:
        Dictionary containing items, pagination info
    """
    # Only show published articles
    query = Article.query.filter_by(status="published", is_deleted=False)

    # Filter by search term if provided
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            db.or_(
                Article.title.ilike(search_term),
                Article.excerpt.ilike(search_term)
            )
        )
    
    # Sorting
    sort_field = getattr(Article, sort_by, Article.published_at)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())
    
    # Pagination
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return {
        "items": [article.to_dict(include_content=False) for article in pagination.items],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": pagination.total,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    }
