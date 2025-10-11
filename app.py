Install
It is recommended to install this module by using pip:

pip install youtube-transcript-api
You can either integrate this module into an existing application or just use it via a CLI.

API
The easiest way to get a transcript for a given video is to execute:

from youtube_transcript_api import YouTubeTranscriptApi

ytt_api = YouTubeTranscriptApi()
ytt_api.fetch(video_id)
