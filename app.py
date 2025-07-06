from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
import yt_dlp
import os
import tkinter as tk
from tkinter import filedialog
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

# --- Folder Selection Endpoint (for desktop use) ---
@app.route('/choose_folder', methods=['POST'])
def choose_folder():
    # Use Tkinter to open a folder dialog
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select Download Folder")
    root.destroy()
    return jsonify({'folder': folder_selected})

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
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
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
                        'cookies', 'sign in', 'age-restricted', 'login', 'account', 'private', 'This video is only available', 'This video is not available', 'confirm your age']):
                        flash("This video requires you to be signed in to YouTube. <a href='https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp' target='_blank' style='color:#2563eb;text-decoration:underline;'>Learn how to download restricted videos</a>.", 'danger')
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
def download_youtube_video_to_memory(link, format_choice='best'):
    import io
    import tempfile
    from yt_dlp.utils import DownloadError
    from flask import current_app
    import platform

    # Determine the user's Downloads folder in a cross-platform way
    if platform.system() == 'Darwin':  # macOS
        downloads_dir = str(Path.home() / 'Downloads')
    elif platform.system() == 'Windows':
        downloads_dir = str(Path.home() / 'Downloads')
    else:  # Linux and others
        downloads_dir = str(Path.home() / 'Downloads')

    cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    # Use a temp file for yt_dlp output
    with tempfile.NamedTemporaryFile(suffix='.tmp', delete=True) as tmpfile:
        ydl_opts = {}
        common_opts = {
            'playlist_items': '1',
            'overwrites': True,  # Always overwrite existing files
            'nopart': True,      # Do not use .part files
            'noprogress': True,  # Do not use .progress files
        }
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
                'ffmpeg_location': '/opt/homebrew/bin/ffmpeg',
                'postprocessor_hooks': [],
                **common_opts
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
                'ffmpeg_location': '/opt/homebrew/bin/ffmpeg',
                'postprocessor_hooks': [],
                **common_opts
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
                'ffmpeg_location': '/opt/homebrew/bin/ffmpeg',
                'postprocessor_hooks': [],
                **common_opts
            }
        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
        with progress_lock:
            progress_data['percent'] = 0
            progress_data['status'] = 'downloading'
        filename = None
        info = None
        try:
            # Always extract the first entry's URL if playlist/radio, then re-extract and download for that URL
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info_dict = ydl.extract_info(link, download=False)
                if info_dict.get('_type') == 'playlist' and info_dict.get('entries'):
                    first_entry = next((e for e in info_dict['entries'] if e), None)
                    if first_entry:
                        link = first_entry.get('webpage_url') or first_entry.get('url')
                        info_dict = ydl.extract_info(link, download=False)
            if format_choice == 'audio':
                # Download directly to Downloads folder
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=True)
                    filename = ydl.prepare_filename(info)
                    # Find the actual mp3 file (yt-dlp may output .m4a first, then .mp3 after postprocessing)
                    base, _ = os.path.splitext(filename)
                    mp3_filename = base + '.mp3'
                    if os.path.exists(mp3_filename):
                        filename = mp3_filename
                    # Read the file from Downloads folder
                    with open(filename, 'rb') as f:
                        file_bytes = f.read()
            elif format_choice == 'video':
                # Download directly to Downloads folder
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=True)
                    filename = ydl.prepare_filename(info)
                    filename = os.path.splitext(filename)[0] + '.mp4'
                    # Remove any existing file before reading (safety)
                    if os.path.exists(filename):
                        pass  # File just created, so this is safe
                    # Read the file from Downloads folder
                    with open(filename, 'rb') as f:
                        file_bytes = f.read()
            else:
                # Download directly to Downloads folder
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=True)
                    filename = ydl.prepare_filename(info)
                    filename = os.path.splitext(filename)[0] + '.mp4'
                    # Remove any existing file before reading (safety)
                    if os.path.exists(filename):
                        pass  # File just created, so this is safe
                    # Read the file from Downloads folder
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
