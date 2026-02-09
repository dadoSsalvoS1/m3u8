#!/usr/bin/env python3
import sys
import os

# Add the src directory to the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

try:
    from ipfs_iptv.main import main
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you have installed the requirements using: pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    main()
