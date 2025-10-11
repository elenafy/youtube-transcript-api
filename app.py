# app.py
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import os

app = Flask(__name__)

@app.route('/', methods=['POST'])
def get_transcript():
    try:
        data = request.get_json()
        url_or_id = data.get('urlOrId', '')
        video_id = data.get('videoId', '')
        languages = data.get('languages', ['en'])
        
        # Extract video ID if needed
        if not video_id and url_or_id:
            if 'youtu.be/' in url_or_id:
                video_id = url_or_id.split('youtu.be/')[-1].split('?')[0]
            elif 'youtube.com/watch' in url_or_id:
                video_id = url_or_id.split('v=')[-1].split('&')[0]
            elif 'youtube.com/shorts/' in url_or_id:
                video_id = url_or_id.split('/shorts/')[-1].split('?')[0]
        
        if not video_id:
            return jsonify({'success': False, 'error': 'No video ID found'})
        
        # Try to get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        
        # Convert to our format
        captions = []
        for item in transcript:
            captions.append({
                'text': item['text'],
                'offset': int(item['start'] * 1000),  # Convert to milliseconds
                'duration': int(item['duration'] * 1000)
            })
        
        return jsonify({'success': True, 'captions': captions})
        
    except Exception as e:
        error_msg = str(e)
        if 'disabled' in error_msg.lower() or 'not available' in error_msg.lower():
            return jsonify({'success': False, 'error': f'Transcript disabled: {error_msg}'})
        return jsonify({'success': False, 'error': error_msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
