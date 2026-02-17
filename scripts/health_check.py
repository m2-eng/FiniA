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
import logging
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError
import socket

logger = logging.getLogger("uvicorn.error")

class HealthChecker:
    def __init__(self, api_url="http://localhost:8000", db_host="localhost", db_port=3306):
        self.api_url = api_url
        self.db_host = db_host
        self.db_port = db_port
        self.results = {}
        
    def check_api(self):
        """Check if API is responding"""
        logger.info("Checking API health...")
        try:
            response = urlopen(f"{self.api_url}/api/docs", timeout=5)
            if response.status == 200:
                self.results['api'] = {'status': 'healthy', 'code': 200}
                logger.info("API is healthy")
                return True
            else:
                self.results['api'] = {'status': 'unhealthy', 'code': response.status}
                logger.error("API returned status %s", response.status)
                return False
        except URLError as e:
            self.results['api'] = {'status': 'unreachable', 'error': str(e)}
            logger.error("API is unreachable: %s", e)
            return False
        except Exception as e:
            self.results['api'] = {'status': 'error', 'error': str(e)}
            logger.error("Error checking API: %s", e)
            return False
    
    def check_database(self):
        """Check if database is responding"""
        logger.info("Checking database health...")
        try:
            sock = socket.create_connection((self.db_host, self.db_port), timeout=5)
            sock.close()
            self.results['database'] = {'status': 'reachable', 'port': self.db_port}
            logger.info("Database is reachable")
            return True
        except socket.timeout:
            self.results['database'] = {'status': 'timeout', 'port': self.db_port}
            logger.error("Database connection timeout")
            return False
        except socket.error as e:
            self.results['database'] = {'status': 'unreachable', 'error': str(e)}
            logger.error("Database is unreachable: %s", e)
            return False
    
    def check_docker_containers(self):
        """Check Docker container status"""
        logger.info("Checking Docker containers...")
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
                logger.info("Found %s containers", len(containers))
                return True
            else:
                self.results['containers'] = {
                    'status': 'docker_error',
                    'error': result.stderr
                }
                logger.error("Docker Compose error")
                return False
        except Exception as e:
            self.results['containers'] = {'status': 'error', 'error': str(e)}
            logger.error("Error checking containers: %s", e)
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
        
        logger.info("%s", "=" * 50)
        logger.info("FiniA Health Check Report")
        logger.info("%s", "=" * 50)
        logger.info("Timestamp: %s", summary["timestamp"])
        logger.info("Overall Status: %s", summary["overall"].upper())
        logger.info("%s", "-" * 50)
        
        for service, status in self.results.items():
            health = status.get('status', 'unknown')
            if health in ['healthy', 'reachable', 'available']:
                logger.info("%s: %s", service.upper(), health)
            else:
                logger.error("%s: %s", service.upper(), health)
            if 'error' in status:
                logger.error("Error: %s", status["error"])
        
        logger.info("%s", "=" * 50)
        return summary['overall'] == 'healthy'

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
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
        logger.info("%s", json.dumps(checker.get_summary(), indent=2))
    else:
        is_healthy = checker.print_report()
        sys.exit(0 if is_healthy else 1)

if __name__ == '__main__':
    main()
