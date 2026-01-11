from sqlalchemy import func
from datetime import datetime, timedelta
from app.extensions import db
from app.models.user import User
from app.models.menu import FoodMenu
from app.models.ingredient import FoodIngredient
from app.models.article import Article
from app.utils.http import ok, arg_int

def get_stats_handler():
    total_users = User.query.count()
    total_active_menus = FoodMenu.query.filter_by(is_active=True).count()
    total_ingredients = FoodIngredient.query.count()
    total_articles = Article.query.filter_by(is_deleted=False).count()
    
    day_ago = datetime.utcnow() - timedelta(days=1)
    active_users_today = User.query.filter(User.created_at >= day_ago).count()
    
    return ok({
        "total_users": total_users,
        "total_users_change": 0,
        "total_active_menus": total_active_menus,
        "active_menus_change": 0,
        "total_ingredients": total_ingredients,
        "ingredients_change": 0,
        "total_articles": total_articles,
        "articles_change": 0,
        "active_users_today": active_users_today,
        "active_users_change": 0
    })

def get_user_growth_handler():
    # Get user registrations for the last N days (default 30)
    days = arg_int("days", 30, min_value=7, max_value=365)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Query to group by date
    # Using DATE() function for MySQL compatibility
    results = (
        db.session.query(
            func.DATE(User.created_at).label('date'),
            func.count(User.id).label('count')
        )
        .filter(User.created_at >= start_date)
        .group_by(func.DATE(User.created_at))
        .order_by('date')
        .all()
    )
    
    # Build a map of dates to counts
    result_map = {}
    for r in results:
        # Convert date to string format
        if hasattr(r.date, 'strftime'):
            date_key = r.date.strftime('%Y-%m-%d')
        else:
            date_key = str(r.date)
        result_map[date_key] = r.count
    
    # Fill in all days in the range, including missing days with 0 count
    data = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        data.append({
            "date": date_str,
            "count": result_map.get(date_str, 0)
        })
        current += timedelta(days=1)
        
    return ok(data)
