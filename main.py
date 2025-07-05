import sys
import yt_dlp

if len(sys.argv) < 2:
    print("Please provide a YouTube video link.")
    sys.exit(1)

link = sys.argv[1]

# Set download options
output_path = '/Users/saig/Desktop/Random Stuff/YouTube-Vid-Downloader/%(title)s.%(ext)s'
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