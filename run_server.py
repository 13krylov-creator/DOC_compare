# -*- coding: utf-8 -*-
import os
import sys
import subprocess

# Get the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, 'backend')

# Change to backend directory
os.chdir(backend_dir)

# Run the server
subprocess.run([sys.executable, 'main.py'])
