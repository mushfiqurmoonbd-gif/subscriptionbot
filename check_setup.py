"""
Comprehensive Setup Check Script
Checks all configuration, dependencies, and setup status
Run: python check_setup.py
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists."""
    exists = Path(filepath).exists()
    status = "[OK]" if exists else "[MISSING]"
    print(f"{status} {description}: {filepath}")
    return exists

def check_env_variable(var_name, description, required=True):
    """Check if an environment variable is set."""
    value = os.environ.get(var_name)
    if value:
        # Mask sensitive values
        if 'KEY' in var_name or 'SECRET' in var_name or 'PASSWORD' in var_name or 'TOKEN' in var_name:
            display_value = value[:8] + "..." if len(value) > 8 else "***"
        else:
            display_value = value
        print(f"[OK] {description}: {display_value}")
        return True
    else:
        status = "[MISSING]" if required else "[OPTIONAL]"
        req_text = "(REQUIRED)" if required else "(optional)"
        print(f"{status} {description}: Not set {req_text}")
        return not required

def check_python_package(package_name):
    """Check if a Python package is installed."""
    try:
        __import__(package_name)
        print(f"[OK] {package_name}: Installed")
        return True
    except ImportError:
        print(f"[MISSING] {package_name}: Not installed")
        return False

def check_database():
    """Check if database file exists."""
    db_path = Path("instance/subscription_service.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"[OK] Database: {db_path} ({size} bytes)")
        return True
    else:
        print(f"[INFO] Database: {db_path} (will be created on first run)")
        return True  # Not an error, will be created automatically

def main():
    print("=" * 70)
    print("SUBSCRIPTION SERVICE - SETUP CHECK")
    print("=" * 70)
    
    all_checks = []
    
    # Check required files
    print("\n[FILE CHECK]")
    print("-" * 70)
    required_files = [
        ("app.py", "Main application"),
        ("config.py", "Configuration"),
        ("models.py", "Database models"),
        ("telegram_bot.py", "Telegram bot"),
        ("sms_sender.py", "SMS sender"),
        ("scheduler.py", "Message scheduler"),
        ("subscription_manager.py", "Stripe manager"),
        ("paypal_manager.py", "PayPal manager"),
        ("crypto_manager.py", "Crypto manager"),
        ("email_sms_gateways.py", "Email-SMS gateways"),
        ("requirements.txt", "Dependencies list"),
    ]
    
    for filepath, desc in required_files:
        all_checks.append(check_file_exists(filepath, desc))
    
    # Check database
    print("\n[DATABASE CHECK]")
    print("-" * 70)
    all_checks.append(check_database())
    
    # Check .env file
    print("\n[CONFIGURATION CHECK - .env file]")
    print("-" * 70)
    env_exists = Path(".env").exists()
    if env_exists:
        print("[OK] .env file: Found")
        # Load and check variables
        from dotenv import load_dotenv
        load_dotenv()
    else:
        print("[MISSING] .env file: Not found (REQUIRED)")
        print("   Create .env file with required configuration")
        all_checks.append(False)
    
    # Check required environment variables
    print("\n[ENVIRONMENT VARIABLES]")
    print("-" * 70)
    
    required_vars = [
        ("SECRET_KEY", "Secret key"),
        ("STRIPE_SECRET_KEY", "Stripe secret key"),
        ("STRIPE_PUBLISHABLE_KEY", "Stripe publishable key"),
        ("TELEGRAM_BOT_TOKEN", "Telegram bot token"),
    ]
    
    optional_vars = [
        ("STRIPE_WEBHOOK_SECRET", "Stripe webhook secret"),
        ("PAYPAL_CLIENT_ID", "PayPal client ID"),
        ("PAYPAL_CLIENT_SECRET", "PayPal client secret"),
        ("COINBASE_COMMERCE_API_KEY", "Coinbase Commerce API key"),
        ("SMTP_SERVER", "SMTP server"),
        ("SMTP_USERNAME", "SMTP username"),
        ("SMTP_PASSWORD", "SMTP password"),
        ("BASE_URL", "Base URL"),
    ]
    
    if env_exists:
        for var, desc in required_vars:
            all_checks.append(check_env_variable(var, desc, required=True))
        
        for var, desc in optional_vars:
            check_env_variable(var, desc, required=False)
    
    # Check Python packages
    print("\n[PYTHON PACKAGES]")
    print("-" * 70)
    
    required_packages = [
        "flask",
        "flask_sqlalchemy",
        "flask_cors",
        "stripe",
        "paypalrestsdk",
        "coinbase_commerce",
        "apscheduler",
        "telegram",
        "dotenv",
        "smtplib",
    ]
    
    for package in required_packages:
        # Handle different import names
        import_name = package
        if package == "flask_sqlalchemy":
            import_name = "flask_sqlalchemy"
        elif package == "flask_cors":
            import_name = "flask_cors"
        elif package == "coinbase_commerce":
            import_name = "coinbase_commerce"
        elif package == "telegram":
            import_name = "telegram"
        elif package == "dotenv":
            import_name = "dotenv"
        elif package == "smtplib":
            import_name = "smtplib"  # Built-in
        
        all_checks.append(check_python_package(import_name))
    
    # Check SMTP configuration (for message sending)
    print("\n[SMTP CONFIGURATION - for sending messages]")
    print("-" * 70)
    if env_exists:
        smtp_configured = (
            os.environ.get('SMTP_USERNAME') and 
            os.environ.get('SMTP_PASSWORD')
        )
        if smtp_configured:
            print("[OK] SMTP: Configured (can send messages)")
        else:
            print("[WARNING] SMTP: Not fully configured (messages won't be sent)")
            print("   Set SMTP_USERNAME and SMTP_PASSWORD in .env")
    
    # Summary
    print("\n" + "=" * 70)
    print("[SUMMARY]")
    print("=" * 70)
    
    passed = sum(all_checks)
    total = len(all_checks)
    
    if passed == total:
        print(f"[OK] All critical checks passed! ({passed}/{total})")
        print("\n[RUN] You can now run: python app.py")
    else:
        print(f"[WARNING] Some checks failed: {passed}/{total} passed")
        print("\n[ERROR] Please fix the issues above before running the application")
        print("\n[INFO] Quick fixes:")
        print("   1. Create .env file with required variables")
        print("   2. Install missing packages: pip install -r requirements.txt")
        print("   3. Check README.md for setup instructions")
    
    print("\n" + "=" * 70)
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error during check: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

