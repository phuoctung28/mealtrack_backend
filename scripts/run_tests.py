#!/usr/bin/env python3
"""
Test runner script for MealTrack API tests.

Usage:
    python run_tests.py [command] [options]

Commands:
    all         - Run all tests
    api         - Run API integration tests only
    performance - Run performance tests only
    validation  - Run validation tests only
    fast        - Run fast tests only
    slow        - Run slow tests only
    health      - Quick health check
    coverage    - Run tests with coverage report
    parallel    - Run tests in parallel (faster)
    
Options:
    --server-url URL    - API server URL (default: http://localhost:8000)
    --verbose           - Verbose output
    --quiet             - Minimal output
    --html              - Generate HTML report
    --junit             - Generate JUnit XML report
"""

import argparse
import os
import subprocess
import sys
import time
from typing import List

import httpx


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def check_server_health(server_url: str) -> bool:
    """Check if the API server is running and healthy."""
    try:
        with httpx.Client() as client:
            response = client.get(f"{server_url}/health", timeout=10.0)
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def run_pytest_command(args: List[str], description: str) -> int:
    """Run a pytest command and return the exit code."""
    print_colored(f"\n🧪 {description}", Colors.HEADER)
    print_colored("=" * 60, Colors.HEADER)
    
    cmd = ["python", "-m", "pytest"] + args
    print_colored(f"Running: {' '.join(cmd)}", Colors.OKBLUE)
    
    start_time = time.time()
    result = subprocess.run(cmd)
    end_time = time.time()
    
    duration = end_time - start_time
    if result.returncode == 0:
        print_colored(f"✅ {description} completed successfully in {duration:.2f}s", Colors.OKGREEN)
    else:
        print_colored(f"❌ {description} failed in {duration:.2f}s", Colors.FAIL)
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="MealTrack API Test Runner")
    parser.add_argument("command", nargs="?", default="all",
                       choices=["all", "api", "performance", "validation", "fast", "slow", 
                               "health", "coverage", "parallel"],
                       help="Test command to run")
    parser.add_argument("--server-url", default="http://localhost:8000",
                       help="API server URL")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--quiet", action="store_true", 
                       help="Minimal output")
    parser.add_argument("--html", action="store_true",
                       help="Generate HTML report")
    parser.add_argument("--junit", action="store_true",
                       help="Generate JUnit XML report")
    
    args = parser.parse_args()
    
    # Set environment variable for tests
    os.environ["TEST_BASE_URL"] = args.server_url
    
    print_colored("🍎 MealTrack API Test Runner", Colors.BOLD + Colors.HEADER)
    print_colored(f"Server URL: {args.server_url}", Colors.OKCYAN)
    
    # Check server health first
    if args.command != "help":
        print_colored("\n🔍 Checking server health...", Colors.OKCYAN)
        if check_server_health(args.server_url):
            print_colored("✅ Server is healthy and ready for testing", Colors.OKGREEN)
        else:
            print_colored("⚠️  Warning: Server health check failed", Colors.WARNING)
            print_colored("Tests may fail if the server is not running", Colors.WARNING)
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print_colored("❌ Aborted by user", Colors.FAIL)
                return 1
    
    # Build base pytest arguments
    base_args = []
    
    if args.verbose:
        base_args.append("-v")
    elif args.quiet:
        base_args.append("-q")
    
    # Add reporting options
    reports_dir = "test_reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    if args.html:
        base_args.extend(["--html", f"{reports_dir}/report.html", "--self-contained-html"])
    
    if args.junit:
        base_args.extend(["--junit-xml", f"{reports_dir}/junit.xml"])
    
    # Define test configurations
    test_configs = {
        "health": {
            "args": ["tests/test_api_endpoints.py::TestHealthAndRoot", "-v"],
            "description": "Quick Health Check"
        },
        "fast": {
            "args": ["-m", "not slow", "--durations=5"],
            "description": "Fast Tests (excluding slow tests)"
        },
        "slow": {
            "args": ["-m", "slow", "--durations=0"],
            "description": "Slow Tests Only"
        },
        "api": {
            "args": ["-m", "api", "--durations=10"],
            "description": "API Integration Tests"
        },
        "performance": {
            "args": ["tests/test_performance.py", "-m", "api", "--durations=0"],
            "description": "Performance Tests"
        },
        "validation": {
            "args": ["tests/test_validation.py", "-m", "api"],
            "description": "Validation & Error Handling Tests"
        },
        "coverage": {
            "args": ["--cov=api", "--cov-report=html", "--cov-report=term-missing", 
                    "--cov-fail-under=80"],
            "description": "Tests with Coverage Report"
        },
        "parallel": {
            "args": ["-n", "auto", "--durations=10"],
            "description": "Parallel Test Execution"
        },
        "all": {
            "args": ["--durations=10"],
            "description": "All Tests"
        }
    }
    
    # Get the test configuration
    config = test_configs.get(args.command)
    if not config:
        print_colored(f"❌ Unknown command: {args.command}", Colors.FAIL)
        return 1
    
    # Run the tests
    pytest_args = base_args + config["args"]
    exit_code = run_pytest_command(pytest_args, config["description"])
    
    # Print summary
    print_colored("\n" + "=" * 60, Colors.HEADER)
    if exit_code == 0:
        print_colored("🎉 All tests completed successfully!", Colors.OKGREEN)
    else:
        print_colored("💥 Some tests failed!", Colors.FAIL)
    
    # Show report locations
    if args.html:
        print_colored(f"📊 HTML Report: {reports_dir}/report.html", Colors.OKCYAN)
    if args.junit:
        print_colored(f"📋 JUnit Report: {reports_dir}/junit.xml", Colors.OKCYAN)
    
    return exit_code


def show_help():
    """Show detailed help information."""
    help_text = """
🍎 MealTrack API Test Runner

QUICK COMMANDS:
    python run_tests.py health      # Quick health check
    python run_tests.py fast        # Run fast tests only
    python run_tests.py api         # All API tests
    python run_tests.py validation  # Validation tests
    python run_tests.py performance # Performance tests
    python run_tests.py coverage    # Tests with coverage
    
EXAMPLES:
    # Quick test to see if everything works
    python run_tests.py health
    
    # Full test suite with HTML report
    python run_tests.py all --html
    
    # Performance tests with custom server
    python run_tests.py performance --server-url http://staging.example.com
    
    # Fast tests in parallel with minimal output
    python run_tests.py fast --parallel --quiet
    
MARKERS:
    You can also run pytest directly with markers:
    pytest -m "api and not slow"      # API tests excluding slow ones
    pytest -m "performance"           # Performance tests only
    pytest -m "validation"            # Validation tests only
    
TEST STRUCTURE:
    tests/
    ├── test_api_endpoints.py     # Main API endpoint tests
    ├── test_performance.py       # Performance & load tests
    ├── test_validation.py        # Validation & error tests
    └── conftest.py              # Shared fixtures & config
    
REQUIREMENTS:
    - API server running on specified URL
    - All dependencies installed (pip install -r requirements.txt)
    - pytest and httpx available
    """
    print_colored(help_text, Colors.OKCYAN)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "help":
        show_help()
        sys.exit(0)
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_colored("\n❌ Tests interrupted by user", Colors.WARNING)
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n💥 Unexpected error: {e}", Colors.FAIL)
        sys.exit(1) 