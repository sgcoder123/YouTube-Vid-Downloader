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