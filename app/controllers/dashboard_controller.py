from sqlalchemy import func
from datetime import datetime, timedelta
from app.extensions import db
from app.models.user import User
from app.models.menu import FoodMenu
from app.utils.http import ok

def get_stats_handler():
    total_users = User.query.count()
    total_active_menus = FoodMenu.query.filter_by(is_active=True).count()
    
    return ok({
        "total_users": total_users,
        "total_active_menus": total_active_menus
    })

def get_user_growth_handler():
    # Get user registrations for the last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Query to group by date
    # Note: This assumes SQLite or PostgreSQL date functions. For MySQL, use func.date()
    # Since requirements.txt has PyMySQL, I assume MySQL.
    
    results = (
        db.session.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        )
        .filter(User.created_at >= start_date)
        .group_by(func.date(User.created_at))
        .order_by('date')
        .all()
    )
    
    data = []
    # Fill in missing days
    result_map = {str(r.date): r.count for r in results}
    
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        data.append({
            "date": date_str,
            "count": result_map.get(date_str, 0)
        })
        current += timedelta(days=1)
        
    return ok(data)
