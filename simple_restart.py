#!/usr/bin/env python3
"""
Simple Flask Server Restart Script
Works without additional dependencies - just kills Python processes and restarts Flask.
"""
import os
import sys
import subprocess
import time
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def kill_python_processes():
    """Kill existing Python processes using taskkill (Windows)"""
    try:
        logger.info("🔪 Killing existing Python processes...")
        
        # Kill all python.exe processes
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                      capture_output=True, text=True)
        
        # Kill all pythonw.exe processes (Windows GUI)
        subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe'], 
                      capture_output=True, text=True)
        
        logger.info("✅ Python processes terminated")
        time.sleep(2)  # Give processes time to clean up
        
    except Exception as e:
        logger.warning(f"⚠️ Could not kill processes (this is usually OK): {e}")

def clear_python_cache():
    """Clear Python bytecode cache files"""
    logger.info("🧹 Clearing Python cache...")
    
    cache_cleaned = False
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk(current_dir):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(pycache_path)
                logger.info(f"✅ Removed: {pycache_path}")
                cache_cleaned = True
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {pycache_path}: {e}")
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                    logger.info(f"✅ Removed: {pyc_path}")
                    cache_cleaned = True
                except Exception as e:
                    logger.warning(f"⚠️ Could not remove {pyc_path}: {e}")
    
    if cache_cleaned:
        logger.info("✅ Python cache cleared")
    else:
        logger.info("ℹ️ No cache files found to clear")

def start_flask_server():
    """Start the Flask server"""
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
    
    if not os.path.exists(app_path):
        logger.error(f"❌ app.py not found at: {app_path}")
        return False
    
    try:
        logger.info("🚀 Starting Flask server...")
        
        # Set environment variables
        env = os.environ.copy()
        env['FLASK_DEBUG'] = '1'
        env['FLASK_ENV'] = 'development'
        env['PYTHONPATH'] = os.path.dirname(app_path)
        
        # Start in a new window so we can continue
        if os.name == 'nt':  # Windows
            cmd = [
                'cmd', '/c', 'start', 
                'Flask Server', 
                'cmd', '/k', 
                f'python "{app_path}"'
            ]
        else:  # Linux/Mac
            cmd = [sys.executable, app_path]
        
        subprocess.Popen(cmd, env=env, cwd=os.path.dirname(app_path))
        
        logger.info("✅ Flask server started in new window!")
        logger.info("🌐 Server should be available at: http://localhost:5000")
        logger.info("⏱️ Please wait a few seconds for the server to fully start...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error starting Flask server: {e}")
        return False

def main():
    """Main restart function"""
    print("🔄 Simple Flask Server Restart")
    print("=" * 50)
    
    # Step 1: Kill existing processes
    kill_python_processes()
    
    # Step 2: Clear cache
    clear_python_cache()
    
    # Step 3: Start Flask server
    success = start_flask_server()
    
    if success:
        print("\n✅ Server restart completed!")
        print("🌐 Visit: http://localhost:5000/online_attendance")
        print("⏱️ Wait a few seconds for the server to fully load")
    else:
        print("\n❌ Server restart failed!")
        print("🔧 Try running manually: python app.py")
    
    return success

if __name__ == '__main__':
    try:
        success = main()
        if success:
            print("\n✨ You can now close this window")
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print("\n👋 Restart cancelled by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        input("Press Enter to exit...")