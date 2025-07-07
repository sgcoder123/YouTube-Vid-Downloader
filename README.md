# YouTube Video Downloader (Flask + yt-dlp)

This project is a modern, privacy-focused YouTube video downloader web app. It is built with Python (Flask) for the backend and uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to handle YouTube video and audio downloads. The frontend is designed with HTML and CSS for a clean, responsive user experience, including both dark and light modes.

With this app, users can download YouTube videos or extract audio in their preferred format (video+audio, video only, or audio only) directly from their browser. No sign-up, ads, or tracking are involved—downloads are instant and private, with nothing saved on the server. The app also supports downloading age-restricted and private videos (with user-supplied cookies) and is ready for easy deployment on Vercel.

**Technologies Used:**
- Python 3.11
- Flask (web framework)
- yt-dlp (YouTube downloader library)
- Flask-WTF & WTForms (form handling and validation)
- FFmpeg (for audio/video conversion, must be installed in the environment)
- HTML/CSS (frontend UI)

This project is ideal for anyone seeking a distraction-free, web-based YouTube downloader that respects user privacy and is simple to run locally or deploy to the cloud.

## Live Demo

Try the app live on Vercel: [https://youtube-vid-downloader.vercel.app/](https://youtube-vid-downloader.vercel.app/)

## Features
- **Download YouTube videos or audio** in your preferred format (video+audio, video only, audio only)
- **No sign-up, no ads, no tracking**—your privacy is guaranteed
- **Modern, responsive UI** with dark/light mode
- **Instant downloads**—files are served directly, nothing is saved on the server
- **Handles age-restricted and private videos** (with cookies, see FAQ)

## Getting Started

To run the app locally:
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the app:**
   ```bash
   python app.py
   ```
3. Open [http://127.0.0.1:5050](http://127.0.0.1:5050) in your browser.

## Technologies Used

**Languages:**
- Python 3.11: The backend and all core logic are written in Python.
- HTML/CSS: The frontend uses HTML and CSS for the user interface, with a modern, responsive design.

**Key Libraries & Frameworks:**
- [Flask](https://flask.palletsprojects.com/): Lightweight Python web framework used to build the web server and handle routing.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): Powerful YouTube video/audio downloader library for extracting and downloading media.
- [Flask-WTF](https://flask-wtf.readthedocs.io/): Simplifies form handling and validation in Flask.
- [WTForms](https://wtforms.readthedocs.io/): Used for form validation and rendering.
- [FFmpeg](https://ffmpeg.org/): Required by yt-dlp for audio/video conversion and merging (must be installed in the environment).

These technologies work together to provide a seamless, private, and efficient YouTube downloading experience through a web interface.

## Project Structure
```
app.py           # Main Flask app (web server)
wsgi.py          # WSGI entrypoint for Vercel
requirements.txt # Python dependencies
vercel.json      # Vercel deployment config
templates/
  index.html     # Main HTML template
```

## License
MIT

---
Made with ❤️ by sgcoder123
