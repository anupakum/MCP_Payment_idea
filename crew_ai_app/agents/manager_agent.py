"""
Manager Agent (Orchestrator) for intelligent routing of dispute resolution requests.

This agent analyzes incoming user requests and delegates to specialized agents:
- VerificationAgent: Customer/card/transaction verification
- DisputeDecisionAgent: Dispute processing and case creation
- CaseQueryAgent: Case status and history queries
"""

from typing import Dict, Any, Optional
import logging

from crewai import Agent, Task
from pydantic import BaseModel, Field

from ..llm_config import get_bedrock_llm_config

logger = logging.getLogger(__name__)


class ManagerInput(BaseModel):
    """Input model for manager agent requests."""
    request_type: str = Field(description="Type of request: 'verify_customer', 'verify_card', 'verify_transaction', 'case_status', 'customer_cases'")
    customer_id: Optional[str] = Field(None, description="Customer ID")
    card_number: Optional[str] = Field(None, description="Card number")
    transaction_id: Optional[str] = Field(None, description="Transaction ID")
    case_id: Optional[str] = Field(None, description="Case ID")


class DisputeManagerAgent:
    """Manager agent that orchestrates the dispute resolution workflow.
    
    This agent acts as an intelligent router, analyzing requests and delegating
    to the appropriate specialized agent based on the request type.
    """

    def __init__(self):
        """Initialize the dispute resolution manager agent."""
        # Get LLM configuration
        llm_config = get_bedrock_llm_config(temperature=0.1)
        
        # Create the manager agent with delegation capabilities
        self.agent = Agent(
            role="Dispute Resolution Manager",
            goal="""Intelligently route customer dispute requests to the appropriate specialized agent.
            Analyze incoming requests and delegate to:
            - VerificationAgent for customer/card/transaction verification
            - DisputeDecisionAgent for processing disputes and creating cases
            - CaseQueryAgent for retrieving case status and history
            Ensure efficient processing and coordinate multi-step workflows.""",
            backstory="""You are an experienced dispute resolution manager with deep knowledge
            of financial systems and customer service. You understand the entire dispute lifecycle
            and know exactly which specialized agent should handle each type of request.
            
            You coordinate complex workflows:
            - Customer verification flows through VerificationAgent
            - Transaction disputes go to VerificationAgent first, then DisputeDecisionAgent
            - Case queries are handled by CaseQueryAgent
            
            You ensure accuracy, efficiency, and excellent customer experience by routing
            requests intelligently and managing the workflow end-to-end.""",
            verbose=True,
            allow_delegation=True,  # CRITICAL: Enables delegation to other agents
            llm=llm_config["model"],
            **llm_config["llm_config"]
        )
        
        logger.info("Dispute Resolution Manager Agent initialized with delegation capabilities")

    def get_agent(self) -> Agent:
        """Get the CrewAI Agent instance.
        
        Returns:
            CrewAI Agent configured as manager with delegation
        """
        return self.agent

    def create_routing_task(self, request_description: str) -> Task:
        """Create a task for the manager to route the request.
        
        Args:
            request_description: Natural language description of the user's request
            
        Returns:
            CrewAI Task for the manager to execute
        """
        task = Task(
            description=f"""Analyze this dispute resolution request and delegate to the appropriate agent:
            
            Request: {request_description}
            
            Routing Rules:
            1. If request is about verifying a customer → Delegate to VerificationAgent
            2. If request is about verifying a card → Delegate to VerificationAgent
            3. If request is about filing a dispute on a transaction → Delegate to VerificationAgent first, then DisputeDecisionAgent
            4. If request is about checking case status → Delegate to CaseQueryAgent
            5. If request is about listing customer cases → Delegate to CaseQueryAgent
            
            Return the result from the delegated agent.""",
            agent=self.agent,
            expected_output="Structured response with success status and relevant data from the delegated agent"
        )
        return task
