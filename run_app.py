# run_app.py
# This file properly starts the server with eventlet monkey patching

# ABSOLUTE FIRST LINE - before ANY other imports
import eventlet
eventlet.monkey_patch()

# Now import everything else
import os  # This was missing
import socket
import sys

# Now import the app
from app import app, socketio

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 FILE TRANSFER ROOM SERVER")
    print("="*60)
    
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 5000))
    
    # Check if port is available
    def check_port(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return True
            except:
                return False
    
    # Test the default port
    if not check_port(port):
        print(f"⚠️  Port {port} is in use. Trying alternative ports...")
        # Try alternative ports
        port_found = False
        for alt_port in [5001, 5002, 5003, 8080, 3000]:
            if check_port(alt_port):
                port = alt_port
                port_found = True
                print(f"✅ Using port {port}")
                break
        
        if not port_found:
            print("❌ No available ports found!")
            print("💡 Please close other applications and try again.")
            sys.exit(1)
    else:
        print(f"✅ Port {port} is available")
    
    print("\n📱 Access the application at:")
    print(f"   → http://127.0.0.1:{port}")
    print(f"   → http://localhost:{port}")
    
    # Try to get local IP for network access
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"   → http://{local_ip}:{port} (Network - for other devices)")
    except:
        pass
    
    print("\n" + "="*60)
    print("Press CTRL+C to stop the server")
    print("="*60 + "\n")
    
    try:
        socketio.run(
            app,
            host='0.0.0.0',  # Listen on all network interfaces
            port=port,
            debug=True,
            use_reloader=False,  # Important: prevents double execution
            log_output=False  # Reduce logging noise
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)