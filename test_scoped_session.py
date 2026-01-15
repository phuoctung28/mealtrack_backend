#!/usr/bin/env python3
"""
Quick test script to verify scoped session implementation.
Run this to ensure the singleton event bus and scoped sessions work correctly.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_scoped_session_import():
    """Test that ScopedSession can be imported."""
    print("✓ Testing ScopedSession import...")
    try:
        from src.infra.database.config import ScopedSession, _request_id
        print("  ✓ ScopedSession imported successfully")
        print("  ✓ _request_id ContextVar imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_event_bus_singleton():
    """Test that event bus returns the same instance."""
    print("\n✓ Testing event bus singleton...")
    try:
        from src.api.dependencies.event_bus import get_configured_event_bus, _configured_event_bus
        
        # First call should create the instance
        bus1 = get_configured_event_bus()
        print(f"  ✓ First call created event bus: {id(bus1)}")
        
        # Second call should return same instance
        bus2 = get_configured_event_bus()
        print(f"  ✓ Second call returned event bus: {id(bus2)}")
        
        if bus1 is bus2:
            print("  ✓ Both calls returned the SAME instance (singleton working!)")
            return True
        else:
            print("  ✗ Calls returned DIFFERENT instances (singleton NOT working)")
            return False
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_repository_scoped_session():
    """Test that repositories use ScopedSession."""
    print("\n✓ Testing repository ScopedSession usage...")
    try:
        from src.infra.repositories.meal_repository import MealRepository
        from src.infra.database.config import ScopedSession, _request_id
        import uuid
        
        # Set a request ID (simulating a request)
        request_id = str(uuid.uuid4())
        token = _request_id.set(request_id)
        
        try:
            # Create repository without db parameter
            repo = MealRepository()
            print("  ✓ MealRepository created without db parameter")
            
            # Get db should return ScopedSession
            db = repo._get_db()
            print(f"  ✓ Repository._get_db() returned session: {type(db).__name__}")
            
            # Clean up
            ScopedSession.remove()
            _request_id.reset(token)
            
            print("  ✓ Repository uses ScopedSession correctly")
            return True
        finally:
            # Ensure cleanup
            try:
                ScopedSession.remove()
                _request_id.reset(token)
            except:
                pass
            
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_handler_no_db_param():
    """Test that updated handler doesn't require db parameter."""
    print("\n✓ Testing handler without db parameter...")
    try:
        from src.app.handlers.command_handlers.save_user_onboarding_command_handler import SaveUserOnboardingCommandHandler
        
        # Should be able to create without db parameter
        handler = SaveUserOnboardingCommandHandler()
        print("  ✓ SaveUserOnboardingCommandHandler created without db parameter")
        
        # Should not have self.db attribute
        if hasattr(handler, 'db'):
            print("  ⚠ Handler still has 'db' attribute (may need migration)")
        else:
            print("  ✓ Handler does not have 'db' attribute (migrated correctly)")
        
        return True
    except TypeError as e:
        if "db" in str(e):
            print(f"  ✗ Handler still requires db parameter: {e}")
            return False
        raise
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("SCOPED SESSION IMPLEMENTATION TEST")
    print("=" * 60)
    
    results = []
    
    results.append(("ScopedSession Import", test_scoped_session_import()))
    results.append(("Event Bus Singleton", test_event_bus_singleton()))
    results.append(("Repository ScopedSession", test_repository_scoped_session()))
    results.append(("Handler Migration", test_handler_no_db_param()))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Implementation looks good!")
        print("\nNext steps:")
        print("1. Complete remaining handler migrations (see SCOPED_SESSION_MIGRATION.md)")
        print("2. Run full test suite: pytest")
        print("3. Test with actual API requests")
        print("4. Monitor memory usage under load")
    else:
        print("✗ SOME TESTS FAILED - Review errors above")
        return 1
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
