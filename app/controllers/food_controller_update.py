def update_menu_handler(menu_id: int):
    """
    Update an existing menu.
    
    Body Parameters (all optional):
        - name: Menu name
        - meal_type: BREAKFAST/LUNCH/DINNER
        - tags: Comma-separated tags
        - image_url: URL to image
        - description: Menu description
        - cooking_instructions: How to cook
        - cooking_time_minutes: Time in minutes
        - is_active: Whether menu is active
        - ingredients: List of {ingredient_id, quantity_g} (replaces all)
    """
    data = json_body()
    
    # Debug logging
    print(f"[UPDATE MENU] Menu ID: {menu_id}")
    print(f"[UPDATE MENU] Received data: {data}")
    
    try:
        success = update_menu(
            menu_id=menu_id,
            name=data.get("name"),
            meal_type=data.get("meal_type"),
            tags=data.get("tags"),
            image_url=data.get("image_url"),
            description=data.get("description"),
            cooking_instructions=data.get("cooking_instructions"),
            cooking_time_minutes=data.get("cooking_time_minutes"),
            is_active=data.get("is_active"),
            ingredients=data.get("ingredients")
        )
        
        if not success:
            return error("NOT_FOUND", "Menu not found", 404)
        
        print(f"[UPDATE MENU] Successfully updated menu ID: {menu_id}")
        return ok({"id": menu_id, "message": "Menu updated successfully"})
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)