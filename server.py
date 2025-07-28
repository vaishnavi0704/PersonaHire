# server.py
import os
from flask import Flask, request, jsonify, render_template
from livekit import api
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interview_server")

@app.route('/getToken', methods=['GET', 'POST'])
def get_token():
    """Generate LiveKit access token for participants"""
    try:
        if request.method == 'GET':
            identity = request.args.get('identity', 'anonymous')
            room_name = request.args.get('room', 'interview-room')
            candidate_name = request.args.get('name', identity)
            position = request.args.get('position', 'Candidate')
        else:  # POST
            data = request.get_json()
            identity = data.get('identity', 'anonymous')
            room_name = data.get('room', 'interview-room')
            candidate_name = data.get('name', identity)
            position = data.get('position', 'Candidate')

        # Create access token
        token = api.AccessToken(
            os.getenv('LIVEKIT_API_KEY'),
            os.getenv('LIVEKIT_API_SECRET')
        ).with_identity(identity).with_name(f"{candidate_name} - {position}").with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
        )

        logger.info(f"✅ Token generated for {candidate_name} applying for {position}")
        
        if request.method == 'GET':
            return token.to_jwt()
        else:
            return jsonify({
                'token': token.to_jwt(),
                'url': os.getenv('LIVEKIT_URL'),
                'room': room_name
            })

    except Exception as e:
        logger.error(f"❌ Token generation failed: {e}")
        return jsonify({'error': 'Failed to generate token'}), 500

@app.route('/start-interview', methods=['POST'])
def start_interview():
    """Start a new interview session"""
    try:
        data = request.get_json()
        candidate_name = data.get('candidateName')
        position = data.get('position')
        room_name = data.get('roomName', 'interview-room')
        
        if not candidate_name or not position:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Generate unique identity
        identity = f"candidate_{candidate_name.lower().replace(' ', '_')}"
        
        # Create token
        token = api.AccessToken(
            os.getenv('LIVEKIT_API_KEY'),
            os.getenv('LIVEKIT_API_SECRET')
        ).with_identity(identity).with_name(f"{candidate_name}").with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
        )
        
        logger.info(f"🎯 Interview started: {candidate_name} for {position}")
        
        return jsonify({
            'success': True,
            'token': token.to_jwt(),
            'url': os.getenv('LIVEKIT_URL'),
            'room': room_name,
            'identity': identity,
            'candidateName': candidate_name,
            'position': position
        })
        
    except Exception as e:
        logger.error(f"❌ Interview start failed: {e}")
        return jsonify({'error': 'Failed to start interview'}), 500

@app.route('/')
def index():
    """Serve the frontend interview interface"""
    return render_template("index.html")

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'livekit_url': os.getenv('LIVEKIT_URL'),
        'server': 'running'
    })

if __name__ == '__main__':
    # Verify environment variables
    if not os.getenv('LIVEKIT_API_KEY') or not os.getenv('LIVEKIT_API_SECRET'):
        logger.error("❌ Missing LIVEKIT_API_KEY or LIVEKIT_API_SECRET")
        exit(1)
    
    logger.info("🚀 Interview server starting...")
    logger.info(f"📡 LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)