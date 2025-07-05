from flask import Flask, request, render_template_string
import os
from main import download_youtube_video

app = Flask(__name__)

HTML_FORM = '''
<!doctype html>
<title>YouTube Video Downloader</title>
<h2>Download a YouTube Video</h2>
<form method="post">
  YouTube URL: <input type="text" name="url" required><br><br>
  Download Folder: <input type="text" name="folder" value="{{ default_folder }}" required><br><br>
  <input type="submit" value="Download">
</form>
{% if message %}<p>{{ message }}</p>{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    default_folder = os.path.expanduser('~/Downloads')
    if request.method == 'POST':
        url = request.form['url']
        folder = request.form['folder']
        try:
            info, output_path = download_youtube_video(url, folder)
            message = f"Downloaded: {info.get('title')}<br>To: {output_path}" \
                      f"<br>Views: {info.get('view_count')}<br>Length: {info.get('duration')} seconds"
        except Exception as e:
            message = f"Error: {e}"
    return render_template_string(HTML_FORM, message=message, default_folder=default_folder)

if __name__ == '__main__':
    app.run(debug=True)
