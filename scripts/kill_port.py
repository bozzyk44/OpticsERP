#!/usr/bin/env python
"""
Kill Process on Port

Utility script to kill processes occupying specific ports.
This ensures standard ports are always available for services.

Author: AI Agent
Created: 2025-10-08
"""

import sys
import argparse
import psutil


def kill_process_on_port(port: int, force: bool = False) -> bool:
    """
    Kill process listening on specified port

    Args:
        port: Port number (1-65535)
        force: Force kill (SIGKILL) instead of graceful termination

    Returns:
        True if process was killed, False if no process found
    """
    killed = False

    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            connections = proc.connections()
            for conn in connections:
                if conn.laddr.port == port:
                    print(f"Found process: {proc.info['name']} (PID: {proc.info['pid']}) on port {port}")

                    if force:
                        proc.kill()  # SIGKILL
                        print(f"✅ Force killed process {proc.info['pid']}")
                    else:
                        proc.terminate()  # SIGTERM
                        print(f"✅ Terminated process {proc.info['pid']}")

                    killed = True
                    break

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not killed:
        print(f"ℹ️  No process found on port {port}")

    return killed


def main():
    parser = argparse.ArgumentParser(
        description="Kill process on specified port",
        epilog="Example: python scripts/kill_port.py 8000"
    )

    parser.add_argument(
        'port',
        type=int,
        help='Port number (1-65535)'
    )

    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force kill (SIGKILL) instead of graceful termination (SIGTERM)'
    )

    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Kill all standard OpticsERP service ports (8000, 8069, 5432, 6379)'
    )

    args = parser.parse_args()

    # Validate port range
    if not (1 <= args.port <= 65535):
        print(f"❌ Error: Port must be between 1 and 65535, got {args.port}")
        sys.exit(1)

    # Kill process on port
    if args.all:
        standard_ports = {
            8000: "KKT Adapter (FastAPI)",
            8069: "Odoo",
            5432: "PostgreSQL",
            6379: "Redis"
        }

        print("=== Killing all standard service ports ===")
        for port, service in standard_ports.items():
            print(f"\n{service} (port {port}):")
            kill_process_on_port(port, force=args.force)
    else:
        kill_process_on_port(args.port, force=args.force)


if __name__ == "__main__":
    main()
