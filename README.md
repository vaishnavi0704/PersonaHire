# 🧠 PersonaHire – Serverless AI Screening Platform

**PersonaHire** is a fully autonomous AI-powered recruitment screener that eliminates the need for manual resume screening or interview scheduling. It’s built to **engage, evaluate, and shortlist candidates** through real-time, empathetic conversations — all without human intervention.

---

## ⚙️ What It Does

- 🎙️ Conducts AI-driven voice interviews via browser using **Livekit**  
- 🤝 Understands candidate tone and emotional cues with **Silerio VAD**  
- 🧠 Uses **GPT-4** to carry human-like dialogue & dynamic question routing  
- 🗂️ Pulls candidate data directly from **Airtable**  
- ☁️ Stores audio + metadata in **AWS S3**, triggering workflows via **Lambda**  
- 🔄 Fully serverless — automated E2E pipeline from candidate application to hiring summary  

---

## 💡 Use Case

**For startups, HR teams, or tech recruiters** looking to:
- Automate early-stage screening
- Scale candidate processing without increasing HR headcount
- Ensure fairness and consistency in interviews
- Integrate seamlessly with Airtable, AWS, and modern hiring stacks

---

## 🧠 Key Features

### 🗣️ Empathetic AI Voice Interviews
- Built using **OpenAI GPT-4** for dynamic dialogue  
- Tone, pause, and emotion captured using **Silerio VAD + STT + TTS**  
- Natural voice communication enabled via **Livekit**

### 🧾 Resume Intake + Screening
- Resume parsing + data intake from **Airtable**  
- Automatically triggers interview workflow via Airtable form submission  

### ☁️ Serverless Automation
- **AWS Lambda** handles:
  - Audio file processing
  - VAD segmentation
  - Triggering evaluation logic
- Interview logs + audio recordings saved in **S3**

### 🧪 Evaluation & Ranking
- Candidate responses scored by GPT-4 with:
  - Relevance
  - Communication clarity
  - Emotional tone
- Final scores logged in Airtable with a decision recommendation

---

## 🛠️ Tech Stack

| Layer             | Tech / Tools                               |
|------------------|---------------------------------------------|
| AI Engine        | OpenAI GPT-4, Python                        |
| Dialogue         | LiveKit, Silerio VAD, ElevenLabs            |
| Frontend         | Next.js                                     |
| Backend          | Python, Docker, AWS Lambda                  |
| Database         | Airtable                                    |
| Storage          | AWS S3                                      |
| DevOps           | Git, Docker, Vercel (UI Hosting)            |

---

## 🧬 System Architecture

```mermaid
flowchart LR
    A[Candidate Airtable Form] --> B[Trigger Lambda]
    B --> C[Create Interview Room (Livekit)]
    C --> D[Empathetic AI Interview (GPT-4)]
    D --> E[STT, VAD, TTS for Dialogue Loop]
    D --> F[S3: Store Audio + Transcript]
    D --> G[Evaluate Candidate Score]
    G --> H[Airtable: Update with Decision]
PersonaHire/
├── frontend/                 # Next.js frontend for interviews
├── backend/
│   ├── dialogue_engine/      # GPT-4 prompt orchestration
│   ├── vad_engine/           # Silerio VAD + STT + TTS pipeline
│   ├── lambda_functions/     # S3 event triggers and orchestration
│   └── airtable_handler/     # API connectors for Airtable
├── docker/                   # Dockerfile and AWS deploy configs
├── utils/                    # Shared helpers and secrets loader
├── README.md
└── .env.example              # Example config for local dev


cd backend
pip install -r requirements.txt
uvicorn app:app --reload



cd frontend
npm install
npm run dev


.env file
OPENAI_API_KEY=your-key
AIRTABLE_BASE_ID=...
AIRTABLE_API_KEY=...
LIVEKIT_API_KEY=...
LIVEKIT_SECRET=...
AWS_ACCESS_KEY=...
AWS_SECRET_KEY=...
S3_BUCKET=...
# PersonaHire
Serverless Automation Pipeline Architected on Airtable &amp; AWS S3. Closed-loop system handling entire screening process without human intervention. Empathetic Dialogue Engine Implemented using OpenAI for dialogue, STT, TTS.
