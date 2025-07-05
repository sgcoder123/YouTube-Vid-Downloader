import yt_dlp

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