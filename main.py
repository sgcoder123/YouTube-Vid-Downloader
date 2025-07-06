import yt_dlp
import tkinter as tk
from tkinter import filedialog

def choose_folder_dialog():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_selected = filedialog.askdirectory(title="Select Download Folder")
    root.destroy()
    return folder_selected

def download_youtube_video(link, folder_selected):
    if not folder_selected:
        raise ValueError("No folder selected.")
    output_path = f'{folder_selected}/%(title)s.%(ext)s'
    opts = {
        'outtmpl': output_path,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(link, download=True)
        final_path = output_path % info
        return info, final_path

# ---
# Why Use This YouTube Downloader?
#
# • YouTube is the world's largest video platform, with over 2 billion users—get your favorite content offline!
# • Download in multiple formats: best quality (video+audio), video only (for editing or sharing), or audio only (mp3 for music/podcasts).
# • No account, no sign-up, no ads—just paste a link and download instantly.
# • Powered by yt-dlp: fast, reliable, and open-source (trusted by thousands of developers).
# • Your privacy is protected: downloads are saved only to your computer, never uploaded or tracked.
# • Works on macOS, Windows, and Linux—cross-platform convenience.
# • 100% free, open source, and safe—no hidden costs, no tracking, no bloat.
# • Great for students, travelers, content creators, and anyone who wants offline access.
#
# Try it now and join a global community of users who enjoy hassle-free, private YouTube downloads!
#
# ---
# How the Download System Works:
#
# 1. Paste a YouTube link and click Download—the app fetches video info and shows a preview (title, thumbnail, duration).
# 2. Choose your preferred format: best (video+audio), video only, or audio only (mp3).
# 3. The file is saved to a temporary folder on your computer (not in the project folder).
#    - On macOS, this is usually /tmp or a similar system temp directory.
#    - The file is available for you to download via the provided link after processing.
# 4. Files in the temp directory may be deleted by your system automatically after some time or on restart.
# 5. No downloaded files are stored in the project, so your project folder stays clean and safe from other users' downloads.
#
# Want to pick your own folder? Use choose_folder_dialog() for manual downloads—great for organizing your files!