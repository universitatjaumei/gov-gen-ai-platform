"""
Server core configuration.
"""
import os

# Environment setting
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Developer mode flag
# Allows auto-provisioning of test accounts and by-passing some strict security checks
IS_DEV_MODE = ENVIRONMENT == "development"
