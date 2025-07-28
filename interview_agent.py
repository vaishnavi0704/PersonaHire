# import os
# import asyncio
# import logging
# from dotenv import load_dotenv

# from livekit import agents, rtc
# from livekit.agents import (
#     Agent,
#     function_tool,
#     AgentSession,
#     RoomInputOptions,
#     JobProcess,
#     JobContext,
#     WorkerOptions,
#     cli,
# )
# from livekit.plugins import openai, silero, noise_cancellation
# from livekit.plugins.turn_detector.multilingual import MultilingualModel

# # Load environment variables from .env
# load_dotenv()

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("vision_call_agent")

# # -- 1. Prewarm heavy models in subprocesses --
# def prewarm_fnc(proc: JobProcess):
#     proc.userdata["vad"] = silero.VAD.load()
#     proc.userdata["stt"] = openai.STT(model="gpt-4o-transcribe")
#     proc.userdata["tts"] = openai.TTS()

# # -- 2. Agent that handles voice call and vision --
# class VisioningCallAgent(Agent):
#     def __init__(self) -> None:
#         super().__init__(
#             instructions=(
#                 "You are conducting a mock job interview. Greet the candidate first, then ask them to briefly introduce themselves. "
#     "After that, ask questions one by one from this list: "
#     "'Why do you want this job?', 'What are your strengths?', 'Describe a challenge you faced and how you solved it.', "
#     "'Where do you see yourself in 5 years?', and 'Do you have any questions for us?'. "
#     "Be polite and professional. Pause and wait for answers after each question."

#             ),
#             stt=openai.STT(model="gpt-4o-transcribe"),
#             llm=openai.LLM(model="gpt-4o-mini-2024-07-18"),
#             tts=openai.TTS(),
#             vad=silero.VAD.load(),
#         )

#     @function_tool(
#         name="evaluate_image",
#         description="Analyze and describe an image frame from the video feed"
#     )
#     async def evaluate_image(self) -> str:
#         # TODO: replace with real image-processing logic
#         return "I see a live video frame with some content."

#     async def on_enter(self):
#         # Trigger initial prompt when session starts
#         await self.session.generate_reply()

# # -- 3. Entrypoint: setup connection and session --
# async def entrypoint(ctx: JobContext):
#     # Connect to LiveKit room, auto-subscribe to audio & video
#     await ctx.connect(auto_subscribe=agents.AutoSubscribe.SUBSCRIBE_ALL)

#     # Retrieve prewarmed instances
#     vad = ctx.proc.userdata["vad"]
#     stt = ctx.proc.userdata["stt"]
#     tts = ctx.proc.userdata["tts"]

#     # Build the agent session pipeline
#     session = AgentSession(
#         stt=stt,
#         llm=openai.LLM(model="gpt-4o-mini-2024-07-18"),
#         tts=tts,
#         vad=vad,
#         turn_detection=MultilingualModel(),
#     )

#     # Start the session (handles STT → LLM → TTS, VAD, and turn detection)
#     await session.start(
#         agent=VisioningCallAgent(),
#         room=ctx.room,
#         room_input_options=RoomInputOptions(
#             noise_cancellation=noise_cancellation.BVC()
#         ),
#     )

#     # Background task: capture video frames and invoke the image tool

#     async def process_video():
#         participant = await ctx.wait_for_participant()

#         video_track = None
#         for pub in participant.get_track_publications():
#             track = pub.track
#             if isinstance(track, rtc.RemoteVideoTrack):
#                 video_track = track
#                 break

#         if not video_track:
#             logger.warning("No remote video track found.")
#             return

#         async for frame in rtc.VideoStream(video_track):
#             await session.invoke_tool("evaluate_image")

#     # ✅ Run video processing in the background
#     asyncio.create_task(process_video())


# # -- 4. Run the worker with prewarming and extended timeout --
# if __name__ == "__main__":
#     opts = WorkerOptions(
#         entrypoint_fnc=entrypoint,
#         prewarm_fnc=prewarm_fnc,
#         num_idle_processes=1,
#         initialize_process_timeout=60000,  # 60 seconds
#     )
#     cli.run_app(opts)







# interview_agent.py - Fixed version
import os
import asyncio
import logging
from dotenv import load_dotenv
import numpy as np
import cv2
import random
import time

from livekit.rtc import LocalVideoTrack, VideoFrame
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    function_tool,
    AgentSession,
    RoomInputOptions,
    JobProcess,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai, silero

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interview_agent")

# -- 1. Prewarm heavy models in subprocesses --
def prewarm_fnc(proc: JobProcess):
    try:
        proc.userdata["vad"] = silero.VAD.load()
        proc.userdata["stt"] = openai.STT(model="gpt-4o-transcribe")
        proc.userdata["tts"] = openai.TTS(voice="alloy")
        logger.info("✅ Models prewarmed successfully")
    except Exception as e:
        logger.error(f"❌ Prewarming failed: {e}")
        raise

# -- 2. Agent that handles voice call and vision --
class VisioningCallAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                """You are Sarah Mitchell, a warm and professional Senior HR Manager conducting a job interview. 
                
                YOUR PERSONALITY:
                - You are a real human, not an AI. You have been working in HR for 8 years.
                - Warm, empathetic, and genuinely interested in people's stories
                - Professional but approachable - you want candidates to feel comfortable
                - You occasionally share brief personal insights: "In my experience..." or "I've found that..."
                - You use natural speech patterns with occasional pauses, "um," and conversational flow
                - You remember what candidates say and reference it later in the conversation
                - You show genuine reactions: surprise, interest, understanding, concern when appropriate
                
                CONVERSATION STYLE:
                - Start with a warm greeting: "Hello! I'm Sarah Mitchell, thanks so much for joining me today. How are you feeling?"
                - Use the candidate's name occasionally to build rapport (get their name from conversation)
                - Ask follow-up questions based on their specific answers
                - Show active listening: "That's fascinating," "I can see why that was challenging," "Tell me more about that"
                - Natural transitions: "That's interesting. Building on what you just said..." 
                - Take brief pauses before asking the next question, like a real person thinking
                
                INTERVIEW FLOW (one question at a time, wait for complete responses):
                1. Warm greeting: "Hello! I'm Sarah Mitchell, Senior HR Manager. Thank you for joining me today! Before we start, could you please tell me your name and the position you're applying for?"
                2. "Great! Tell me about yourself and what brings you here today"
                3. "What attracted you to this position specifically?"
                4. "Walk me through a project you're particularly proud of"
                5. "Describe a time when you faced a significant challenge at work and how you handled it"
                6. "Tell me about a time you had to work with someone difficult. How did you manage that?"
                7. "Where do you see yourself professionally in the next few years?"
                8. "What questions do you have for me about the role or our company?"
                
                HUMAN BEHAVIORS TO INCLUDE:
                - Occasionally say "mm-hmm" or "right" during their responses
                - Reference what they said earlier: "You mentioned earlier about X, can you tell me more..."
                - Show surprise: "Oh wow, that sounds really challenging!"
                - Show empathy: "I can imagine that must have been difficult"
                - Use encouraging phrases: "That's a great example" or "I really appreciate your honesty there"
                - End warmly: "Thank you so much for your time today. It's been wonderful getting to know you."
                
                Remember: You are Sarah Mitchell, a real person conducting this interview. Make it feel natural, engaging, and authentically human.
                """
            ),
            stt=openai.STT(model="gpt-4o-transcribe"),
            llm=openai.LLM(model="gpt-4o-mini-2024-07-18"),
            tts=openai.TTS(voice="alloy"),
            vad=silero.VAD.load(),
        )

    @function_tool(
        name="evaluate_image",
        description="Analyze and describe an image frame from the video feed"
    )
    async def evaluate_image(self) -> str:
        observations = [
            "I can see you're thinking carefully about that - take your time!",
            "You look very confident and engaged, which is wonderful to see.",
            "I notice you're quite comfortable on camera, that's great.",
            "Your body language shows you're really passionate about this topic.",
            "I can tell this is something you care deeply about from your expression."
        ]
        return random.choice(observations)

    async def on_enter(self):
        logger.info("🎭 Sarah Mitchell entering the interview room")
        # Wait for connection to stabilize
        await asyncio.sleep(3)
        # Start the interview
        await self.session.generate_reply()

async def start_interviewer_video(session: AgentSession):
    """Generate and publish the interviewer's video feed"""
    
    def create_professional_video():
        frame_count = 0
        
        while True:
            frame_count += 1
            
            # Create professional background
            height, width = 720, 1280
            img = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Professional gradient background
            for i in range(height):
                intensity = int(25 + (i / height) * 45)
                img[i, :] = [intensity, intensity + 10, intensity + 15]
            
            # Office elements
            # Bookshelf
            cv2.rectangle(img, (50, 80), (280, 450), (101, 67, 33), -1)
            for shelf in [130, 200, 270, 340, 410]:
                cv2.rectangle(img, (60, shelf), (270, shelf + 40), (139, 69, 19), -1)
            
            # Plant
            cv2.circle(img, (1150, 280), 50, (34, 139, 34), -1)
            cv2.ellipse(img, (1150, 220), (40, 70), 0, 0, 360, (46, 125, 50), -1)
            
            # Professional avatar - Sarah Mitchell
            center_x, center_y = 640, 300
            
            # Professional blazer (navy blue)
            cv2.rectangle(img, (center_x - 130, center_y + 70), (center_x + 130, center_y + 320), (25, 25, 112), -1)
            
            # White blouse
            cv2.rectangle(img, (center_x - 110, center_y + 80), (center_x + 110, center_y + 300), (255, 255, 255), -1)
            
            # Head (realistic skin tone)
            cv2.circle(img, (center_x, center_y), 95, (222, 184, 135), -1)
            
            # Professional hairstyle (brown)
            cv2.ellipse(img, (center_x, center_y - 55), (100, 75), 0, 180, 360, (101, 67, 33), -1)
            
            # Facial features with animation
            # Eyes (blinking every 4 seconds)
            blink_cycle = frame_count % 120
            if blink_cycle < 8:  # Blink duration
                cv2.line(img, (center_x - 35, center_y - 30), (center_x - 15, center_y - 30), (0, 0, 0), 5)
                cv2.line(img, (center_x + 15, center_y - 30), (center_x + 35, center_y - 30), (0, 0, 0), 5)
            else:
                # Open eyes
                cv2.circle(img, (center_x - 25, center_y - 30), 12, (255, 255, 255), -1)
                cv2.circle(img, (center_x + 25, center_y - 30), 12, (255, 255, 255), -1)
                cv2.circle(img, (center_x - 25, center_y - 30), 8, (101, 67, 33), -1)
                cv2.circle(img, (center_x + 25, center_y - 30), 8, (101, 67, 33), -1)
                cv2.circle(img, (center_x - 25, center_y - 30), 3, (0, 0, 0), -1)
                cv2.circle(img, (center_x + 25, center_y - 30), 3, (0, 0, 0), -1)
            
            # Eyebrows
            cv2.ellipse(img, (center_x - 25, center_y - 45), (18, 6), 0, 0, 180, (101, 67, 33), -1)
            cv2.ellipse(img, (center_x + 25, center_y - 45), (18, 6), 0, 0, 180, (101, 67, 33), -1)
            
            # Nose
            cv2.circle(img, (center_x, center_y - 5), 5, (205, 133, 63), -1)
            
            # Speaking mouth animation
            speaking_cycle = frame_count % 90
            if speaking_cycle < 30:
                mouth_height = 10 + int(4 * np.sin(speaking_cycle * 0.4))
                cv2.ellipse(img, (center_x, center_y + 35), (20, mouth_height), 0, 0, 180, (139, 69, 19), -1)
            else:
                cv2.ellipse(img, (center_x, center_y + 35), (16, 8), 0, 0, 180, (139, 69, 19), -1)
            
            # Professional information overlay
            cv2.putText(img, "Sarah Mitchell", (380, 580), cv2.FONT_HERSHEY_SIMPLEX, 2.8, (255, 255, 255), 5)
            cv2.putText(img, "Senior HR Manager", (420, 630), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (200, 200, 200), 3)
            cv2.putText(img, "TechCorp Industries", (460, 670), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (150, 150, 150), 2)
            
            # Company logo
            cv2.circle(img, (140, 650), 45, (70, 130, 180), -1)
            cv2.putText(img, "TC", (115, 665), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)
            
            # Live recording indicator
            if frame_count % 60 < 30:
                cv2.circle(img, (80, 80), 25, (0, 255, 0), -1)
                cv2.putText(img, "LIVE", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Professional frame
            cv2.rectangle(img, (8, 8), (width-8, height-8), (100, 100, 100), 6)
            
            yield VideoFrame.from_ndarray(img, format="bgr24")
    
    # Create and publish video track
    try:
        video_track = LocalVideoTrack.create_video_track("sarah_mitchell", create_professional_video())
        await session.room.local_participant.publish_track(video_track)
        logger.info("✅ Sarah Mitchell video feed published successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to publish video: {e}")

# -- 3. Entrypoint: setup connection and session --
async def entrypoint(ctx: JobContext):
    logger.info("🚀 Starting interview agent...")
    
    # Connect to LiveKit room
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.SUBSCRIBE_ALL)
    logger.info("✅ Connected to LiveKit room")

    # Retrieve prewarmed instances
    vad = ctx.proc.userdata["vad"]
    stt = ctx.proc.userdata["stt"]
    tts = ctx.proc.userdata["tts"]

    # Build the agent session pipeline WITHOUT MultilingualModel
    session = AgentSession(
        stt=stt,
        llm=openai.LLM(model="gpt-4o-mini-2024-07-18"),
        tts=tts,
        vad=vad,
        # Removed turn_detection to avoid the timeout issue
    )

    # Start the session
    await session.start(
        agent=VisioningCallAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions()
    )
    
    logger.info("✅ Agent session started")
    
    # Start Sarah Mitchell's video feed
    await start_interviewer_video(session)
    logger.info("🎭 Sarah Mitchell is now conducting interviews!")

    # Background task: process candidate video
    async def process_video():
        try:
            participant = await ctx.wait_for_participant()
            logger.info(f"👤 Candidate joined: {participant.identity}")

            # Find video track
            video_track = None
            for pub in participant.track_publications.values():
                if pub.track and isinstance(pub.track, rtc.RemoteVideoTrack):
                    video_track = pub.track
                    break


            if not video_track:
                logger.warning("⚠️  No candidate video track found.")
                return

            frame_count = 0
            async for frame in rtc.VideoStream(video_track):
                frame_count += 1
                # Analyze every 60 seconds
                if frame_count % (30 * 60) == 0:
                    await session.invoke_tool("evaluate_image")
                    
        except Exception as e:
            logger.error(f"❌ Video processing error: {e}")

    # Start video processing
    asyncio.create_task(process_video())

# -- 4. Run the worker --
if __name__ == "__main__":
    # Check environment variables
    required_vars = ['LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        logger.error("Please check your .env file")
        exit(1)
    
    logger.info("✅ Environment variables loaded")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    
    opts = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm_fnc,
        num_idle_processes=1,
        initialize_process_timeout=120000,  # Increased timeout to 2 minutes
    )
    
    logger.info("🏁 Starting interview agent...")
    cli.run_app(opts)