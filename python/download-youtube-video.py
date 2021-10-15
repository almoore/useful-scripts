#!/usr/local/bin/env python3
from pytube import YouTube
 
def download(youtube_video_url):
    try:
        yt_obj = YouTube(youtube_video_url)
        filters = yt_obj.streams.filter(progressive=True, file_extension='mp4')
        # download the highest quality video
        filters.get_highest_resolution().download()
        print('Video Downloaded Successfully')
    except Exception as e:
        print(e)


if __name__ == "__main__":
    import sys 
    download(sys.argv[1])
