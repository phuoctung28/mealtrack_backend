"""Initial database schema

Revision ID: 000
Revises: 
Create Date: 2024-08-28 22:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum


# revision identifiers, used by Alembic.
revision = '000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial database schema"""
    
    # Create users table (basic version without enhancements)
    op.create_table('users',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('email', String(255), nullable=False, unique=True),
        sa.Column('username', String(100), nullable=False, unique=True),
        sa.Column('first_name', String(100), nullable=True),
        sa.Column('last_name', String(100), nullable=True),
        sa.Column('password_hash', String(255), nullable=False),
        sa.Column('is_active', Boolean, nullable=False, server_default='1')
    )
    
    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        sa.Column('age', Integer, nullable=True),
        sa.Column('gender', sa.Enum('MALE', 'FEMALE', 'OTHER', name='genderenum'), nullable=True),
        sa.Column('height', Float, nullable=True),
        sa.Column('weight', Float, nullable=True),
        sa.Column('body_fat_percentage', Float, nullable=True),
        sa.Column('activity_level', sa.Enum('SEDENTARY', 'LIGHTLY_ACTIVE', 'MODERATELY_ACTIVE', 'VERY_ACTIVE', 'EXTREMELY_ACTIVE', name='activitylevelenum'), nullable=True),
        sa.Column('fitness_goal', sa.Enum('WEIGHT_LOSS', 'WEIGHT_GAIN', 'MUSCLE_GAIN', 'MAINTENANCE', 'BODY_RECOMPOSITION', name='fitnessgoalenum'), nullable=True),
        sa.Column('dietary_preferences', JSON, nullable=True),
        sa.Column('tdee', Float, nullable=True),
        sa.Column('target_calories', Integer, nullable=True),
        sa.Column('target_protein', Float, nullable=True),
        sa.Column('target_carbs', Float, nullable=True),
        sa.Column('target_fat', Float, nullable=True),
        sa.Column('is_current', Boolean, nullable=False, server_default='1')
    )
    
    # Create meal_plans table
    op.create_table('meal_plans',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        sa.Column('name', String(255), nullable=False),
        sa.Column('description', Text, nullable=True),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('is_active', Boolean, nullable=False, server_default='1')
    )
    
    # Create meal_plan_days table
    op.create_table('meal_plan_days',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('plan_id', Integer, ForeignKey('meal_plans.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('total_calories', Integer, nullable=True),
        sa.Column('total_protein', Float, nullable=True),
        sa.Column('total_carbs', Float, nullable=True),
        sa.Column('total_fat', Float, nullable=True)
    )
    
    # Create planned_meals table (without seasonings initially)
    op.create_table('planned_meals',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('day_id', Integer, ForeignKey('meal_plan_days.id'), nullable=False),
        sa.Column('meal_type', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', 'SNACK', name='mealtypeenum'), nullable=False),
        sa.Column('name', String(255), nullable=False),
        sa.Column('description', Text, nullable=True),
        sa.Column('prep_time', Integer, nullable=True),
        sa.Column('cook_time', Integer, nullable=True),
        sa.Column('calories', Integer, nullable=True),
        sa.Column('protein', Float, nullable=True),
        sa.Column('carbs', Float, nullable=True),
        sa.Column('fat', Float, nullable=True),
        sa.Column('ingredients', JSON, nullable=True),
        sa.Column('instructions', JSON, nullable=True),
        sa.Column('is_vegetarian', Boolean, nullable=False, server_default='0'),
        sa.Column('is_vegan', Boolean, nullable=False, server_default='0'),
        sa.Column('is_gluten_free', Boolean, nullable=False, server_default='0'),
        sa.Column('cuisine_type', String(100), nullable=True)
    )
    
    # Create meals table
    op.create_table('meals',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('meal_type', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', 'SNACK', name='mealtypeenum'), nullable=False),
        sa.Column('name', String(255), nullable=True),
        sa.Column('description', Text, nullable=True),
        sa.Column('calories', Integer, nullable=True),
        sa.Column('protein', Float, nullable=True),
        sa.Column('carbs', Float, nullable=True),
        sa.Column('fat', Float, nullable=True),
        sa.Column('fiber', Float, nullable=True),
        sa.Column('sugar', Float, nullable=True),
        sa.Column('sodium', Float, nullable=True),
        sa.Column('analysis_status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='analysisstatusenum'), nullable=False, server_default='PENDING'),
        sa.Column('is_analyzed', Boolean, nullable=False, server_default='0')
    )
    
    # Create meal_images table
    op.create_table('meal_images',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('meal_id', Integer, ForeignKey('meals.id'), nullable=False),
        sa.Column('original_filename', String(255), nullable=True),
        sa.Column('file_path', Text, nullable=False),
        sa.Column('file_size', Integer, nullable=True),
        sa.Column('mime_type', String(100), nullable=True),
        sa.Column('width', Integer, nullable=True),
        sa.Column('height', Integer, nullable=True),
        sa.Column('upload_source', sa.Enum('MOBILE', 'WEB', 'API', name='uploadsourceenum'), nullable=False, server_default='MOBILE'),
        sa.Column('is_primary', Boolean, nullable=False, server_default='0')
    )
    
    # Create nutrition_facts table
    op.create_table('nutrition_facts',
        sa.Column('id', Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('meal_id', Integer, ForeignKey('meals.id'), nullable=False),
        sa.Column('serving_size', String(100), nullable=True),
        sa.Column('calories_per_serving', Integer, nullable=True),
        sa.Column('total_fat', Float, nullable=True),
        sa.Column('saturated_fat', Float, nullable=True),
        sa.Column('trans_fat', Float, nullable=True),
        sa.Column('cholesterol', Float, nullable=True),
        sa.Column('sodium', Float, nullable=True),
        sa.Column('total_carbs', Float, nullable=True),
        sa.Column('dietary_fiber', Float, nullable=True),
        sa.Column('total_sugars', Float, nullable=True),
        sa.Column('added_sugars', Float, nullable=True),
        sa.Column('protein', Float, nullable=True),
        sa.Column('vitamin_d', Float, nullable=True),
        sa.Column('calcium', Float, nullable=True),
        sa.Column('iron', Float, nullable=True),
        sa.Column('potassium', Float, nullable=True)
    )


def downgrade():
    """Drop initial database schema"""
    op.drop_table('nutrition_facts')
    op.drop_table('meal_images')
    op.drop_table('meals')
    op.drop_table('planned_meals')
    op.drop_table('meal_plan_days')
    op.drop_table('meal_plans')
    op.drop_table('user_profiles')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS genderenum')
    op.execute('DROP TYPE IF EXISTS activitylevelenum')
    op.execute('DROP TYPE IF EXISTS fitnessgoalenum')
    op.execute('DROP TYPE IF EXISTS mealtypeenum')
    op.execute('DROP TYPE IF EXISTS analysisstatusenum')
    op.execute('DROP TYPE IF EXISTS uploadsourceenum')