from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import os
import certifi

app = Flask(__name__)

# Proxy configuration helper
def get_proxy_config():
    proxy_url = os.environ.get('PROXY_URL')
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy_url:
        return {'http': proxy_url, 'https': proxy_url}
    if http_proxy or https_proxy:
        return {'http': http_proxy or https_proxy, 'https': https_proxy or http_proxy}
    return None

# Ensure proxy env vars are exported at startup so requests picks them up
def set_proxy_env_from_config():
    cfg = get_proxy_config()
    if not cfg:
        return
    if cfg.get('http'):
        os.environ['HTTP_PROXY'] = cfg['http']
        os.environ['http_proxy'] = cfg['http']
    if cfg.get('https'):
        os.environ['HTTPS_PROXY'] = cfg['https']
        os.environ['https_proxy'] = cfg['https']
    # Ensure requests uses a valid CA bundle in serverless/container
    ca_path = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = ca_path
    os.environ['SSL_CERT_FILE'] = ca_path

# Apply at import time
set_proxy_env_from_config()

@app.route('/health', methods=['GET'])
def health_check():
    proxy_config = get_proxy_config()
    # Effective proxies used by requests
    effective_http = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    effective_https = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

    def mask(url):
        if not url:
            return None
        return f"***:***@{url.split('@')[-1]}" if '@' in url else url

    return jsonify({
        'status': 'healthy',
        'service': 'youtube-transcript-api',
        'proxy_configured': proxy_config is not None,
        'effective_http_proxy': mask(effective_http),
        'effective_https_proxy': mask(effective_https)
    })

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
        
        # Set proxy env so requests (used by youtube-transcript-api) picks it up
        proxy_config = get_proxy_config()
        if proxy_config:
            if proxy_config.get('http'):
                os.environ['HTTP_PROXY'] = proxy_config['http']
                os.environ['http_proxy'] = proxy_config['http']
            if proxy_config.get('https'):
                os.environ['HTTPS_PROXY'] = proxy_config['https']
                os.environ['https_proxy'] = proxy_config['https']

        # Create API instance
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
    proxy_config = get_proxy_config()
    print('=' * 80)
    print('🚀 Starting Flask YouTube Transcript API')
    print('=' * 80)
    print(f"Port: {port}")
    print(f"Environment: {os.environ.get('RENDER', 'local')}")
    print(f"Proxy configured: {'✅ Yes' if proxy_config else '❌ No (requests may be blocked)'}")
    if proxy_config:
        disp = proxy_config.get('https') or proxy_config.get('http')
        if disp and '@' in disp:
            disp = f"***:***@{disp.split('@')[-1]}"
        print(f"Proxy URL: {disp}")
    print('=' * 80)
    app.run(host='0.0.0.0', port=port, debug=False)
