from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
import yt_dlp
import os
import tempfile
import io
import threading
from urllib.parse import urlparse, parse_qs, urlunparse
import shutil
from pathlib import Path
import uuid

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

# --- Forms ---
class DownloadForm(FlaskForm):
    link = StringField('YouTube Video URL', validators=[DataRequired(), URL()])
    submit = SubmitField('Download')

# --- Utility: Clean YouTube URL ---
def clean_youtube_url(url):
    """
    Remove playlist/radio parameters (&list=... &start_radio=... &index=... etc) from a YouTube URL.
    Returns the cleaned URL for a single video.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # Only keep 'v' (video id) and 't' (timestamp) if present
    keep_keys = {'v', 't'}
    new_qs = {k: v for k, v in qs.items() if k in keep_keys}
    new_query = '&'.join(f"{k}={v[0]}" for k, v in new_qs.items())
    cleaned = parsed._replace(query=new_query)
    return urlunparse(cleaned)

# --- Progress State Management ---
progress_data = {'percent': 0, 'status': 'idle'}
progress_lock = threading.Lock()
cancel_download_flag = {'cancel': False}

# --- Progress Reset ---
def reset_progress():
    with progress_lock:
        progress_data['percent'] = 0
        progress_data['status'] = 'idle'
        cancel_download_flag['cancel'] = False

# --- Main Page & Download Handler ---
@app.route('/', methods=['GET', 'POST'])
def index():
    form = DownloadForm()
    download_url = None
    filename = None
    video_info = None
    file_bytes = None
    if request.method == 'POST':
        reset_progress()  # Reset progress and cancel flag at the start
        link = form.link.data
        link = clean_youtube_url(link)  # Clean the URL before processing
        format_choice = request.form.get('format', 'best')
        
        if not link:
            flash("Please enter a YouTube link.", 'danger')
        else:
            try:
                # Use bypass options for initial video info extraction
                bypass_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extractor_args': {
                        'youtube': {
                            'skip': ['dash', 'hls'],
                            'player_skip': ['configs'],
                        }
                    },
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                    },
                    'sleep_interval': 1,
                    'retries': 2,
                }
                
                with yt_dlp.YoutubeDL(bypass_opts) as ydl:
                    info = ydl.extract_info(link, download=False)
                    video_info = {
                        'title': info.get('title'),
                        'thumbnail': info.get('thumbnail'),
                        'duration': info.get('duration'),
                    }
                global _in_memory_files
                try:
                    info, filename, file_bytes = download_youtube_video_to_memory(link, format_choice)
                except Exception as e:
                    err_msg = str(e)
                    if any(x in err_msg.lower() for x in [
                        'cookies', 'sign in', 'age-restricted', 'login', 'account', 'private', 'This video is only available', 'This video is not available', 'confirm your age', 'bot']):
                        flash("🔄 Video detected as restricted. Trying advanced bypass methods...", 'warning')
                        # Try again with more aggressive bypass methods
                        try:
                            info, filename, file_bytes = download_youtube_video_to_memory(link, format_choice, use_aggressive_bypass=True)
                            flash("✅ Successfully bypassed restrictions!", 'success')
                        except Exception as e2:
                            flash(f"❌ Unable to download this video. It may be heavily restricted: {str(e2)}", 'danger')
                            return render_template('index.html', form=form, download_url=None, filename=None, video_info=video_info)
                    else:
                        flash(f"Error: {err_msg}", 'danger')
                        return render_template('index.html', form=form, download_url=None, filename=None, video_info=video_info)
                    
                _in_memory_files[filename] = file_bytes
                download_url = url_for('download_file', filename=filename)
                download_links = {'best': None, 'video': None, 'audio': None}
                download_links[format_choice] = download_url
                video_info['download_links'] = download_links
                if filename:
                    video_info['auto_download_url'] = download_url
            except Exception as e:
                flash(f"Error: {str(e)}", 'danger')
    return render_template('index.html', form=form, download_url=download_url, filename=filename, video_info=video_info)

# --- In-Memory File Store ---
_in_memory_files = {}

# --- Download File Endpoint ---
@app.route('/downloads/<filename>')
def download_file(filename):
    # Serve file from memory
    file_bytes = _in_memory_files.get(filename)
    if file_bytes is None:
        flash("File not found or expired.", 'danger')
        return redirect(url_for('index'))
    return send_file(io.BytesIO(file_bytes), as_attachment=True, download_name=filename)

# --- Progress API ---
@app.route('/progress')
def get_progress():
    with progress_lock:
        return jsonify(progress_data)

# --- Cancel Download API ---
@app.route('/cancel_download', methods=['POST'])
def cancel_download():
    with progress_lock:
        cancel_download_flag['cancel'] = True
        progress_data['status'] = 'cancelled'
    return jsonify({'status': 'cancelled'})

# --- Clear Form API ---
@app.route('/clear_form', methods=['POST'])
def clear_form():
    reset_progress()
    # Clear in-memory files to free up memory
    global _in_memory_files
    _in_memory_files.clear()
    return redirect(url_for('index'))

# --- yt-dlp Progress Hook ---
def ytdlp_progress_hook(d):
    with progress_lock:
        if cancel_download_flag['cancel']:
            progress_data['status'] = 'cancelled'
            raise Exception('Download cancelled by user')
        # DEBUG: Print every progress event to the console
        print('YTDLP PROGRESS EVENT:', d)
        # Always set status to downloading if not finished/error/cancelled
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if not total and 'fragment_index' in d and 'fragment_count' in d and d['fragment_count']:
                total = d['fragment_count']
                downloaded = d['fragment_index']
            if total and downloaded:
                percent = float(downloaded) / float(total) * 100
                percent = max(0, min(percent, 100))
                progress_data['percent'] = percent
            elif downloaded:
                progress_data['percent'] = 10
            else:
                progress_data['percent'] = 0
            progress_data['status'] = 'downloading'
        elif d['status'] == 'finished':
            progress_data['percent'] = 100
            progress_data['status'] = 'finished'
        elif d['status'] == 'error':
            progress_data['status'] = 'error'
        else:
            progress_data['percent'] = 0
            progress_data['status'] = 'downloading'
        import sys
        sys.stdout.flush()
        sys.stderr.flush()

# --- Download Logic ---
def download_youtube_video_to_memory(link, format_choice='best', use_aggressive_bypass=False):
    import io
    import tempfile
    from yt_dlp.utils import DownloadError
    from flask import current_app
    import platform
    import time
    import random

    # Determine the temp directory for serverless (Vercel only allows /tmp)
    downloads_dir = '/tmp'

    def get_bypass_options(aggressive=False):
        """Get bypass options for yt-dlp"""
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        bypass_opts = {
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'] if not aggressive else ['dash'],
                    'player_skip': ['configs'] if not aggressive else [],
                    'player_client': ['android', 'web'] if aggressive else ['web'],
                }
            },
            'http_headers': base_headers,
            'retries': 5 if aggressive else 3,
            'fragment_retries': 5 if aggressive else 3,
            'sleep_interval': 1,
            'max_sleep_interval': 3 if aggressive else 5,
            'prefer_ipv6': False,
            'no_check_certificate': True,
            'ignoreerrors': False,
            'socket_timeout': 30,
        }
        
        if aggressive:
            # More aggressive bypass options
            bypass_opts.update({
                'format_sort': ['res:720', 'ext:mp4:m4a'],
                'extract_flat': False,
                'youtube_include_dash_manifest': False,
            })
            
        return bypass_opts

    # Use a temp file for yt_dlp output
    with tempfile.NamedTemporaryFile(suffix='.tmp', delete=True) as tmpfile:
        ydl_opts = {}
        common_opts = {
            'playlist_items': '1',
            'overwrites': True,  # Always overwrite existing files
            'nopart': True,      # Do not use .part files
            'noprogress': True,  # Do not use .progress files
        }
        
        # Get bypass options
        bypass_options = get_bypass_options(use_aggressive_bypass)
        
        if format_choice == 'audio':
            # Output template to Downloads folder with unique suffix and .mp3 extension
            unique_id = uuid.uuid4().hex[:8]
            outtmpl = os.path.join(downloads_dir, f'%(title)s_{unique_id}.%(ext)s')
            ydl_opts = {
                'outtmpl': outtmpl,
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'merge_output_format': None,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'progress_hooks': [ytdlp_progress_hook],
                'logtostderr': False,
                'force_overwrites': True,
                'postprocessor_hooks': [],
                **common_opts,
                **bypass_options
            }
        elif format_choice == 'video':
            # Output template to Downloads folder with unique suffix
            unique_id = uuid.uuid4().hex[:8]
            outtmpl = os.path.join(downloads_dir, f'%(title)s_{unique_id}.mp4')
            ydl_opts = {
                'outtmpl': outtmpl,
                'format': 'bestvideo[ext=mp4]/bestvideo/best',  # Only video, no audio
                'merge_output_format': 'mp4',
                # Remove postprocessors to avoid merging audio
                'postprocessors': [],
                'quiet': True,
                'progress_hooks': [ytdlp_progress_hook],
                'logtostderr': False,
                'force_overwrites': True,
                'postprocessor_hooks': [],
                **common_opts,
                **bypass_options
            }
        else:  # best (video+audio)
            unique_id = uuid.uuid4().hex[:8]
            outtmpl = os.path.join(downloads_dir, f'%(title)s_{unique_id}.mp4')
            ydl_opts = {
                'outtmpl': outtmpl,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'quiet': True,
                'progress_hooks': [ytdlp_progress_hook],
                'logtostderr': False,
                'force_overwrites': True,
                'postprocessor_hooks': [],
                **common_opts,
                **bypass_options
            }
        with progress_lock:
            progress_data['percent'] = 0
            progress_data['status'] = 'downloading'
        
        filename = None
        info = None
        
        try:
            # Always extract the first entry's URL if playlist/radio, then re-extract and download for that URL
            bypass_extract_opts = {
                'quiet': True,
                **get_bypass_options(use_aggressive_bypass)
            }
            
            with yt_dlp.YoutubeDL(bypass_extract_opts) as ydl:
                info_dict = ydl.extract_info(link, download=False)
                if info_dict.get('_type') == 'playlist' and info_dict.get('entries'):
                    first_entry = next((e for e in info_dict['entries'] if e), None)
                    if first_entry:
                        link = first_entry.get('webpage_url') or first_entry.get('url')
                        info_dict = ydl.extract_info(link, download=False)
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                filename = ydl.prepare_filename(info)
                
                # Handle different formats
                if format_choice == 'audio':
                    # Find the actual mp3 file (yt-dlp may output .m4a first, then .mp3 after postprocessing)
                    base, _ = os.path.splitext(filename)
                    mp3_filename = base + '.mp3'
                    if os.path.exists(mp3_filename):
                        filename = mp3_filename
                else:
                    # For video formats, ensure .mp4 extension
                    filename = os.path.splitext(filename)[0] + '.mp4'
                
                # Read the file
                with open(filename, 'rb') as f:
                    file_bytes = f.read()
                    
            with progress_lock:
                progress_data['percent'] = 100
                progress_data['status'] = 'finished'
                
            return info, os.path.basename(filename), file_bytes
            
        except DownloadError as e:
            with progress_lock:
                progress_data['status'] = 'error'
            print(f"yt-dlp DownloadError: {e}")
            raise e
        except Exception as e:
            with progress_lock:
                progress_data['status'] = 'error'
            print(f"yt-dlp Exception: {e}")
            raise e

# --- Main Entrypoint ---
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5050)
