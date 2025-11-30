#!/usr/bin/env python3
"""
OpticsERP Configuration Validation Script

Validates system prerequisites, configuration files, and environment
before deployment.

Usage:
    python scripts/validate_config.py

Exit codes:
    0 - All checks passed
    1 - One or more checks failed

Last Updated: 2025-11-30
"""

import os
import sys
import socket
import subprocess
from pathlib import Path
from typing import List, Tuple


# ANSI colors
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color


def log_info(msg: str):
    """Print info message"""
    print(f"{GREEN}[INFO]{NC} {msg}")


def log_warn(msg: str):
    """Print warning message"""
    print(f"{YELLOW}[WARN]{NC} {msg}")


def log_error(msg: str):
    """Print error message"""
    print(f"{RED}[ERROR]{NC} {msg}")


def check_docker() -> bool:
    """Check if Docker is installed and running"""
    print("\n=== Docker ===")

    # Check Docker command
    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        log_info(f"Docker installed: {version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("Docker is not installed")
        log_error("Install with: curl -fsSL https://get.docker.com | sh")
        return False

    # Check Docker service
    try:
        result = subprocess.run(
            ['docker', 'ps'],
            capture_output=True,
            text=True,
            check=True
        )
        log_info("Docker service is running")
    except subprocess.CalledProcessError:
        log_error("Docker service is not running")
        log_error("Start with: sudo systemctl start docker")
        return False

    return True


def check_docker_compose() -> bool:
    """Check if Docker Compose is installed"""
    print("\n=== Docker Compose ===")

    try:
        result = subprocess.run(
            ['docker-compose', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        log_info(f"Docker Compose installed: {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("Docker Compose is not installed")
        log_error("Install with prep_server.sh script")
        return False


def check_env_file() -> bool:
    """Check if .env file exists and has required variables"""
    print("\n=== Environment File ===")

    env_file = Path('.env')

    if not env_file.exists():
        log_error(".env file not found")
        log_error("Create it with: cp .env.example .env")
        log_error("Then edit .env with your configuration")
        return False

    log_info(".env file exists")

    # Required variables
    required_vars = [
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'ODOO_ADMIN_PASSWORD',
        'KKT_OFD_API_URL',
        'KKT_OFD_API_TOKEN',
    ]

    # Read .env file
    with open(env_file) as f:
        content = f.read()

    # Check for required variables
    missing = []
    for var in required_vars:
        if var not in content:
            missing.append(var)
        # Check if not using example values
        elif f"{var}=Change" in content or f"{var}=Your" in content or f"{var}=Admin" in content:
            log_warn(f"{var} still has default/example value")

    if missing:
        log_error(f"Missing required variables: {', '.join(missing)}")
        return False

    log_info("All required environment variables present")
    return True


def check_ports() -> bool:
    """Check if required ports are available"""
    print("\n=== Port Availability ===")

    ports = {
        8069: 'Odoo Web',
        8000: 'KKT Adapter',
        5432: 'PostgreSQL',
        6379: 'Redis',
        5555: 'Celery Flower',
    }

    all_available = True

    for port, service in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result == 0:
            log_warn(f"Port {port} ({service}) is already in use")
            all_available = False
        else:
            log_info(f"Port {port} ({service}) is available")

    if not all_available:
        log_warn("Some ports are in use. Stop conflicting services or use kill_port.py")

    return True  # Warnings, not failures


def check_disk_space() -> bool:
    """Check if sufficient disk space is available"""
    print("\n=== Disk Space ===")

    try:
        import shutil
        total, used, free = shutil.disk_usage("/")

        total_gb = total // (2**30)
        used_gb = used // (2**30)
        free_gb = free // (2**30)

        print(f"   Total: {total_gb} GB")
        print(f"   Used:  {used_gb} GB")
        print(f"   Free:  {free_gb} GB")

        if free_gb < 20:
            log_error(f"Insufficient disk space. Need at least 20 GB, have {free_gb} GB")
            return False
        elif free_gb < 50:
            log_warn(f"Low disk space. Recommended: 50 GB, have {free_gb} GB")
        else:
            log_info(f"Disk space OK: {free_gb} GB available")

        return True
    except Exception as e:
        log_warn(f"Could not check disk space: {e}")
        return True  # Non-critical


def check_git() -> bool:
    """Check if Git is installed"""
    print("\n=== Git ===")

    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        log_info(f"Git installed: {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("Git is not installed")
        log_error("Install with: sudo apt install git")
        return False


def check_repository() -> bool:
    """Check if we're in OpticsERP repository"""
    print("\n=== Repository ===")

    if not Path('.git').exists():
        log_warn("Not in a git repository")
        return True  # Warning, not failure

    if not Path('docker-compose.yml').exists():
        log_error("docker-compose.yml not found")
        log_error("Are you in the OpticsERP root directory?")
        return False

    log_info("OpticsERP repository detected")

    # Check for addons directory
    if Path('addons').exists():
        log_info("Custom addons directory found")
    else:
        log_warn("Custom addons directory not found")

    return True


def check_python_version() -> bool:
    """Check Python version"""
    print("\n=== Python Version ===")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    print(f"   Python version: {version_str}")

    if version.major < 3 or (version.major == 3 and version.minor < 9):
        log_error(f"Python 3.9+ required, have {version_str}")
        return False

    log_info(f"Python version OK: {version_str}")
    return True


def print_summary(results: List[Tuple[str, bool]]):
    """Print summary of all checks"""
    print("\n" + "=" * 50)
    print("  Validation Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = f"{GREEN}✅ PASS{NC}" if result else f"{RED}❌ FAIL{NC}"
        print(f"{status} - {check_name}")

    print("=" * 50)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print(f"\n{GREEN}✅ All checks passed! System is ready for deployment.{NC}")
        print("\nNext steps:")
        print("1. Build containers: docker-compose build --no-cache")
        print("2. Start services: docker-compose up -d")
        print("3. Initialize database: See docs/installation/02_installation_steps.md")
        return True
    else:
        print(f"\n{RED}❌ Some checks failed. Fix issues before deployment.{NC}")
        print("\nFor help, see:")
        print("- docs/installation/02_installation_steps.md")
        print("- docs/installation/05_troubleshooting.md")
        return False


def main():
    """Main validation routine"""
    print("=" * 50)
    print("  OpticsERP Configuration Validation")
    print("=" * 50)

    # Run all checks
    checks = [
        ("Python Version", check_python_version()),
        ("Docker", check_docker()),
        ("Docker Compose", check_docker_compose()),
        ("Git", check_git()),
        ("Repository", check_repository()),
        ("Environment File", check_env_file()),
        ("Port Availability", check_ports()),
        ("Disk Space", check_disk_space()),
    ]

    # Print summary
    all_passed = print_summary(checks)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
