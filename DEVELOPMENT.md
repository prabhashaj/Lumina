# Development Tips & Best Practices

## Quick Development Commands

### Backend
```bash
cd backend

# Run with auto-reload
python main.py

# Run with uvicorn directly
uvicorn main:app --reload --port 8000

# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy .
```

### Frontend
```bash
cd frontend

# Development
npm run dev

# Build
npm run build

# Production
npm start

# Lint
npm run lint

# Type check
npx tsc --noEmit
```

## Testing the API

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Simple research request
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"question": "What is photosynthesis?"}'

# Streaming request
curl -N http://localhost:8000/api/research/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain quantum mechanics"}'
```

### Using httpie

```bash
http POST http://localhost:8000/api/research question="How does AI work?"
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/research",
    json={"question": "What is machine learning?"}
)

print(response.json())
```

## Debugging

### Backend Debugging

1. Enable detailed logging:
```python
# In backend/config/settings.py
log_level: str = "DEBUG"
```

2. Add breakpoints in your IDE or use pdb:
```python
import pdb; pdb.set_trace()
```

3. Check LangGraph execution:
```python
# The orchestrator logs each node execution
# Look for: "NODE: Classifying intent..."
```

### Frontend Debugging

1. Open React DevTools
2. Check Network tab for SSE streams
3. Console.log in components
4. Use Next.js debug mode:
```bash
NODE_OPTIONS='--inspect' npm run dev
```

## Environment-Specific Configs

### Development
```env
# backend/.env
LOG_LEVEL=DEBUG
API_HOST=localhost
CACHE_TTL=300  # Short cache for testing
```

### Production
```env
# backend/.env
LOG_LEVEL=INFO
API_HOST=0.0.0.0
CACHE_TTL=3600  # Longer cache
MAX_RETRIES=3
```

## Performance Optimization

### Backend

1. Enable Redis caching
2. Use connection pooling
3. Implement request queuing
4. Add rate limiting

### Frontend

1. Use Next.js Image optimization
2. Implement virtual scrolling for long conversations
3. Add proper loading states
4. Optimize bundle size

## Common Issues & Solutions

### Issue: "Module not found" in backend
**Solution**: Ensure you're in the virtual environment
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: API keys not working
**Solution**: Check .env file is in the correct location
```bash
# backend/.env should be directly in backend/ folder
# Not in backend/config/ or anywhere else
```

### Issue: CORS errors in frontend
**Solution**: Check backend CORS settings
```python
# backend/config/settings.py
cors_origins: List[str] = ["http://localhost:3000"]
```

### Issue: Streaming not working
**Solution**: Check nginx/proxy settings. Disable buffering:
```
proxy_buffering off;
X-Accel-Buffering: no
```

### Issue: Images not loading
**Solution**: Check Next.js image domains
```javascript
// frontend/next.config.js
images: {
  domains: ['localhost'],
  remotePatterns: [{ protocol: 'https', hostname: '**' }]
}
```

## Monitoring in Production

### Key Metrics to Track

1. **Response Time**: Target < 10s average
2. **Error Rate**: Target < 1%
3. **Cache Hit Rate**: Target > 70%
4. **API Usage**: Track OpenAI/Tavily usage
5. **User Sessions**: Active learning sessions

### Logging

All agents log their execution:
```python
logger.info(f"Processing question: {question}")
logger.error(f"Error in agent: {str(e)}")
```

Check logs:
```bash
tail -f backend/logs/app.log
```

## Advanced Customization

### Adding a New Agent

1. Create agent file:
```python
# backend/agents/my_agent.py
class MyCustomAgent:
    async def process(self, state: AgentState) -> AgentState:
        # Your logic here
        return state
```

2. Add to orchestrator:
```python
# backend/graph/orchestrator.py
self.my_agent = MyCustomAgent()
workflow.add_node("my_agent", self.my_agent_node)
workflow.add_edge("previous_node", "my_agent")
```

### Customizing Prompts

Edit templates in:
```python
# shared/prompts/templates.py
CUSTOM_PROMPT = """Your custom prompt here..."""
```

### Changing Models

```env
# backend/.env
PRIMARY_LLM_MODEL=gpt-4-turbo-preview  # or claude-3-opus, etc.
EMBEDDING_MODEL=text-embedding-3-large
```

## Security Best Practices

1. **Never commit .env files** (already in .gitignore)
2. **Use environment variables** for all secrets
3. **Implement rate limiting** in production
4. **Validate all inputs** (already done with Pydantic)
5. **Use HTTPS** in production
6. **Implement authentication** for production use

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Tavily API](https://docs.tavily.com/)
- [OpenAI API](https://platform.openai.com/docs)
