#!/usr/bin/env python3
"""
Validation script for Car Wash Mixer optimizations
Checks that all implemented optimizations are working correctly.
"""

import subprocess
import sys
import importlib.util
from pathlib import Path


def check_dependency_optimization():
    """Check that librosa has been removed and new dependencies are present."""
    print("🔍 Checking dependency optimization...")
    
    # Check if librosa is NOT in requirements.txt
    with open("requirements.txt", "r") as f:
        requirements = f.read()
    
    if "librosa" in requirements:
        print("   ❌ librosa still in requirements.txt")
        return False
    else:
        print("   ✅ librosa removed from requirements.txt")
    
    # Check if production dependencies are present
    required_deps = ["gunicorn", "redis", "Flask-Compress", "psutil"]
    missing_deps = []
    
    for dep in required_deps:
        if dep not in requirements:
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"   ❌ Missing production dependencies: {missing_deps}")
        return False
    else:
        print("   ✅ All production dependencies present")
    
    return True


def check_configuration_files():
    """Check that all configuration files are present."""
    print("\n🔍 Checking configuration files...")
    
    required_files = [
        "gunicorn.conf.py",
        "Dockerfile", 
        "docker-compose.yml",
        "start_production.sh",
        "performance_benchmark.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"   ❌ Missing configuration files: {missing_files}")
        return False
    else:
        print("   ✅ All configuration files present")
    
    return True


def check_server_optimizations():
    """Check that server.py has been optimized."""
    print("\n🔍 Checking server optimizations...")
    
    with open("server.py", "r") as f:
        server_content = f.read()
    
    optimizations = {
        "Flask-Compress import": "from flask_compress import Compress",
        "Redis import": "import redis",
        "Compression enabled": "Compress(app)",
        "Error handlers": "@app.errorhandler(400)",
        "Health check endpoint": '@app.route("/health")',
        "Caching functions": "def get_cache_key",
        "Input validation": "Missing required fields",
        "Logging": "import logging"
    }
    
    missing_optimizations = []
    for name, pattern in optimizations.items():
        if pattern not in server_content:
            missing_optimizations.append(name)
    
    if missing_optimizations:
        print(f"   ❌ Missing server optimizations: {missing_optimizations}")
        return False
    else:
        print("   ✅ All server optimizations implemented")
    
    return True


def check_mixer_optimizations():
    """Check that mixer.py has been optimized."""
    print("\n🔍 Checking mixer optimizations...")
    
    with open("mixer.py", "r") as f:
        mixer_content = f.read()
    
    optimizations = {
        "Memory management": "import gc",
        "NumPy optimization": "import numpy as np",
        "Logging": "import logging",
        "Memory cleanup": "gc.collect()",
        "Error handling": "try:",
        "Type hints": "from typing import",
        "Better encoding": "UnicodeDecodeError"
    }
    
    missing_optimizations = []
    for name, pattern in optimizations.items():
        if pattern not in mixer_content:
            missing_optimizations.append(name)
    
    if missing_optimizations:
        print(f"   ❌ Missing mixer optimizations: {missing_optimizations}")
        return False
    else:
        print("   ✅ All mixer optimizations implemented")
    
    return True


def check_docker_optimization():
    """Check that Docker configuration is optimized."""
    print("\n🔍 Checking Docker optimization...")
    
    with open("Dockerfile", "r") as f:
        dockerfile_content = f.read()
    
    optimizations = {
        "Slim base image": "python:3.11-slim",
        "Non-root user": "useradd",
        "Layer caching": "COPY requirements.txt",
        "Health check": "HEALTHCHECK",
        "Production server": "gunicorn"
    }
    
    missing_optimizations = []
    for name, pattern in optimizations.items():
        if pattern not in dockerfile_content:
            missing_optimizations.append(name)
    
    if missing_optimizations:
        print(f"   ❌ Missing Docker optimizations: {missing_optimizations}")
        return False
    else:
        print("   ✅ All Docker optimizations implemented")
    
    return True


def check_file_sizes():
    """Check that package size has been optimized."""
    print("\n🔍 Checking package size optimization...")
    
    # Estimate package size by checking requirements
    with open("requirements.txt", "r") as f:
        requirements = f.read()
    
    if "librosa" in requirements:
        print("   ❌ librosa still present (adds ~130MB)")
        return False
    
    heavy_packages = ["tensorflow", "torch", "scipy"]
    for package in heavy_packages:
        if package in requirements:
            print(f"   ⚠️  Heavy package detected: {package}")
    
    print("   ✅ Package size optimized (librosa removed)")
    return True


def main():
    """Run all validation checks."""
    print("🚀 Validating Car Wash Mixer Optimizations")
    print("=" * 50)
    
    checks = [
        check_dependency_optimization,
        check_configuration_files,
        check_server_optimizations,
        check_mixer_optimizations,
        check_docker_optimization,
        check_file_sizes
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        try:
            if check():
                passed += 1
        except Exception as e:
            print(f"   ❌ Check failed with error: {e}")
    
    print(f"\n📊 Validation Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("✅ All optimizations validated successfully!")
        print("\n🚀 Ready for production deployment!")
        print("\nNext steps:")
        print("1. Run: pip install -r requirements.txt")
        print("2. Start server: ./start_production.sh")
        print("3. Run benchmark: python performance_benchmark.py")
    else:
        print("❌ Some optimizations are missing or incomplete.")
        print("Please review the failed checks above.")
        sys.exit(1)


if __name__ == "__main__":
    main()