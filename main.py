from pytube import YouTube
import sys

link = sys.argv[1]

yt = YouTube(link)

print(f"Title: {yt.title}")
print(f"Views: {yt.views}")
print(f"Length: {yt.length} seconds")

ytdl = yt.streams.get_highest_resolution()
print(f"Downloading {ytdl.title}...")
ytdl.download()
print("Download completed!")