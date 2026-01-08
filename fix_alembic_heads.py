#!/usr/bin/env python3
"""
Script to fix alembic multiple heads situation
"""
import sys
import os
sys.path.append('.')

from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

def fix_multiple_heads():
    """Fix multiple heads by creating merge migration"""
    alembic_cfg = Config('alembic.ini')
    
    # Get current heads
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    
    print(f"Current heads: {heads}")
    
    if len(heads) <= 1:
        print("No multiple heads detected.")
        return
    
    # Create merge migration
    print("Creating merge migration...")
    command.merge(alembic_cfg, heads)
    
    print("Merge migration created. Please run:")
    print("flask db upgrade")

if __name__ == "__main__":
    try:
        fix_multiple_heads()
    except Exception as e:
        print(f"Error: {e}")
        print("\nAlternative solution:")
        print("1. Run: flask db heads")
        print("2. Choose specific head: flask db upgrade <head_id>")
        print("3. Or run: flask db upgrade heads")