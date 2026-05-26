#!/bin/bash
echo "🏥 Hospital CEO Dashboard — XelerAIT Hackathon"
echo "================================================"

cd "$(dirname "$0")/backend"

echo "📦 Installing dependencies..."
pip install fastapi uvicorn sqlalchemy httpx --break-system-packages -q

echo "🌱 Seeding database..."
python seed.py

# Prompt for Groq API key if not set
if [ -z "$GROQ_API_KEY" ]; then
  echo ""
  echo "🔑 Enter your Groq API key (get it free at console.groq.com):"
  read -r GROQ_API_KEY
  export GROQ_API_KEY
fi

echo ""
echo "🚀 Starting API server on http://localhost:8000"
echo "🌐 Open frontend/index.html in your browser"
echo "🤖 AI Concierge: click the chat button (bottom-right)"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
