
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.finance import FinanceAgent
from decimal import Decimal

@pytest.mark.asyncio
async def test_finance_agent_add_income():
    # Mock DB
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    
    # Create Agent
    agent = FinanceAgent(mock_db, "tenant-id", "user-id", "ru")
    
    # Test valid income
    result = await agent._add_income(50000, "Salary")
    
    assert "✅" in result
    assert "50,000" in result
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_finance_agent_add_expense_invalid():
    # Mock DB
    mock_db = AsyncMock()
    
    # Create Agent
    agent = FinanceAgent(mock_db, "tenant-id", "user-id", "ru")
    
    # Test invalid amount
    result = await agent._add_expense(-100, "Bad")
    
    assert "❌" in result
    mock_db.add.assert_not_called()
