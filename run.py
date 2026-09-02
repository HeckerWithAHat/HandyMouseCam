"""
Main entry point for HandyMouseCam application.
Run this script to start the server.
"""

import sys
import os
import asyncio
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app import run_server

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("""
    ╔════════════════════════════════════════╗
    ║   HandyMouseCam - ItalicOne Display    ║
    ║   Hand Gesture Mouse Control System    ║
    ╚════════════════════════════════════════╝
    """)
    
    run_server()
