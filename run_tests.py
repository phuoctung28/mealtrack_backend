#!/usr/bin/env python3
"""
Test runner script for the MealTrack application.

Usage:
    python run_tests.py [command] [options]

Commands:
    health      - Quick health check
    fast        - Run fast tests only
    unit        - Run unit tests
    integration - Run integration tests
    api         - Run API tests
    validation  - Run validation tests
    performance - Run performance tests
    coverage    - Run tests with coverage report
    all         - Run all tests
    clean       - Clean test artifacts

Examples:
    python run_tests.py fast
    python run_tests.py coverage
    python run_tests.py unit --verbose
"""

import os
import sys
import subprocess
import shutil
import time
import argparse
from pathlib import Path
import requests
from typing import List, Optional


class TestRunner:
    """Test runner for MealTrack application."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.python_path = sys.executable
        
    def check_server_health(self, max_retries: int = 5) -> bool:
        """Check if the server is running and healthy."""
        print("Checking server health...")
        
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Server is healthy")
                    return True
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    print(f"⏳ Waiting for server... ({i+1}/{max_retries})")
                    time.sleep(2)
        
        print("❌ Server is not responding. Please start the server first.")
        return False
    
    def run_command(self, cmd: List[str], check_health: bool = False) -> int:
        """Run a command and return the exit code."""
        if check_health and not self.check_server_health():
            return 1
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)
        env["TESTING"] = "true"
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env)
        return result.returncode
    
    def clean_artifacts(self):
        """Clean test artifacts."""
        print("Cleaning test artifacts...")
        
        artifacts = [
            ".coverage",
            "coverage.xml",
            "htmlcov",
            ".pytest_cache",
            "**/__pycache__",
            "**/*.pyc",
            ".mypy_cache",
            ".ruff_cache"
        ]
        
        for pattern in artifacts:
            if "**" in pattern:
                for path in self.project_root.glob(pattern):
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
            else:
                path = self.project_root / pattern
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
        
        print("✅ Cleaned test artifacts")
    
    def run_health_check(self) -> int:
        """Run a quick health check."""
        return self.run_command([
            self.python_path, "-m", "pytest",
            "-m", "fast",
            "-k", "test_health",
            "--tb=short",
            "-v"
        ])
    
    def run_fast_tests(self) -> int:
        """Run fast tests only."""
        return self.run_command([
            self.python_path, "-m", "pytest",
            "-m", "fast",
            "--tb=short",
            "-v"
        ])
    
    def run_unit_tests(self, verbose: bool = False) -> int:
        """Run unit tests."""
        cmd = [
            self.python_path, "-m", "pytest",
            "-m", "unit",
            "--tb=short"
        ]
        if verbose:
            cmd.append("-vv")
        else:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_integration_tests(self) -> int:
        """Run integration tests."""
        return self.run_command([
            self.python_path, "-m", "pytest",
            "-m", "integration",
            "--tb=short",
            "-v"
        ])
    
    def run_api_tests(self) -> int:
        """Run API tests."""
        return self.run_command([
            self.python_path, "-m", "pytest",
            "-m", "api",
            "--tb=short",
            "-v"
        ], check_health=True)
    
    def run_validation_tests(self) -> int:
        """Run validation tests."""
        return self.run_command([
            self.python_path, "-m", "pytest",
            "-m", "validation",
            "--tb=short",
            "-v"
        ])
    
    def run_performance_tests(self) -> int:
        """Run performance tests."""
        return self.run_command([
            self.python_path, "-m", "pytest",
            "-m", "performance",
            "--tb=short",
            "-v"
        ])
    
    def run_with_coverage(self) -> int:
        """Run all tests with coverage report."""
        result = self.run_command([
            self.python_path, "-m", "pytest",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-report=xml",
            "--tb=short",
            "-v"
        ])
        
        if result == 0:
            print("\n📊 Coverage report generated:")
            print("   - Terminal: See above")
            print("   - HTML: htmlcov/index.html")
            print("   - XML: coverage.xml")
        
        return result
    
    def run_all_tests(self) -> int:
        """Run all tests."""
        return self.run_command([
            self.python_path, "-m", "pytest",
            "--tb=short",
            "-v"
        ])


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test runner for MealTrack application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "command",
        choices=[
            "health", "fast", "unit", "integration", "api",
            "validation", "performance", "coverage", "all", "clean"
        ],
        help="Test command to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    command_map = {
        "health": runner.run_health_check,
        "fast": runner.run_fast_tests,
        "unit": lambda: runner.run_unit_tests(args.verbose),
        "integration": runner.run_integration_tests,
        "api": runner.run_api_tests,
        "validation": runner.run_validation_tests,
        "performance": runner.run_performance_tests,
        "coverage": runner.run_with_coverage,
        "all": runner.run_all_tests,
        "clean": lambda: (runner.clean_artifacts(), 0)[1]
    }
    
    exit_code = command_map[args.command]()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()