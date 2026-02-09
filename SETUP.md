# 🚀 Complete Setup Guide

## Welcome! This is your step-by-step guide to get the AI Research Teaching Agent running.

## ⏱️ Expected Setup Time: 15-20 minutes

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.10 or higher installed
- [ ] Node.js 18 or higher installed
- [ ] npm or yarn package manager
- [ ] Git (optional, for cloning)
- [ ] A code editor (VS Code recommended)

Check your versions:
```bash
python --version    # Should be 3.10+
node --version      # Should be v18+
npm --version       # Any recent version
```

---

## 🔑 Step 1: Get API Keys (10 minutes)

### Required API Keys:

#### 1. OpenAI API Key
- Go to: https://platform.openai.com/api-keys
- Sign in or create account
- Click "Create new secret key"
- Copy the key (starts with `sk-`)
- **Cost**: ~$0.01-0.10 per question (GPT-4)

#### 2. Tavily API Key
- Go to: https://tavily.com/
- Sign up for free account
- Navigate to API keys section
- Copy your API key
- **Cost**: Free tier available, enough for testing

#### 3. Replicate API Token (Optional)
- Go to: https://replicate.com/
- Sign up
- Get API token
- **Required for**: Image understanding (VLM)
- **Can skip**: System works without it

---

## 💻 Step 2: Backend Setup (5 minutes)

### 2.1 Navigate to backend directory
```bash
cd C:\Users\Vivek\Desktop\LearnAI\ai-research-agent\backend
```

### 2.2 Create Python virtual environment
```bash
python -m venv venv
```

### 2.3 Activate virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### 2.4 Install Python dependencies
```bash
pip install -r requirements.txt
```

This will install:
- FastAPI & Uvicorn
- LangChain & LangGraph
- OpenAI client
- Tavily client
- And all other dependencies

### 2.5 Create environment file
```bash
copy .env.example .env
```

### 2.6 Edit .env file

Open `backend/.env` in your editor and add your API keys:

```env
# Required
OPENAI_API_KEY=sk-your-key-here
TAVILY_API_KEY=tvly-your-key-here

# Optional
REPLICATE_API_TOKEN=r8_your-token-here

# Keep other settings as default
```

**Save the file!**

### 2.7 Test backend
```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000
```

**Leave this terminal running** and open a new one for frontend setup.

---

## 🎨 Step 3: Frontend Setup (5 minutes)

### 3.1 Open NEW terminal and navigate to frontend
```bash
cd C:\Users\Vivek\Desktop\LearnAI\ai-research-agent\frontend
```

### 3.2 Install Node dependencies
```bash
npm install
```

This will install:
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- All UI components

### 3.3 Create environment file
```bash
copy .env.local.example .env.local
```

### 3.4 Edit .env.local (if needed)

The default should work:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3.5 Start development server
```bash
npm run dev
```

You should see:
```
  ▲ Next.js 14.1.0
  - Local:        http://localhost:3000
  - Ready in 2.5s
```

---

## ✅ Step 4: Verify Everything Works

### 4.1 Check backend health
Open browser: http://localhost:8000/health

Should see:
```json
{
  "status": "healthy",
  "orchestrator": true,
  "settings": {...}
}
```

### 4.2 Check API documentation
Open browser: http://localhost:8000/docs

You should see interactive API documentation (Swagger UI).

### 4.3 Open the application
Open browser: http://localhost:3000

You should see:
- Clean, modern interface
- Input box at the bottom
- Suggested questions
- "AI Research Agent" header

### 4.4 Ask your first question!

Try one of these:
- "What is photosynthesis?"
- "Explain quantum computing"
- "How do neural networks learn?"

Watch as the system:
1. Analyzes your question ✓
2. Searches the web ✓
3. Processes images ✓
4. Synthesizes explanation ✓
5. Shows sources ✓

---

## 🎉 Success! You're ready!

If everything worked, you now have:
- ✅ Backend running on http://localhost:8000
- ✅ Frontend running on http://localhost:3000
- ✅ Multi-agent AI system operational
- ✅ Real-time web research working
- ✅ Streaming UI functional

---

## 🔧 Troubleshooting

### Issue: "Module not found" in backend

**Solution:**
```bash
# Make sure you're in the virtual environment
cd backend
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Issue: "Port already in use"

**Solution:**
```bash
# Backend (port 8000)
# Kill process using port 8000
netstat -ano | findstr :8000  # Find PID
taskkill /PID <PID> /F

# Frontend (port 3000)
# Kill process using port 3000
netstat -ano | findstr :3000  # Find PID
taskkill /PID <PID> /F
```

### Issue: "API key invalid"

**Solution:**
- Check .env file is in correct location: `backend/.env`
- Ensure no spaces around the `=` sign
- Verify keys are correct (copy-paste from dashboard)
- Keys should NOT be in quotes

### Issue: Frontend can't connect to backend

**Solution:**
- Verify backend is running (check http://localhost:8000/health)
- Check CORS settings in `backend/config/settings.py`
- Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local`

### Issue: Images not loading

**Solution:**
- This is normal if you don't have Replicate API token
- System will still work, just without image captions
- Images will still be collected and displayed

### Issue: Slow responses

**Possible causes:**
- First request is always slower (cold start)
- GPT-4 is slower than GPT-3.5
- Tavily "advanced" search takes longer
- Multiple sources being processed

**Normal response time:** 5-10 seconds

---

## 📱 Using the Application

### Basic Usage

1. **Type your question** in the input box
2. **Press Enter** or click Send
3. **Watch real-time updates** as agents work
4. **Review the complete response** which includes:
   - TL;DR summary
   - Step-by-step explanation
   - Visual explanations with images
   - Real-world analogies
   - Practice questions
   - Source citations

### Advanced Usage

- **Difficulty levels**: System auto-detects and adapts
- **Follow-up questions**: Use suggested questions
- **Source verification**: Click sources to read original
- **Image details**: Hover over images for captions

---

## 🛠️ Development

### Run with auto-reload (recommended)

**Backend:**
```bash
cd backend
python main.py  # Already has auto-reload
```

**Frontend:**
```bash
cd frontend
npm run dev  # Already has hot-reload
```

### Check logs

**Backend logs:**
- Console output shows real-time logging
- File logs: `backend/logs/app.log`

**Frontend logs:**
- Browser console (F12)
- Terminal shows build info

### Make changes

- Edit any Python file → backend auto-reloads
- Edit any TypeScript/React file → frontend auto-reloads
- Edit prompts in `shared/prompts/templates.py`
- Edit agent logic in `backend/agents/`

---

## 📊 Testing API Directly

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Simple research
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is AI?\"}"

# Streaming
curl -N http://localhost:8000/api/research/stream \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"Explain machine learning\"}"
```

### Using Swagger UI

1. Open http://localhost:8000/docs
2. Try the `/api/research` endpoint
3. Click "Try it out"
4. Enter your question
5. Click "Execute"

---

## 🔐 Security Notes

- ✅ Never commit .env files (already in .gitignore)
- ✅ Keep API keys secret
- ✅ Don't share keys in screenshots
- ✅ Rotate keys if exposed
- ✅ Use environment variables in production

---

## 🚀 Next Steps

Now that everything is running:

1. **Explore the code**
   - Check out `backend/agents/` for agent implementations
   - Look at `backend/graph/orchestrator.py` for LangGraph
   - Review `frontend/components/` for UI components

2. **Customize it**
   - Edit prompts to change teaching style
   - Modify UI colors and layout
   - Add new agents
   - Change models

3. **Test thoroughly**
   - Ask questions from different domains
   - Try different difficulty levels
   - Test edge cases

4. **Deploy (optional)**
   - Backend: Any Python hosting (Render, Railway, AWS)
   - Frontend: Vercel, Netlify, or any static host
   - See DEVELOPMENT.md for deploy guides

---

## 📞 Need Help?

- Check the main README.md for architecture details
- Review DEVELOPMENT.md for advanced topics
- Check logs for error messages
- Verify API keys are correct
- Ensure all dependencies are installed

---

## 🎓 Learning Resources

- **LangChain Docs**: https://python.langchain.com/
- **LangGraph Tutorial**: https://langchain-ai.github.io/langgraph/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Next.js Docs**: https://nextjs.org/docs
- **Tavily Docs**: https://docs.tavily.com/

---

<div align="center">
  <h2>🎉 Congratulations!</h2>
  <p>You now have a production-grade AI teaching system running!</p>
  <p><strong>Happy Learning! 🚀</strong></p>
</div>
