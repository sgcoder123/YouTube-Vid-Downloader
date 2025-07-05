import sys
import yt_dlp
import tkinter as tk
from tkinter import filedialog

# Prompt user for YouTube video URL
link = input("Enter the YouTube video URL: ")

# Ask user to select a download folder using tkinter
root = tk.Tk()
root.withdraw()  # Hide the main window
folder_selected = filedialog.askdirectory(title="Select Download Folder")
if not folder_selected:
    print("No folder selected. Exiting.")
    sys.exit(1)

# Set download options
output_path = f'{folder_selected}/%(title)s.%(ext)s'
opts = {
    'outtmpl': output_path,
    'format': 'bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
    'quiet': False,
}

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(link, download=True)
    print(f"Title: {info.get('title')}")
    print(f"Views: {info.get('view_count')}")
    print(f"Length: {info.get('duration')} seconds")
    print(f"Downloaded to: {output_path % info}")
    print("Download completed!")