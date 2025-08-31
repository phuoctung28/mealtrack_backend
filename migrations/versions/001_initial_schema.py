"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-08-28 22:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema to match actual models"""
    
    # Create users table - basic version without enhancements (firebase_uid, phone_number, etc. added in migration 002)
    op.create_table('users',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        # Basic Information
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        # Authentication
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        # Status & Activity
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    logger.info("✅ Created users table")
    
    # Create user_profiles table - matches UserProfile model
    op.create_table('user_profiles',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('gender', sa.String(length=20), nullable=False),
        sa.Column('height_cm', sa.Float(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('body_fat_percentage', sa.Float(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='1'),
        # Goal fields
        sa.Column('activity_level', sa.String(length=30), nullable=False, server_default='sedentary'),
        sa.Column('fitness_goal', sa.String(length=30), nullable=False, server_default='maintenance'),
        sa.Column('target_weight_kg', sa.Float(), nullable=True),
        sa.Column('meals_per_day', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('snacks_per_day', sa.Integer(), nullable=False, server_default='1'),
        # Preference fields
        sa.Column('dietary_preferences', sa.JSON(), nullable=False),
        sa.Column('health_conditions', sa.JSON(), nullable=False),
        sa.Column('allergies', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('age >= 13 AND age <= 120', name='check_age_range'),
        sa.CheckConstraint('height_cm > 0', name='check_height_positive'),
        sa.CheckConstraint('weight_kg > 0', name='check_weight_positive'),
        sa.CheckConstraint('body_fat_percentage IS NULL OR (body_fat_percentage >= 0 AND body_fat_percentage <= 100)', name='check_body_fat_range')
    )
    logger.info("✅ Created user_profiles table")
    
    # Create meal_plans table - matches MealPlan model
    op.create_table('meal_plans',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, index=True),
        # User preferences stored as JSON
        sa.Column('dietary_preferences', sa.JSON(), nullable=True),
        sa.Column('allergies', sa.JSON(), nullable=True),
        sa.Column('fitness_goal', sa.String(length=20), nullable=True),
        sa.Column('meals_per_day', sa.Integer(), nullable=True),
        sa.Column('snacks_per_day', sa.Integer(), nullable=True),
        sa.Column('cooking_time_weekday', sa.Integer(), nullable=True),
        sa.Column('cooking_time_weekend', sa.Integer(), nullable=True),
        sa.Column('favorite_cuisines', sa.JSON(), nullable=True),
        sa.Column('disliked_ingredients', sa.JSON(), nullable=True),
        sa.Column('plan_duration', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created meal_plans table")
    
    # Create meal_plan_days table - matches MealPlanDay model
    op.create_table('meal_plan_days',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('meal_plan_id', sa.CHAR(36), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plans.id']),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created meal_plan_days table")
    
    # Create planned_meals table - matches PlannedMeal model
    op.create_table('planned_meals',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('day_id', sa.Integer(), nullable=False),
        sa.Column('meal_type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prep_time', sa.Integer(), nullable=True),
        sa.Column('cook_time', sa.Integer(), nullable=True),
        # Nutrition info
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('carbs', sa.Float(), nullable=True),
        sa.Column('fat', sa.Float(), nullable=True),
        # Stored as JSON arrays
        sa.Column('ingredients', sa.JSON(), nullable=True),
        sa.Column('instructions', sa.JSON(), nullable=True),
        # Dietary flags
        sa.Column('is_vegetarian', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('is_vegan', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('is_gluten_free', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('cuisine_type', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['day_id'], ['meal_plan_days.id']),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created planned_meals table")
    
    # Create mealimage table - matches MealImage model
    op.create_table('mealimage',
        sa.Column('image_id', sa.CHAR(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('format', sa.String(length=10), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('image_id')
    )
    logger.info("✅ Created mealimage table")
    
    # Create meal table - matches Meal model
    op.create_table('meal',
        sa.Column('meal_id', sa.CHAR(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False, index=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('dish_name', sa.String(length=255), nullable=True),
        sa.Column('ready_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_ai_response', sa.Text(), nullable=True),
        sa.Column('image_id', sa.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['mealimage.image_id']),
        sa.PrimaryKeyConstraint('meal_id')
    )
    logger.info("✅ Created meal table")
    
    # Create nutrition table - matches Nutrition model
    op.create_table('nutrition',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('calories', sa.Float(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('raw_ai_response', sa.Text(), nullable=True),
        # Macro fields
        sa.Column('protein', sa.Float(), nullable=False, server_default='0'),
        sa.Column('carbs', sa.Float(), nullable=False, server_default='0'),
        sa.Column('fat', sa.Float(), nullable=False, server_default='0'),
        sa.Column('fiber', sa.Float(), nullable=True),
        sa.Column('meal_id', sa.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(['meal_id'], ['meal.meal_id']),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created nutrition table")
    
    # Create food_item table - matches FoodItem model
    op.create_table('food_item',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('calories', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        # Macro fields
        sa.Column('protein', sa.Float(), nullable=False, server_default='0'),
        sa.Column('carbs', sa.Float(), nullable=False, server_default='0'),
        sa.Column('fat', sa.Float(), nullable=False, server_default='0'),
        sa.Column('fiber', sa.Float(), nullable=True),
        sa.Column('nutrition_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['nutrition_id'], ['nutrition.id']),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created food_item table")


def downgrade() -> None:
    """Drop initial database schema"""
    # Drop tables in reverse order of creation (respecting foreign key constraints)
    op.drop_table('food_item')
    op.drop_table('nutrition')
    op.drop_table('meal')
    op.drop_table('mealimage')
    op.drop_table('planned_meals')
    op.drop_table('meal_plan_days')
    op.drop_table('meal_plans')
    op.drop_table('user_profiles')
    op.drop_table('users')
    logger.info("✅ Dropped all tables")