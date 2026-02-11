#!/usr/bin/env python3
"""
Chris Effect - Inventory System
Main entry point for the desktop application
Run this file to start the inventory management system.
"""

import os
import sys

# Add the current directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Import the CE module which contains the Tkinter application
    import ttkbootstrap as ttk
    from CE import LoginWindow, InventoryApp
    
    # Create the root window
    root = ttk.Window(themename="cyborg")
    root.withdraw()  # Hide while initializing
    
    # Define the login callback
    def launch_app(user, role):
        root.deiconify()
        app = InventoryApp(root, user, role)
    
    # Create and display the login window
    login_win = LoginWindow(root, launch_app)
    
    # Start the main event loop
    root.mainloop()
