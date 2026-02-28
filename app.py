# 🟢 CRITICAL: This must be the FIRST lines of the file - before ANY other imports
import eventlet
eventlet.monkey_patch()

# Now import everything else
import os
import time
import threading
import sys
import socket
from pathlib import Path
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, make_response
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import zipfile
import io
import logging

# ────────────────────────────────────────────────
#  LOGGING CONFIGURATION (Reduce noise)
# ────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Suppress verbose logs from libraries
logging.getLogger('eventlet').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# ────────────────────────────────────────────────
#  APP & SOCKET.IO CONFIGURATION
# ────────────────────────────────────────────────

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your-secret-key-here-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload size

# 🟢 SocketIO Configuration - Minimal logging to reduce warnings
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,  # Disable SocketIO logging
    engineio_logger=False,  # Disable EngineIO logging
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=100 * 1024 * 1024  # 100MB buffer for large files
)

# Configuration
UPLOAD_FOLDER = "uploads"
ROOM_DURATION_MINS = 15

# Ensure directories exist with proper permissions
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path("static").mkdir(parents=True, exist_ok=True)
Path("templates").mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────
#  IN-MEMORY STORAGE & LOCKING
# ────────────────────────────────────────────────

room_store = {}
room_lock = threading.RLock()  # Reentrant lock for thread safety

# ────────────────────────────────────────────────
#  UTILITY FUNCTIONS
# ────────────────────────────────────────────────

def generate_code():
    """Generate a unique 6-digit code for the room."""
    with room_lock:
        while True:
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            if code not in room_store:
                return code

def get_human_size(bytes_size):
    """Convert bytes to human-readable format."""
    if bytes_size == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

def get_or_create_user():
    """Get user ID from cookie or create a new one."""
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = f"user_{int(time.time())}_{random.randint(1000, 9999)}"
    return user_id

def add_history(code, user, action):
    """Add an action to room history (Thread Safe)."""
    with room_lock:
        if code in room_store:
            room_store[code]["history"].append({
                "user": user,
                "action": action,
                "time": datetime.now().strftime("%H:%M:%S")
            })
            # Keep only last 50 history items to prevent memory bloat
            if len(room_store[code]["history"]) > 50:
                room_store[code]["history"] = room_store[code]["history"][-50:]

def cleanup_expired_rooms():
    """Background task to delete expired rooms and their files."""
    logger.info("🧹 Cleanup thread started")
    while True:
        try:
            eventlet.sleep(60)  # Check every minute
            now = datetime.now()
            expired_files = []
            expired_rooms = []
            
            # Identify expired items safely
            with room_lock:
                for code, data in list(room_store.items()):
                    if (now - data["timestamp"]) > timedelta(minutes=ROOM_DURATION_MINS):
                        expired_rooms.append(code)
                        for file_info in data["files"]:
                            expired_files.append(file_info["stored_name"])
                
                # Remove from memory
                for code in expired_rooms:
                    del room_store[code]

            # Delete files from disk (Outside lock to allow other operations)
            for filename in expired_files:
                try:
                    file_path = Path(UPLOAD_FOLDER) / filename
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Deleted expired file: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting file {filename}: {e}")
                    
            if expired_rooms:
                logger.info(f"🧹 Cleanup: Removed {len(expired_rooms)} expired rooms.")
                
        except Exception as e:
            logger.error(f"Error in cleanup thread: {e}")
            eventlet.sleep(60)  # Wait before retrying

def check_port_available(port, host='127.0.0.1'):
    """Check if a port is available on specific host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except socket.error:
            return False

# ────────────────────────────────────────────────
#  SOCKET.IO EVENTS
# ────────────────────────────────────────────────

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected")

@socketio.on('join')
def handle_join(data):
    code = data.get('code')
    with room_lock:
        exists = code in room_store

    if code and exists:
        join_room(code)
        logger.info(f"User joined room: {code}")
        emit('joined_room', {'code': code, 'success': True})
    else:
        logger.warning(f"User tried to join invalid room: {code}")
        emit('error', {'message': 'Room not found'})

@socketio.on('leave')
def handle_leave(data):
    code = data.get('code')
    if code:
        leave_room(code)
        logger.info(f"User left room: {code}")

# ────────────────────────────────────────────────
#  ROUTES
# ────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/create", methods=["POST"])
def create_room():
    code = generate_code()
    
    with room_lock:
        room_store[code] = {
            "timestamp": datetime.now(),
            "files": [],
            "history": []
        }
    
    user = get_or_create_user()
    add_history(code, user, "created room")
    logger.info(f"Room created: {code}")
    
    response = make_response(redirect(url_for('room_page', code=code)))
    response.set_cookie('user_id', user, max_age=60*60*24)
    return response

@app.route("/join", methods=["POST"])
def join_existing_room():
    code = request.form.get("code", "").strip()
    
    with room_lock:
        if code not in room_store:
            return render_template("index.html", error="Invalid or expired code")
    
    user = get_or_create_user()
    add_history(code, user, "joined room")
    logger.info(f"User joined room: {code}")
    
    response = make_response(redirect(url_for('room_page', code=code)))
    response.set_cookie('user_id', user, max_age=60*60*24)
    return response

@app.route("/j/<code>")
def join_via_link(code):
    """Handle Direct Join Links (QR Code)"""
    with room_lock:
        if code not in room_store:
            return render_template("index.html", error="Room expired or invalid")
    
    user = get_or_create_user()
    add_history(code, user, "joined via QR/Link")
    logger.info(f"User joined via link: {code}")
    
    response = make_response(redirect(url_for('room_page', code=code)))
    response.set_cookie('user_id', user, max_age=60*60*24)
    return response

@app.route("/room/<code>")
def room_page(code):
    with room_lock:
        if code not in room_store:
            return render_template("index.html", error="Room not found or expired")
        
        room_data = room_store[code]
        files = room_data["files"]
        history = room_data["history"]
        timestamp = room_data["timestamp"]

    user = get_or_create_user()
    
    now = datetime.now()
    elapsed = now - timestamp
    remaining = timedelta(minutes=ROOM_DURATION_MINS) - elapsed
    remaining_seconds = int(remaining.total_seconds())
    
    logger.info(f"Room page accessed: {code} by user {user}")
    
    return render_template("room.html",
                         code=code,
                         files=files,
                         history=history,
                         current_user=user,
                         remaining_seconds=max(0, remaining_seconds))

@app.route("/upload/<code>", methods=["POST"])
def upload_file(code):
    with room_lock:
        if code not in room_store:
            return redirect(url_for('index'))

    user = get_or_create_user()
    
    # Check if files were uploaded
    if 'file' not in request.files:
        logger.warning(f"No file part in upload request for room {code}")
        return redirect(url_for('room_page', code=code))
    
    files = request.files.getlist("file")
    
    # Filter out empty files
    files = [f for f in files if f and f.filename]
    
    if not files:
        logger.warning(f"No files selected for upload in room {code}")
        return redirect(url_for('room_page', code=code))
    
    uploaded_files = []
    processed_files_data = []
    
    # Process files
    for file in files:
        try:
            if file and file.filename:
                orig_name = file.filename
                # Secure the filename and ensure uniqueness
                safe_filename = secure_filename(orig_name)
                if not safe_filename:
                    safe_filename = "file_" + str(int(time.time()))
                
                stored_name = f"{code}_{int(time.time())}_{random.randint(1000,9999)}_{safe_filename}"
                path = Path(UPLOAD_FOLDER) / stored_name
                file.save(path)
                
                # Verify file was saved
                if path.exists():
                    file_size = path.stat().st_size
                    processed_files_data.append({
                        "original_name": orig_name,
                        "stored_name": stored_name,
                        "size": get_human_size(file_size),
                        "type": orig_name.split('.')[-1].upper() if '.' in orig_name else "FILE",
                        "sender": user
                    })
                    logger.info(f"File uploaded: {orig_name} ({file_size} bytes) to room {code}")
                else:
                    logger.error(f"Failed to save file: {orig_name}")
                    
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            continue

    # Update store safely
    with room_lock:
        if code in room_store:
            current_count = len(room_store[code]["files"])
            for i, f_data in enumerate(processed_files_data):
                f_data["index"] = current_count + i
                room_store[code]["files"].append(f_data)
                uploaded_files.append(f_data)
    
    if uploaded_files:
        add_history(code, user, f"sent {len(uploaded_files)} file(s)")
        # Notify all users in the room about new files
        socketio.emit('new_files', {
            'files': uploaded_files,
            'sender': user
        }, to=code)
        logger.info(f"Broadcasted {len(uploaded_files)} new files to room {code}")
            
    return redirect(url_for('room_page', code=code))

@app.route("/download/<code>/<int:index>")
def download_file(code, index):
    file_info = None
    
    with room_lock:
        if code in room_store and index < len(room_store[code]["files"]):
            file_info = room_store[code]["files"][index]
    
    if file_info:
        user = get_or_create_user()
        add_history(code, user, f"downloaded: {file_info['original_name']}")
        
        socketio.emit('file_downloaded', {
            'filename': file_info['original_name'],
            'user': user
        }, to=code)
        
        logger.info(f"File downloaded: {file_info['original_name']} from room {code}")
        
        return send_from_directory(
            UPLOAD_FOLDER, 
            file_info["stored_name"], 
            as_attachment=True, 
            download_name=file_info["original_name"]
        )
    
    logger.warning(f"File not found: room {code}, index {index}")
    return "File not found", 404

@app.route("/download_all/<code>")
def download_all(code):
    files_to_zip = []
    
    with room_lock:
        if code not in room_store:
            return "Room not found", 404
        # Create a shallow copy to use outside the lock
        files_to_zip = list(room_store[code]["files"])
    
    if not files_to_zip:
        return "No files to download", 404
    
    user = get_or_create_user()
    memory_file = io.BytesIO()
    
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in files_to_zip:
                file_path = Path(UPLOAD_FOLDER) / file_info["stored_name"]
                if file_path.exists():
                    zf.write(file_path, file_info["original_name"])
                    logger.info(f"Added {file_info['original_name']} to zip")
                else:
                    logger.warning(f"File missing when creating zip: {file_info['stored_name']}")
    except Exception as e:
        logger.error(f"Error creating zip: {e}")
        return f"Error creating zip: {str(e)}", 500
    
    memory_file.seek(0)
    add_history(code, user, "downloaded all files")
    logger.info(f"All files downloaded from room {code}")
    
    return (memory_file.getvalue(), 200, {
        'Content-Type': 'application/zip',
        'Content-Disposition': f'attachment; filename=files_{code}.zip'
    })

@app.route("/destroy/<code>", methods=["POST"])
def destroy_room(code):
    """Immediate Room Destruction (Exit & Delete)"""
    files_to_delete = []
    
    # Remove from memory safely
    with room_lock:
        if code in room_store:
            # Get list of files to delete from disk
            for file_info in room_store[code]["files"]:
                files_to_delete.append(file_info["stored_name"])
            
            # Delete room data from memory
            del room_store[code]
            logger.info(f"💥 Room {code} destroyed by user.")
    
    # Delete files from disk
    deleted_count = 0
    for filename in files_to_delete:
        try:
            file_path = Path(UPLOAD_FOLDER) / filename
            if file_path.exists():
                file_path.unlink()
                deleted_count += 1
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
    
    logger.info(f"Deleted {deleted_count} files from room {code}")

    # Notify everyone in the room to leave
    socketio.emit('room_destroyed', {}, to=code)
    
    # Redirect the user who clicked the button to home
    return redirect(url_for('index'))

@app.route("/health")
def health():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy", 
        "rooms": len(room_store),
        "uptime": "running"
    }), 200

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return render_template("index.html", error="File too large. Maximum size is 100MB."), 413

@app.errorhandler(404)
def not_found(e):
    return render_template("index.html", error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template("index.html", error="Internal server error. Please try again."), 500

# ────────────────────────────────────────────────
#  APP START (Modified to work with run_app.py)
# ────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("📁 FILE TRANSFER ROOM SERVER")
    print("="*60)
    print("\n⚠️  Please use 'run_app.py' to start the server")
    print("   This ensures proper eventlet monkey patching\n")
    print("   Run: python run_app.py")
    print("="*60 + "\n")