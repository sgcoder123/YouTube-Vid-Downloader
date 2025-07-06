from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
import yt_dlp
import os
import tkinter as tk
from tkinter import filedialog

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

class DownloadForm(FlaskForm):
    link = StringField('YouTube Video URL', validators=[DataRequired(), URL()])
    submit = SubmitField('Download')

@app.route('/choose_folder', methods=['POST'])
def choose_folder():
    # Use Tkinter to open a folder dialog
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select Download Folder")
    root.destroy()
    return jsonify({'folder': folder_selected})

@app.route('/', methods=['GET', 'POST'])
def index():
    form = DownloadForm()
    download_url = None
    filename = None
    video_info = None
    downloads = os.listdir(DOWNLOADS_DIR)
    downloads = [f for f in downloads if not f.endswith('.temp.mp4')]
    if request.method == 'POST':
        link = form.link.data
        format_choice = request.form.get('format', 'best')
        if not link:
            flash("Please enter a YouTube link.", 'danger')
        else:
            try:
                # Get video info for preview
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(link, download=False)
                    video_info = {
                        'title': info.get('title'),
                        'thumbnail': info.get('thumbnail'),
                        'duration': info.get('duration'),
                    }
                # Download if submit pressed
                info, final_path = download_youtube_video(link, DOWNLOADS_DIR, format_choice)
                filename = os.path.basename(final_path)
                download_url = url_for('download_file', filename=filename)
                flash(f"Downloaded: {filename}", 'success')
            except Exception as e:
                flash(f"Error: {str(e)}", 'danger')
    return render_template('index.html', form=form, download_url=download_url, filename=filename, video_info=video_info, downloads=downloads)

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)

def download_youtube_video(link, folder_selected, format_choice='best'):
    if not folder_selected:
        raise ValueError("No folder selected.")
    output_path = os.path.join(folder_selected, '%(title)s.%(ext)s')
    if format_choice == 'audio':
        opts = {
            'outtmpl': output_path,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'merge_output_format': 'mp3',
            'quiet': True,
        }
    elif format_choice == 'video':
        opts = {
            'outtmpl': output_path,
            'format': 'bestvideo[ext=mp4]/bestvideo',  # Only video, prefer mp4
            'quiet': True,
        }
    else:
        opts = {
            'outtmpl': output_path,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'quiet': True,
        }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(link, download=True)
        filename = ydl.prepare_filename(info)
        if format_choice == 'audio':
            filename = os.path.splitext(filename)[0] + '.mp3'
        return info, filename

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
