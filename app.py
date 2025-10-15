from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'youtube-transcript-api'})

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'youtube-transcript-api',
        'status': 'running',
        'endpoints': {
            'health': 'GET /health',
            'transcript': 'POST /'
        }
    })

@app.route('/', methods=['POST'])
def get_transcript():
    try:
        data = request.get_json()
        print(f"🔍 Received request: {data}")  # Debug log
        url_or_id = data.get('urlOrId', '')
        video_id = data.get('videoId', '')
        languages = data.get('languages', ['en'])
        print(f"🎯 Processing video_id: {video_id}, languages: {languages}")  # Debug log
        
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
        
        # Use the same API as your local environment
        ytt_api = YouTubeTranscriptApi()
        
        # Try to fetch transcript with the specified languages
        # First try with specified languages, then fallback to auto-detect
        language_attempts = [languages, []]  # Try specified languages, then auto-detect
        
        for attempt_languages in language_attempts:
            try:
                fetched_transcript = ytt_api.fetch(video_id, languages=attempt_languages)
                
                # Convert to our format
                captions = []
                for snippet in fetched_transcript:
                    captions.append({
                        'text': snippet.text,
                        'offset': int(snippet.start * 1000),  # Convert to milliseconds
                        'duration': int(snippet.duration * 1000)
                    })
                
                return jsonify({'success': True, 'captions': captions})
                
            except Exception as e:
                # If this attempt failed, try the next language combination
                if attempt_languages == []:  # This was the last attempt
                    error_msg = str(e)
                    # Handle specific YouTube transcript API errors
                    if 'disabled' in error_msg.lower():
                        return jsonify({
                            'success': False, 
                            'error': 'Transcript disabled by video creator',
                            'error_type': 'transcript_disabled',
                            'video_id': video_id
                        })
                    elif 'not available' in error_msg.lower() or 'no transcript' in error_msg.lower():
                        return jsonify({
                            'success': False, 
                            'error': 'No transcript available for this video',
                            'error_type': 'no_transcript',
                            'video_id': video_id
                        })
                    elif 'video unavailable' in error_msg.lower():
                        return jsonify({
                            'success': False, 
                            'error': 'Video is unavailable or private',
                            'error_type': 'video_unavailable',
                            'video_id': video_id
                        })
                    else:
                        return jsonify({
                            'success': False, 
                            'error': f'Transcript extraction failed: {error_msg}',
                            'error_type': 'extraction_error',
                            'video_id': video_id
                        })
                continue  # Try next language combination
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Flask app on port {port}")
    print(f"🔧 Environment: {os.environ.get('RENDER', 'local')}")
    app.run(host='0.0.0.0', port=port, debug=False)
