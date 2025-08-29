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
    """Create initial database schema"""
    
    # Create users table (basic version without enhancements)
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    logger.info("✅ Created users table")
    
    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.Enum('MALE', 'FEMALE', 'OTHER', name='genderenum'), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('body_fat_percentage', sa.Float(), nullable=True),
        sa.Column('activity_level', sa.Enum('SEDENTARY', 'LIGHTLY_ACTIVE', 'MODERATELY_ACTIVE', 'VERY_ACTIVE', 'EXTREMELY_ACTIVE', name='activitylevelenum'), nullable=True),
        sa.Column('fitness_goal', sa.Enum('WEIGHT_LOSS', 'WEIGHT_GAIN', 'MUSCLE_GAIN', 'MAINTENANCE', 'BODY_RECOMPOSITION', name='fitnessgoalenum'), nullable=True),
        sa.Column('dietary_preferences', sa.JSON(), nullable=True),
        sa.Column('tdee', sa.Float(), nullable=True),
        sa.Column('target_calories', sa.Integer(), nullable=True),
        sa.Column('target_protein', sa.Float(), nullable=True),
        sa.Column('target_carbs', sa.Float(), nullable=True),
        sa.Column('target_fat', sa.Float(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created user_profiles table")
    
    # Create meal_plans table
    op.create_table('meal_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created meal_plans table")
    
    # Create meal_plan_days table
    op.create_table('meal_plan_days',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_calories', sa.Integer(), nullable=True),
        sa.Column('total_protein', sa.Float(), nullable=True),
        sa.Column('total_carbs', sa.Float(), nullable=True),
        sa.Column('total_fat', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['meal_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created meal_plan_days table")
    
    # Create planned_meals table (without seasonings initially)
    op.create_table('planned_meals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('day_id', sa.Integer(), nullable=False),
        sa.Column('meal_type', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', 'SNACK', name='mealtypeenum'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prep_time', sa.Integer(), nullable=True),
        sa.Column('cook_time', sa.Integer(), nullable=True),
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('carbs', sa.Float(), nullable=True),
        sa.Column('fat', sa.Float(), nullable=True),
        sa.Column('ingredients', sa.JSON(), nullable=True),
        sa.Column('instructions', sa.JSON(), nullable=True),
        sa.Column('is_vegetarian', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_vegan', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_gluten_free', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('cuisine_type', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['day_id'], ['meal_plan_days.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created planned_meals table")
    
    # Create meals table
    op.create_table('meals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', 'SNACK', name='mealtypeenum'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('carbs', sa.Float(), nullable=True),
        sa.Column('fat', sa.Float(), nullable=True),
        sa.Column('fiber', sa.Float(), nullable=True),
        sa.Column('sugar', sa.Float(), nullable=True),
        sa.Column('sodium', sa.Float(), nullable=True),
        sa.Column('analysis_status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='analysisstatusenum'), nullable=False, server_default='PENDING'),
        sa.Column('is_analyzed', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created meals table")
    
    # Create meal_images table
    op.create_table('meal_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('meal_id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('upload_source', sa.Enum('MOBILE', 'WEB', 'API', name='uploadsourceenum'), nullable=False, server_default='MOBILE'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['meal_id'], ['meals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created meal_images table")
    
    # Create nutrition_facts table
    op.create_table('nutrition_facts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('meal_id', sa.Integer(), nullable=False),
        sa.Column('serving_size', sa.String(length=100), nullable=True),
        sa.Column('calories_per_serving', sa.Integer(), nullable=True),
        sa.Column('total_fat', sa.Float(), nullable=True),
        sa.Column('saturated_fat', sa.Float(), nullable=True),
        sa.Column('trans_fat', sa.Float(), nullable=True),
        sa.Column('cholesterol', sa.Float(), nullable=True),
        sa.Column('sodium', sa.Float(), nullable=True),
        sa.Column('total_carbs', sa.Float(), nullable=True),
        sa.Column('dietary_fiber', sa.Float(), nullable=True),
        sa.Column('total_sugars', sa.Float(), nullable=True),
        sa.Column('added_sugars', sa.Float(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('vitamin_d', sa.Float(), nullable=True),
        sa.Column('calcium', sa.Float(), nullable=True),
        sa.Column('iron', sa.Float(), nullable=True),
        sa.Column('potassium', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['meal_id'], ['meals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    logger.info("✅ Created nutrition_facts table")


def downgrade() -> None:
    """Drop initial database schema"""
    op.drop_table('nutrition_facts')
    op.drop_table('meal_images')
    op.drop_table('meals')
    op.drop_table('planned_meals')
    op.drop_table('meal_plan_days')
    op.drop_table('meal_plans')
    op.drop_table('user_profiles')
    op.drop_table('users')
    logger.info("✅ Dropped all tables")
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS genderenum')
    op.execute('DROP TYPE IF EXISTS activitylevelenum')
    op.execute('DROP TYPE IF EXISTS fitnessgoalenum')
    op.execute('DROP TYPE IF EXISTS mealtypeenum')
    op.execute('DROP TYPE IF EXISTS analysisstatusenum')
    op.execute('DROP TYPE IF EXISTS uploadsourceenum')
    logger.info("✅ Dropped enums")