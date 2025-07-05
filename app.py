from flask import Flask, render_template_string, request, redirect, url_for, flash
import yt_dlp
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

HTML_FORM = '''
<!doctype html>
<title>YouTube Video Downloader</title>
<h2>YouTube Video Downloader</h2>
<form method="post">
    <label for="url">YouTube Video URL:</label><br>
    <input type="text" id="url" name="url" required style="width: 400px;"><br><br>
    <label for="folder">Download Folder (absolute path):</label><br>
    <input type="text" id="folder" name="folder" required style="width: 400px;"><br><br>
    <input type="submit" value="Download">
</form>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul style="color: red;">
    {% for message in messages %}
      <li>{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
{% if info %}
    <h3>Download Complete!</h3>
    <ul>
        <li>Title: {{ info['title'] }}</li>
        <li>Views: {{ info['view_count'] }}</li>
        <li>Length: {{ info['duration'] }} seconds</li>
        <li>Downloaded to: {{ info['filepath'] }}</li>
    </ul>
{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    info = None
    if request.method == 'POST':
        url = request.form.get('url')
        folder = request.form.get('folder')
        if not url or not folder:
            flash('Both fields are required!')
        elif not os.path.isdir(folder):
            flash('The specified folder does not exist!')
        else:
            output_path = os.path.join(folder, '%(title)s.%(ext)s')
            opts = {
                'outtmpl': output_path,
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'quiet': True,
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    result = ydl.extract_info(url, download=True)
                    info = {
                        'title': result.get('title'),
                        'view_count': result.get('view_count'),
                        'duration': result.get('duration'),
                        'filepath': output_path % result
                    }
            except Exception as e:
                flash(f'Error: {e}')
    return render_template_string(HTML_FORM, info=info)

if __name__ == '__main__':
    app.run(debug=True)
