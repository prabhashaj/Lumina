"""
Example test file for the AI Research Teaching Agent backend

Run with: pytest test_agents.py -v
"""
import pytest
from unittest.mock import Mock, patch
import asyncio

from agents.intent_classifier import IntentClassifierAgent
from shared.schemas.models import DifficultyLevel, QuestionType


class TestIntentClassifier:
    """Test suite for Intent Classifier Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance for testing"""
        return IntentClassifierAgent()
    
    @pytest.mark.asyncio
    async def test_beginner_question(self, agent):
        """Test classification of a beginner-level question"""
        question = "What is photosynthesis?"
        
        result = await agent.analyze(question)
        
        assert result is not None
        assert isinstance(result.difficulty_level, DifficultyLevel)
        assert result.confidence > 0
        
    @pytest.mark.asyncio
    async def test_advanced_question(self, agent):
        """Test classification of an advanced question"""
        question = "Explain the quantum mechanical treatment of hydrogen atom wavefunctions"
        
        result = await agent.analyze(question)
        
        assert result is not None
        assert result.question_type in [QuestionType.MATHEMATICAL, QuestionType.CONCEPTUAL]
        
    @pytest.mark.asyncio
    async def test_requires_visuals(self, agent):
        """Test detection of questions requiring visuals"""
        question = "Show me how the water cycle works"
        
        result = await agent.analyze(question)
        
        assert result.requires_visuals == True
        
    @pytest.mark.asyncio
    async def test_requires_code(self, agent):
        """Test detection of programming questions"""
        question = "How do I implement a binary search in Python?"
        
        result = await agent.analyze(question)
        
        # Should detect code requirement
        assert result.requires_code == True or result.question_type == QuestionType.PRACTICAL


class TestSearchAgent:
    """Test suite for Search Agent"""
    
    def test_search_initialization(self):
        """Test search agent can be initialized"""
        from agents.search_agent import WebSearchAgent
        
        agent = WebSearchAgent()
        assert agent is not None
        assert agent.max_results > 0


class TestOrchestrator:
    """Test suite for the LangGraph Orchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance"""
        from graph.orchestrator import ResearchOrchestrator
        return ResearchOrchestrator()
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes all agents"""
        assert orchestrator.intent_agent is not None
        assert orchestrator.search_agent is not None
        assert orchestrator.content_agent is not None
        assert orchestrator.teaching_agent is not None
        
    def test_graph_structure(self, orchestrator):
        """Test that the LangGraph is properly structured"""
        assert orchestrator.graph is not None
        # Graph should have multiple nodes
        # This is a basic structural test


@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for the complete workflow"""
    
    @pytest.mark.asyncio
    async def test_simple_question_flow(self):
        """Test a simple question through the full workflow"""
        from graph.orchestrator import ResearchOrchestrator
        from shared.schemas.models import ResearchRequest
        
        orchestrator = ResearchOrchestrator()
        request = ResearchRequest(
            question="What is the water cycle?"
        )
        
        # This will make real API calls if keys are configured
        # In production tests, you'd mock the API calls
        # result = await orchestrator.process_question(request)
        
        # For now, just test the structure exists
        assert orchestrator is not None


@pytest.mark.unit
class TestDataModels:
    """Test Pydantic models"""
    
    def test_research_request_validation(self):
        """Test ResearchRequest model validation"""
        from shared.schemas.models import ResearchRequest
        
        # Valid request
        request = ResearchRequest(question="Test question")
        assert request.question == "Test question"
        
        # Test validation - question too short
        with pytest.raises(Exception):
            ResearchRequest(question="ab")  # Less than min_length
            
    def test_intent_analysis_model(self):
        """Test IntentAnalysis model"""
        from shared.schemas.models import IntentAnalysis, DifficultyLevel, QuestionType
        
        intent = IntentAnalysis(
            difficulty_level=DifficultyLevel.BEGINNER,
            question_type=QuestionType.CONCEPTUAL,
            requires_visuals=True,
            requires_math=False,
            requires_code=False,
            key_concepts=["test"],
            confidence=0.9
        )
        
        assert intent.difficulty_level == DifficultyLevel.BEGINNER
        assert intent.confidence == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
