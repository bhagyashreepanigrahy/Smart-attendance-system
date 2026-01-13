#!/usr/bin/env python3
"""
Flask Server Restart Script
Properly restarts the Flask server and clears Python module cache to ensure latest code is loaded.
"""
import os
import sys
import subprocess
import time
import signal
import psutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def kill_flask_processes():
    """Kill all existing Flask processes"""
    killed_processes = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if process is running Flask app
            cmdline = proc.info['cmdline']
            if cmdline and any('app.py' in str(cmd) or 'flask' in str(cmd).lower() for cmd in cmdline):
                logger.info(f"Killing Flask process PID: {proc.info['pid']}")
                proc.kill()
                killed_processes += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_processes > 0:
        logger.info(f"Killed {killed_processes} Flask process(es)")
        time.sleep(2)  # Give processes time to clean up
    else:
        logger.info("No Flask processes found to kill")
    
    return killed_processes

def clear_python_cache():
    """Clear Python bytecode cache files"""
    cache_dirs_removed = 0
    pyc_files_removed = 0
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk(current_dir):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                import shutil
                shutil.rmtree(pycache_path)
                cache_dirs_removed += 1
                logger.info(f"Removed cache directory: {pycache_path}")
            except Exception as e:
                logger.warning(f"Could not remove {pycache_path}: {e}")
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                    pyc_files_removed += 1
                    logger.info(f"Removed .pyc file: {pyc_path}")
                except Exception as e:
                    logger.warning(f"Could not remove {pyc_path}: {e}")
    
    logger.info(f"Cache cleanup complete: {cache_dirs_removed} __pycache__ dirs, {pyc_files_removed} .pyc files removed")

def restart_flask_server():
    """Restart the Flask server with fresh modules"""
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
    
    if not os.path.exists(app_path):
        logger.error(f"app.py not found at: {app_path}")
        return False
    
    try:
        logger.info("Starting Flask server...")
        
        # Start the Flask app
        env = os.environ.copy()
        env['FLASK_DEBUG'] = '1'
        env['FLASK_ENV'] = 'development'
        
        process = subprocess.Popen([
            sys.executable, 
            app_path
        ], 
        cwd=os.path.dirname(app_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
        )
        
        logger.info(f"Flask server started with PID: {process.pid}")
        
        # Monitor the process for a few seconds to ensure it starts properly
        time.sleep(3)
        
        if process.poll() is None:
            logger.info("✅ Flask server is running successfully!")
            logger.info("🌐 Access your app at: http://localhost:5000")
            logger.info("🛑 Press Ctrl+C to stop the server")
            
            # Stream output
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        print(line.rstrip())
            except KeyboardInterrupt:
                logger.info("Stopping server...")
                process.terminate()
                process.wait()
                logger.info("Server stopped.")
        else:
            logger.error("❌ Flask server failed to start")
            if process.stdout:
                output = process.stdout.read()
                logger.error(f"Error output: {output}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error starting Flask server: {e}")
        return False

def main():
    """Main restart function"""
    logger.info("🔄 Starting Flask server restart process...")
    
    # Step 1: Kill existing Flask processes
    logger.info("Step 1: Killing existing Flask processes...")
    kill_flask_processes()
    
    # Step 2: Clear Python cache
    logger.info("Step 2: Clearing Python cache...")
    clear_python_cache()
    
    # Step 3: Start Flask server
    logger.info("Step 3: Starting Flask server...")
    success = restart_flask_server()
    
    if success:
        logger.info("✅ Flask server restart completed successfully!")
    else:
        logger.error("❌ Flask server restart failed!")
        return 1
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Restart process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during restart: {e}")
        sys.exit(1)