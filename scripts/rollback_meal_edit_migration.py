#!/usr/bin/env python3
"""
Script to rollback the meal edit feature migration.

This script will:
1. Check current migration status
2. Rollback the meal edit migration (004 -> 003)
3. Verify the rollback was successful

⚠️  WARNING: This will remove all meal edit data including:
- Edit history (edit_count, last_edited_at, is_manually_edited)
- Food item IDs and USDA references
- Custom ingredient flags
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(
            command.split(), 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def confirm_rollback():
    """Confirm the user wants to proceed with rollback."""
    print("\n⚠️  WARNING: DESTRUCTIVE OPERATION")
    print("=" * 50)
    print("This will remove the following data:")
    print("• All meal edit history")
    print("• Food item editing metadata")
    print("• USDA food references")
    print("• Custom ingredient flags")
    print("\nThis operation cannot be undone without data loss!")
    
    response = input("\nDo you want to continue? Type 'yes' to proceed: ").strip().lower()
    return response == 'yes'

def main():
    """Main function to rollback the meal edit migration."""
    print("🔄 Rolling Back Meal Edit Feature Migration")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("alembic.ini"):
        print("❌ Error: alembic.ini not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Check current migration status
    print("\n📋 Current Migration Status:")
    try:
        result = subprocess.run(
            ["python3", "-m", "alembic", "current"], 
            capture_output=True, 
            text=True
        )
        if result.stdout:
            current_revision = result.stdout.strip()
            print(current_revision)
            
            if "004" not in current_revision:
                print("\n❌ Migration 004 is not currently applied.")
                print("Nothing to rollback.")
                sys.exit(0)
    except Exception as e:
        print(f"Warning: Could not check current status: {e}")
    
    # Confirm rollback
    if not confirm_rollback():
        print("\n❌ Rollback cancelled by user.")
        sys.exit(0)
    
    # Show what will be rolled back
    if not run_command("python3 -m alembic downgrade --sql 004:003", "Showing rollback SQL (dry run)"):
        print("⚠️  Warning: Could not generate rollback SQL, but continuing...")
    
    # Perform the rollback
    if not run_command("python3 -m alembic downgrade 003", "Rolling back meal edit migration"):
        print("\n❌ Rollback failed. Please check the error messages above.")
        sys.exit(1)
    
    # Verify rollback was successful
    print("\n✅ Rollback Completed Successfully!")
    print("\n📋 New Migration Status:")
    try:
        result = subprocess.run(
            ["python3", "-m", "alembic", "current"], 
            capture_output=True, 
            text=True
        )
        if result.stdout:
            print(result.stdout)
    except Exception as e:
        print(f"Warning: Could not verify final status: {e}")
    
    print("\n🔄 Meal Edit Feature Database Schema Rolled Back!")
    print("\nThe following changes have been reverted:")
    print("• Removed edit tracking fields from meal table")
    print("• Removed USDA integration fields from food_item table")
    print("• Dropped performance indexes for meal editing")
    print("\n⚠️  Note: Any meal edit data has been permanently lost.")

if __name__ == "__main__":
    main()
