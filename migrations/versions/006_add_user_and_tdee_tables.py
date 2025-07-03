"""Add user and TDEE tables

Revision ID: 006
Revises: 005
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('gender', sa.String(20), nullable=False),
        sa.Column('height_cm', sa.Float(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('body_fat_percentage', sa.Float(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('age >= 13 AND age <= 120', name='check_age_range'),
        sa.CheckConstraint('height_cm > 0', name='check_height_positive'),
        sa.CheckConstraint('weight_kg > 0', name='check_weight_positive'),
        sa.CheckConstraint('body_fat_percentage IS NULL OR (body_fat_percentage >= 0 AND body_fat_percentage <= 100)', 
                          name='check_body_fat_range'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_current', 'user_profiles', ['user_id', 'is_current'], unique=False)
    
    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create user_dietary_preferences table
    op.create_table('user_dietary_preferences',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_preference_id', sa.String(36), nullable=False),
        sa.Column('preference', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_preference_id'], ['user_preferences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dietary_preference', 'user_dietary_preferences', ['user_preference_id'], unique=False)
    
    # Create user_health_conditions table
    op.create_table('user_health_conditions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_preference_id', sa.String(36), nullable=False),
        sa.Column('condition', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_preference_id'], ['user_preferences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_health_condition', 'user_health_conditions', ['user_preference_id'], unique=False)
    
    # Create user_allergies table
    op.create_table('user_allergies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_preference_id', sa.String(36), nullable=False),
        sa.Column('allergen', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_preference_id'], ['user_preferences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_allergen', 'user_allergies', ['user_preference_id'], unique=False)
    
    # Create user_goals table
    op.create_table('user_goals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('activity_level', sa.String(30), nullable=False),
        sa.Column('fitness_goal', sa.String(30), nullable=False),
        sa.Column('target_weight_kg', sa.Float(), nullable=True),
        sa.Column('meals_per_day', sa.Integer(), nullable=False, default=3),
        sa.Column('snacks_per_day', sa.Integer(), nullable=False, default=1),
        sa.Column('is_current', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('target_weight_kg IS NULL OR target_weight_kg > 0', name='check_target_weight_positive'),
        sa.CheckConstraint('meals_per_day >= 1 AND meals_per_day <= 10', name='check_meals_per_day_range'),
        sa.CheckConstraint('snacks_per_day >= 0 AND snacks_per_day <= 10', name='check_snacks_per_day_range'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_goal_current', 'user_goals', ['user_id', 'is_current'], unique=False)
    
    # Create tdee_calculations table
    op.create_table('tdee_calculations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('user_profile_id', sa.String(36), nullable=False),
        sa.Column('user_goal_id', sa.String(36), nullable=False),
        sa.Column('bmr', sa.Float(), nullable=False),
        sa.Column('tdee', sa.Float(), nullable=False),
        sa.Column('target_calories', sa.Float(), nullable=False),
        sa.Column('protein_grams', sa.Float(), nullable=False),
        sa.Column('carbs_grams', sa.Float(), nullable=False),
        sa.Column('fat_grams', sa.Float(), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('bmr > 0', name='check_bmr_positive'),
        sa.CheckConstraint('tdee > 0', name='check_tdee_positive'),
        sa.CheckConstraint('target_calories > 0', name='check_target_calories_positive'),
        sa.CheckConstraint('protein_grams >= 0', name='check_protein_non_negative'),
        sa.CheckConstraint('carbs_grams >= 0', name='check_carbs_non_negative'),
        sa.CheckConstraint('fat_grams >= 0', name='check_fat_non_negative'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_profile_id'], ['user_profiles.id']),
        sa.ForeignKeyConstraint(['user_goal_id'], ['user_goals.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_date', 'tdee_calculations', ['user_id', 'calculation_date'], unique=False)
    
    # Add foreign key constraints to existing tables using batch mode for SQLite
    # Update meal_plans table to reference users
    with op.batch_alter_table('meal_plans') as batch_op:
        batch_op.add_column(sa.Column('new_user_id', sa.String(36), nullable=True))
        # Note: SQLite doesn't enforce foreign keys by default, so we just add the column
    
    # Update conversations table to reference users  
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.add_column(sa.Column('new_user_id', sa.String(36), nullable=True))
        # Note: SQLite doesn't enforce foreign keys by default, so we just add the column


def downgrade():
    # Remove columns from existing tables using batch mode
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.drop_column('new_user_id')
    
    with op.batch_alter_table('meal_plans') as batch_op:
        batch_op.drop_column('new_user_id')
    
    # Drop tables in reverse order
    op.drop_index('idx_user_date', table_name='tdee_calculations')
    op.drop_table('tdee_calculations')
    
    op.drop_index('idx_user_goal_current', table_name='user_goals')
    op.drop_table('user_goals')
    
    op.drop_index('idx_allergen', table_name='user_allergies')
    op.drop_table('user_allergies')
    
    op.drop_index('idx_health_condition', table_name='user_health_conditions')
    op.drop_table('user_health_conditions')
    
    op.drop_index('idx_dietary_preference', table_name='user_dietary_preferences')
    op.drop_table('user_dietary_preferences')
    
    op.drop_table('user_preferences')
    
    op.drop_index('idx_user_current', table_name='user_profiles')
    op.drop_table('user_profiles')
    
    op.drop_table('users')