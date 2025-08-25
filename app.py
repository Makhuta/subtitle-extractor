import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
import json
from io import BytesIO
import tempfile
import uuid
from video_processor import VideoProcessor
from subtitle_processor import SubtitleProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configuration
MEDIA_PATH = os.environ.get("MEDIA_PATH", "/mnt/media")
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
ALLOWED_SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass', '.ssa'}

video_processor = VideoProcessor()
subtitle_processor = SubtitleProcessor()

@app.route('/')
def index():
    """Main page with file browser"""
    try:
        current_path = request.args.get('path', '')
        full_path = os.path.join(MEDIA_PATH, current_path.lstrip('/'))
        
        # Security check - ensure we don't go outside MEDIA_PATH
        if not os.path.abspath(full_path).startswith(os.path.abspath(MEDIA_PATH)):
            flash("Invalid path", "error")
            return redirect(url_for('index'))
        
        if not os.path.exists(full_path):
            flash("Path does not exist", "error")
            return redirect(url_for('index'))
        
        items = []
        if os.path.isdir(full_path):
            try:
                for item in sorted(os.listdir(full_path)):
                    item_path = os.path.join(full_path, item)
                    relative_path = os.path.relpath(item_path, MEDIA_PATH)
                    
                    if os.path.isdir(item_path):
                        items.append({
                            'name': item,
                            'type': 'directory',
                            'path': relative_path
                        })
                    else:
                        _, ext = os.path.splitext(item.lower())
                        if ext in ALLOWED_VIDEO_EXTENSIONS:
                            items.append({
                                'name': item,
                                'type': 'video',
                                'path': relative_path,
                                'size': os.path.getsize(item_path)
                            })
            except PermissionError:
                flash("Permission denied accessing directory", "error")
                return redirect(url_for('index'))
        
        # Handle parent directory navigation
        parent_path = ''
        if current_path:
            parent_path = os.path.dirname(current_path.rstrip('/'))
        
        return render_template('index.html', 
                             items=items, 
                             current_path=current_path,
                             parent_path=parent_path)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash(f"Error loading directory: {str(e)}", "error")
        return render_template('index.html', items=[], current_path='', parent_path='')

@app.route('/video/<path:video_path>')
def video_details(video_path):
    """Video details page with subtitle extraction"""
    try:
        full_path = os.path.join(MEDIA_PATH, video_path.lstrip('/'))
        
        # Security check
        if not os.path.abspath(full_path).startswith(os.path.abspath(MEDIA_PATH)):
            flash("Invalid video path", "error")
            return redirect(url_for('index'))
        
        if not os.path.exists(full_path):
            flash("Video file not found", "error")
            return redirect(url_for('index'))
        
        # Extract subtitle tracks
        subtitle_tracks = video_processor.get_subtitle_tracks(full_path)
        
        return render_template('video_details.html', 
                             video_path=video_path,
                             video_name=os.path.basename(full_path),
                             subtitle_tracks=subtitle_tracks)
    except Exception as e:
        logger.error(f"Error in video_details route: {str(e)}")
        flash(f"Error processing video: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/api/extract_subtitle', methods=['POST'])
def extract_subtitle():
    """Extract subtitle from video file"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        track_index = data.get('track_index')
        
        if not video_path or track_index is None:
            return jsonify({'error': 'Missing video_path or track_index'}), 400
        
        full_path = os.path.join(MEDIA_PATH, video_path.lstrip('/'))
        
        # Security check
        if not os.path.abspath(full_path).startswith(os.path.abspath(MEDIA_PATH)):
            return jsonify({'error': 'Invalid video path'}), 400
        
        # Extract subtitle content
        subtitle_content = video_processor.extract_subtitle(full_path, track_index)
        
        if not subtitle_content:
            return jsonify({'error': 'Failed to extract subtitle'}), 500
        
        # Parse subtitle for preview
        parsed_subtitle = subtitle_processor.parse_ass_content(subtitle_content)
        
        # Store subtitle content in temporary file instead of session
        temp_id = str(uuid.uuid4())
        temp_file_path = os.path.join(tempfile.gettempdir(), f"subtitle_{temp_id}.ass")
        
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(subtitle_content)
        
        # Store only the temp file reference in session
        session['subtitle_temp_file'] = temp_file_path
        session['video_path'] = video_path
        session['track_index'] = track_index
        
        return jsonify({
            'success': True,
            'content': subtitle_content[:1000] + '...' if len(subtitle_content) > 1000 else subtitle_content,
            'lines_count': len(parsed_subtitle),
            'preview': parsed_subtitle[:10]  # First 10 lines for preview
        })
        
    except Exception as e:
        logger.error(f"Error extracting subtitle: {str(e)}")
        return jsonify({'error': f'Failed to extract subtitle: {str(e)}'}), 500

@app.route('/api/get_subtitle_preview')
def get_subtitle_preview():
    """Get subtitle preview data for inline display"""
    try:
        if 'subtitle_temp_file' not in session:
            return jsonify({'error': 'No subtitle data found'}), 400
        
        # Read subtitle content from temp file
        temp_file_path = session['subtitle_temp_file']
        
        if not os.path.exists(temp_file_path):
            return jsonify({'error': 'Subtitle data expired'}), 400
        
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            extracted_content = f.read()
        
        # Parse the extracted subtitle
        parsed_subtitle = subtitle_processor.parse_ass_content(extracted_content)
        
        # Show 50-75 lines preview
        preview_lines = parsed_subtitle[:75]
        
        return jsonify({
            'success': True,
            'lines': preview_lines,
            'total_lines': len(parsed_subtitle)
        })
        
    except Exception as e:
        logger.error(f"Error getting subtitle preview: {str(e)}")
        return jsonify({'error': f'Failed to get preview: {str(e)}'}), 500




@app.route('/api/download_subtitle')
def download_subtitle():
    """Generate and download final subtitle file"""
    try:
        if 'subtitle_temp_file' not in session:
            flash("No subtitle data found", "error")
            return redirect(url_for('index'))
        
        # Read subtitle content from temp file
        temp_file_path = session['subtitle_temp_file']
        
        if not os.path.exists(temp_file_path):
            flash("Subtitle data expired. Please extract again.", "error")
            return redirect(url_for('index'))
        
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Create file-like object for download
        output = BytesIO()
        output.write(original_content.encode('utf-8'))
        output.seek(0)
        
        # Generate filename
        video_path = session.get('video_path', 'subtitle')
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        filename = f"{video_name}_extracted.ass"
        
        # Clean up temp file after successful download preparation
        try:
            os.remove(temp_file_path)
            session.pop('subtitle_temp_file', None)
        except:
            pass  # Don't fail download if cleanup fails
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Error downloading subtitle: {str(e)}")
        flash(f"Error generating download: {str(e)}", "error")
        return redirect(url_for('subtitle_preview'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
