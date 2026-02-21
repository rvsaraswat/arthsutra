"""
Local LLM integration using Ollama for conversational AI.
Provides financial insights and explanations.
"""
import requests
from typing import Dict, List, Optional
import logging
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with local LLM via Ollama."""

    def __init__(self, base_url: str = None, model: str = None):
        """Initialize Ollama client."""
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = 120  # 2 minutes timeout

    def chat(
        self,
        message: str,
        context: Dict = None,
        system_prompt: str = None
    ) -> Dict:
        """
        Send a message to the LLM and get a response.

        Args:
            message: User message
            context: Optional context (transactions, analytics, etc.)
            system_prompt: Optional custom system prompt

        Returns:
            Response dictionary with content and metadata
        """
        try:
            # Build system prompt
            system = system_prompt or self._get_default_system_prompt()

            # Add context if provided
            if context:
                system += f"\n\nContext Information:\n{self._format_context(context)}"

            # Prepare request
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": message}
                ],
                "stream": False
            }

            # Send request
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            return {
                "content": result.get("message", {}).get("content", ""),
                "model": result.get("model", self.model),
                "total_duration": result.get("total_duration", 0),
                "load_duration": result.get("load_duration", 0),
                "prompt_eval_count": result.get("prompt_eval_count", 0),
                "eval_count": result.get("eval_count", 0),
                "timestamp": datetime.utcnow().isoformat()
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Ollama: {e}")
            return {
                "content": f"Error: Unable to connect to local LLM. Please ensure Ollama is running with model '{self.model}'.",
                "model": self.model,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for financial assistant."""
        return """You are Arthsutra, an AI-powered Personal Finance Manager. Your role is to help users understand their finances, provide insights, and offer recommendations.

Your capabilities:
1. Explain financial concepts in simple terms
2. Analyze spending patterns and identify trends
3. Provide budgeting advice
4. Answer questions about transactions and accounts
5. Offer investment and savings recommendations
6. Help with goal planning

Guidelines:
- Be clear, concise, and helpful
- Use Indian Rupee (₹) for currency
- Reference specific data when possible
- Provide actionable recommendations
- If you don't have enough information, ask clarifying questions
- Be objective and non-judgmental
- Focus on privacy and security - never ask for sensitive credentials"""

    def _format_context(self, context: Dict) -> str:
        """Format context information for the LLM."""
        formatted = []

        if 'transactions' in context:
            formatted.append(f"Recent Transactions (last 10):")
            for tx in context['transactions'][-10:]:
                formatted.append(f"- {tx['date']}: {tx['description']} - ₹{tx['amount']} ({tx['type']})")

        if 'cashflow' in context:
            cf = context['cashflow']
            formatted.append(f"\nCash Flow Summary:")
            formatted.append(f"- Total Income: ₹{cf.get('total_income', 0):,.2f}")
            formatted.append(f"- Total Expenses: ₹{cf.get('total_expenses', 0):,.2f}")
            formatted.append(f"- Net Cashflow: ₹{cf.get('net_cashflow', 0):,.2f}")
            formatted.append(f"- Savings Rate: {cf.get('savings_rate', 0):.2f}%")

        if 'budget' in context:
            formatted.append(f"\nBudget Status:")
            for budget in context['budget'][:5]:
                formatted.append(f"- {budget['name']}: ₹{budget['amount']:,} (Utilized: {budget.get('utilization', 0):.1f}%)")

        if 'goals' in context:
            formatted.append(f"\nFinancial Goals:")
            for goal in context['goals'][:5]:
                formatted.append(f"- {goal['name']}: ₹{goal['current_amount']:,} / ₹{goal['target_amount']:,} ({goal.get('progress', 0):.1f}%)")

        return "\n".join(formatted)

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if error
        """
        try:
            payload = {
                "model": settings.EMBEDDING_MODEL,
                "prompt": text
            }

            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result.get("embedding")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting embedding: {e}")
            return None

    def list_models(self) -> List[Dict]:
        """List available models in Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            return result.get("models", [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing models: {e}")
            return []

    def check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


class FinancialChatBot:
    """Financial chatbot with specialized prompts and tools."""

    def __init__(self, ollama_client: OllamaClient):
        """Initialize financial chatbot."""
        self.client = ollama_client

    def analyze_expense_spike(self, spike_data: Dict) -> str:
        """Analyze and explain expense spike."""
        prompt = f"""Analyze this expense spike and provide insights:

Period: {spike_data['period']}
Expense Amount: ₹{spike_data['expenses']:,.2f}
Average Expense: ₹{spike_data['average_expense']:,.2f}
Percentage Above Average: {spike_data['percentage_above_average']:.2f}

Please provide:
1. What might have caused this spike
2. Whether this is concerning
3. Recommendations to avoid similar spikes in the future
4. Any budget adjustments that might help

Keep your response concise and actionable."""

        response = self.client.chat(prompt)
        return response['content']

    def assess_affordability(self, goal_data: Dict) -> str:
        """Assess if a goal is affordable."""
        prompt = f"""Assess if this financial goal is affordable:

Goal: {goal_data['name']}
Target Amount: ₹{goal_data['target_amount']:,.2f}
Target Date: {goal_data['target_date']}
Current Savings: ₹{goal_data['current_amount']:,.2f}
Time Remaining: {goal_data['time_remaining']}

Please provide:
1. Whether this goal is achievable
2. Monthly savings needed to reach the goal
3. Any risks or considerations
4. Alternative suggestions if needed

Keep your response practical and realistic."""

        response = self.client.chat(prompt)
        return response['content']

    def recommend_portfolio_rebalance(self, portfolio_data: Dict) -> str:
        """Recommend portfolio rebalancing."""
        prompt = f"""Analyze this portfolio and provide rebalancing recommendations:

Current Portfolio:
{portfolio_data}

Please provide:
1. Current risk level assessment
2. Suggested asset allocation
3. Specific rebalancing actions
4. Expected outcomes

Keep your recommendations aligned with conservative financial principles."""

        response = self.client.chat(prompt)
        return response['content']

    def simulate_scenario(self, scenario_data: Dict) -> str:
        """Simulate financial scenario."""
        prompt = f"""Simulate this financial scenario and provide analysis:

Scenario: {scenario_data['scenario']}
Details: {scenario_data['details']}

Please provide:
1. Potential outcomes
2. Risk factors
3. Mitigation strategies
4. Key considerations

Be thorough but concise."""

        response = self.client.chat(prompt)
        return response['content']

    def explain_transaction(self, transaction_data: Dict) -> str:
        """Explain a transaction to the user."""
        prompt = f"""Explain this transaction to the user:

Description: {transaction_data['description']}
Amount: ₹{transaction_data['amount']:,.2f}
Date: {transaction_data['date']}
Category: {transaction_data.get('category', 'Uncategorized')}

Please provide:
1. What this transaction likely represents
2. Whether it's normal or unusual
3. Any tips for managing similar transactions
4. Budgeting advice if relevant

Keep your explanation simple and helpful."""

        response = self.client.chat(prompt)
        return response['content']

    def get_financial_summary(self, context: Dict) -> str:
        """Get comprehensive financial summary."""
        prompt = f"""Provide a comprehensive financial summary based on this data:

{self._format_context(context)}

Please provide:
1. Overall financial health assessment
2. Key strengths and areas for improvement
3. Top 3 recommendations
4. Any concerns to watch

Be encouraging but realistic."""

        response = self.client.chat(prompt)
        return response['content']

    def _format_context(self, context: Dict) -> str:
        """Format context for summary."""
        return self.client._format_context(context)