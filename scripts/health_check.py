#!/usr/bin/env python3
#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: FiniA Health Check Script
#
"""
FiniA Health Check Script
Monitors the health of FiniA services (API & Database)
"""

import subprocess
import json
import sys
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError
import socket

class HealthChecker:
    def __init__(self, api_url="http://localhost:8000", db_host="localhost", db_port=3306):
        self.api_url = api_url
        self.db_host = db_host
        self.db_port = db_port
        self.results = {}
        
    def check_api(self):
        """Check if API is responding"""
        print("🔍 Checking API health...")
        try:
            response = urlopen(f"{self.api_url}/api/docs", timeout=5)
            if response.status == 200:
                self.results['api'] = {'status': 'healthy', 'code': 200}
                print("✅ API is healthy")
                return True
            else:
                self.results['api'] = {'status': 'unhealthy', 'code': response.status}
                print(f"❌ API returned status {response.status}")
                return False
        except URLError as e:
            self.results['api'] = {'status': 'unreachable', 'error': str(e)}
            print(f"❌ API is unreachable: {e}")
            return False
        except Exception as e:
            self.results['api'] = {'status': 'error', 'error': str(e)}
            print(f"❌ Error checking API: {e}")
            return False
    
    def check_database(self):
        """Check if database is responding"""
        print("🔍 Checking Database health...")
        try:
            sock = socket.create_connection((self.db_host, self.db_port), timeout=5)
            sock.close()
            self.results['database'] = {'status': 'reachable', 'port': self.db_port}
            print("✅ Database is reachable")
            return True
        except socket.timeout:
            self.results['database'] = {'status': 'timeout', 'port': self.db_port}
            print(f"❌ Database connection timeout")
            return False
        except socket.error as e:
            self.results['database'] = {'status': 'unreachable', 'error': str(e)}
            print(f"❌ Database is unreachable: {e}")
            return False
    
    def check_docker_containers(self):
        """Check Docker container status"""
        print("🔍 Checking Docker containers...")
        try:
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                containers = json.loads(result.stdout) if result.stdout.strip() else []
                self.results['containers'] = {
                    'status': 'available',
                    'count': len(containers),
                    'containers': containers
                }
                print(f"✅ Found {len(containers)} containers")
                return True
            else:
                self.results['containers'] = {
                    'status': 'docker_error',
                    'error': result.stderr
                }
                print("❌ Docker Compose error")
                return False
        except Exception as e:
            self.results['containers'] = {'status': 'error', 'error': str(e)}
            print(f"❌ Error checking containers: {e}")
            return False
    
    def get_summary(self):
        """Generate health check summary"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'services': self.results
        }
        
        all_healthy = all(
            result.get('status') in ['healthy', 'reachable', 'available'] 
            for result in self.results.values()
        )
        
        summary['overall'] = 'healthy' if all_healthy else 'unhealthy'
        return summary
    
    def print_report(self):
        """Print formatted health report"""
        summary = self.get_summary()
        
        print("\n" + "="*50)
        print("FiniA Health Check Report")
        print("="*50)
        print(f"Timestamp: {summary['timestamp']}")
        print(f"Overall Status: {summary['overall'].upper()}")
        print("-"*50)
        
        for service, status in self.results.items():
            health = status.get('status', 'unknown')
            symbol = "✅" if health in ['healthy', 'reachable', 'available'] else "❌"
            print(f"{symbol} {service.upper()}: {health}")
            if 'error' in status:
                print(f"   Error: {status['error']}")
        
        print("="*50)
        return summary['overall'] == 'healthy'

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='FiniA Health Check')
    parser.add_argument('--api-url', default='http://localhost:8000', 
                       help='API URL (default: http://localhost:8000)')
    parser.add_argument('--db-host', default='localhost',
                       help='Database host (default: localhost)')
    parser.add_argument('--db-port', type=int, default=3306,
                       help='Database port (default: 3306)')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')
    
    args = parser.parse_args()
    
    checker = HealthChecker(
        api_url=args.api_url,
        db_host=args.db_host,
        db_port=args.db_port
    )
    
    # Run checks
    checker.check_docker_containers()
    checker.check_api()
    checker.check_database()
    
    # Output results
    if args.json:
        print(json.dumps(checker.get_summary(), indent=2))
    else:
        is_healthy = checker.print_report()
        sys.exit(0 if is_healthy else 1)

if __name__ == '__main__':
    main()
