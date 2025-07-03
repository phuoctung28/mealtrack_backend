"""Add meal planning tables

Revision ID: 005
Revises: 004
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create meal_plans table
    op.create_table('meal_plans',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('dietary_preferences', sa.JSON(), nullable=True),
        sa.Column('allergies', sa.JSON(), nullable=True),
        sa.Column('fitness_goal', sa.Enum('weight_loss', 'muscle_gain', 'maintenance', 'general_health', name='fitnessgoalenum'), nullable=True),
        sa.Column('meals_per_day', sa.Integer(), nullable=True),
        sa.Column('snacks_per_day', sa.Integer(), nullable=True),
        sa.Column('cooking_time_weekday', sa.Integer(), nullable=True),
        sa.Column('cooking_time_weekend', sa.Integer(), nullable=True),
        sa.Column('favorite_cuisines', sa.JSON(), nullable=True),
        sa.Column('disliked_ingredients', sa.JSON(), nullable=True),
        sa.Column('plan_duration', sa.Enum('daily', 'weekly', name='plandurationenum'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meal_plans_user_id'), 'meal_plans', ['user_id'], unique=False)
    
    # Create meal_plan_days table
    op.create_table('meal_plan_days',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('meal_plan_id', sa.String(36), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create planned_meals table
    op.create_table('planned_meals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('day_id', sa.String(36), nullable=False),
        sa.Column('meal_type', sa.Enum('breakfast', 'lunch', 'dinner', 'snack', name='mealtypeenum'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prep_time', sa.Integer(), nullable=True),
        sa.Column('cook_time', sa.Integer(), nullable=True),
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('carbs', sa.Float(), nullable=True),
        sa.Column('fat', sa.Float(), nullable=True),
        sa.Column('ingredients', sa.JSON(), nullable=True),
        sa.Column('instructions', sa.JSON(), nullable=True),
        sa.Column('is_vegetarian', sa.Boolean(), nullable=True),
        sa.Column('is_vegan', sa.Boolean(), nullable=True),
        sa.Column('is_gluten_free', sa.Boolean(), nullable=True),
        sa.Column('cuisine_type', sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(['day_id'], ['meal_plan_days.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create conversations table
    op.create_table('conversations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('state', sa.Enum('greeting', 'asking_dietary_preferences', 'asking_allergies', 
                                  'asking_fitness_goals', 'asking_meal_count', 'asking_plan_duration',
                                  'asking_cooking_time', 'asking_cuisine_preferences', 'confirming_preferences',
                                  'generating_plan', 'showing_plan', 'adjusting_meal', 'completed',
                                  name='conversationstateenum'), nullable=False),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)
    
    # Create conversation_messages table
    op.create_table('conversation_messages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('conversation_id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('conversation_messages')
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_table('planned_meals')
    op.drop_table('meal_plan_days')
    op.drop_index(op.f('ix_meal_plans_user_id'), table_name='meal_plans')
    op.drop_table('meal_plans')
    
    # Drop enums
    sa.Enum(name='conversationstateenum').drop(op.get_bind())
    sa.Enum(name='mealtypeenum').drop(op.get_bind())
    sa.Enum(name='plandurationenum').drop(op.get_bind())
    sa.Enum(name='fitnessgoalenum').drop(op.get_bind())