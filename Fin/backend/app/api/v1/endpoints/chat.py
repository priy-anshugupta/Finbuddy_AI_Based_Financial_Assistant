"""
Chat API endpoints for agent interactions
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
import asyncio

from app.dependencies import get_db, CurrentUser
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas.agent_response import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationList,
    MessageResponse
)


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/conversations", response_model=ConversationList)
async def get_conversations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """Get user's conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    # Add message count
    conversation_list = []
    for conv in conversations:
        result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        messages = result.scalars().all()
        
        conv_dict = {
            "id": conv.id,
            "title": conv.title,
            "summary": conv.summary,
            "active_orchestrator": conv.active_orchestrator,
            "active_agents": conv.active_agents,
            "is_active": conv.is_active,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "message_count": len(messages)
        }
        conversation_list.append(ConversationResponse(**conv_dict))
    
    return ConversationList(
        items=conversation_list,
        total=len(conversation_list)
    )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation."""
    conversation = Conversation(
        user_id=current_user.id,
        title=conversation_data.title or "New Conversation",
        context=conversation_data.context or {}
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        active_orchestrator=conversation.active_orchestrator,
        active_agents=conversation.active_agents,
        is_active=conversation.is_active,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific conversation."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get message count
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    )
    messages = result.scalars().all()
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        active_orchestrator=conversation.active_orchestrator,
        active_agents=conversation.active_agents,
        is_active=conversation.is_active,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(messages)
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """Get messages for a conversation."""
    # Verify conversation belongs to user
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = result.scalars().all()
    
    return [
        MessageResponse(
            id=m.id,
            role=m.role.value,
            content=m.content,
            agent_name=m.agent_name,
            orchestrator=m.orchestrator,
            tool_calls=m.tool_calls,
            created_at=m.created_at
        )
        for m in messages
    ]


@router.post("/send", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get agent response."""
    # Get or create conversation
    if chat_request.conversation_id:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == chat_request.conversation_id)
            .where(Conversation.user_id == current_user.id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        conversation = Conversation(
            user_id=current_user.id,
            title="New Conversation"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    
    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=chat_request.message
    )
    db.add(user_message)
    
    # TODO: Process message through agent orchestrators
    # This is where we'll integrate with the agent system
    
    # For now, return a placeholder response
    agent_response = await process_with_agents(
        message=chat_request.message,
        user=current_user,
        conversation=conversation,
        context=chat_request.context,
        db=db
    )
    
    # Save assistant message
    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=agent_response["message"],
        agent_name=agent_response["agent_name"],
        orchestrator=agent_response["orchestrator"]
    )
    db.add(assistant_message)
    
    # Update conversation
    conversation.updated_at = datetime.utcnow()
    conversation.active_orchestrator = agent_response["orchestrator"]
    
    await db.commit()
    
    return ChatResponse(
        message=agent_response["message"],
        conversation_id=conversation.id,
        agent_name=agent_response["agent_name"],
        orchestrator=agent_response["orchestrator"],
        suggestions=agent_response.get("suggestions"),
        actions=agent_response.get("actions")
    )


@router.post("/send/stream")
async def send_message_stream(
    chat_request: ChatRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Send a message and stream the agent response."""
    
    async def generate():
        # TODO: Implement streaming with agents
        # This will stream agent thinking, tool calls, and responses
        
        events = [
            {"event": "thinking", "agent": "router", "content": "Analyzing your request..."},
            {"event": "thinking", "agent": "money_growth", "content": "Looking at your spending patterns..."},
            {"event": "response", "agent": "money_growth", "content": "Based on your transaction history, I can see..."}
        ]
        
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0.5)
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    await db.delete(conversation)
    await db.commit()


async def process_with_agents(
    message: str,
    user,
    conversation,
    context: Optional[dict],
    db: AsyncSession
) -> dict:
    """
    Process user message through the agent system.
    
    This function routes the message to the appropriate orchestrator
    based on the intent and context.
    """
    # TODO: Integrate with actual agent orchestrators
    # For now, return a mock response
    
    # Simple intent detection
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["spend", "expense", "transaction", "budget", "money"]):
        orchestrator = "orchestrator_1"
        agent_name = "money_growth_agent"
        response = (
            "I've analyzed your recent transactions. "
            "Your spending this month is within budget. "
            "Would you like me to provide a detailed breakdown by category?"
        )
        suggestions = [
            "Show spending by category",
            "Compare with last month",
            "Set a budget alert"
        ]
    elif any(word in message_lower for word in ["invest", "stock", "mutual fund", "sip", "portfolio"]):
        orchestrator = "orchestrator_2"
        agent_name = "investment_agent"
        response = (
            "Based on your risk profile and financial goals, "
            "I can help you with investment recommendations. "
            "What specific aspect would you like to explore?"
        )
        suggestions = [
            "View portfolio summary",
            "Get investment recommendations",
            "Analyze market trends"
        ]
    elif any(word in message_lower for word in ["tax", "itr", "credit card", "loan"]):
        orchestrator = "orchestrator_3"
        agent_name = "itr_agent"
        response = (
            "I can help you with tax planning and financial products. "
            "Would you like to calculate your tax liability or explore "
            "credit card/loan options?"
        )
        suggestions = [
            "Calculate income tax",
            "Compare credit cards",
            "Check loan eligibility"
        ]
    else:
        orchestrator = "orchestrator_1"
        agent_name = "router"
        response = (
            "Hello! I'm your AI financial assistant. I can help you with:\n\n"
            "💰 **Money Management** - Track spending, budgets, categorize transactions\n"
            "📈 **Investments** - Portfolio analysis, stock research, SIP recommendations\n"
            "🏦 **Financial Products** - Credit cards, loans, tax planning\n\n"
            "What would you like to know?"
        )
        suggestions = [
            "Show my spending summary",
            "Analyze my portfolio",
            "Calculate my tax"
        ]
    
    return {
        "message": response,
        "agent_name": agent_name,
        "orchestrator": orchestrator,
        "suggestions": suggestions,
        "actions": []
    }
