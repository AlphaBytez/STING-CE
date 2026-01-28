# Bee Prompt Enhancement Integration Guide

This guide explains how to integrate the enhanced prompt system into bee_server.py.

## Quick Integration Steps

1. **Import the prompt configuration** at the top of bee_server.py:
```python
from chatbot.prompts.bee_prompt_config import BeePromptConfig
```

2. **Update the generate_bee_response function** to use the enhanced prompts:
   - Replace the existing prompt building logic with BeePromptConfig.generate_prompt()
   - Add sentiment-based response enhancements
   - Include feature-specific context

3. **Key improvements**:
   - Dynamic personality based on user sentiment
   - Role-specific response guidelines
   - Feature-aware context injection
   - Better conversation continuity
   - Enhanced fallback responses

## Configuration Options

### Environment Variables
```bash
# Optional: Override default system prompt
export BEE_SYSTEM_PROMPT="Custom system prompt..."

# Optional: Set default personality
export BEE_PERSONALITY="technical"  # or "friendly", "empathetic", etc.

# Optional: Enable verbose prompting
export BEE_VERBOSE_PROMPTS="true"
```

### Dynamic Adjustments
The system automatically adjusts based on:
- User role (admin, end_user, support_staff, developer)
- Detected sentiment (frustrated, confused, satisfied, urgent)
- Query type (security, technical, general)
- Conversation history

## Example Usage

### Basic Implementation
```python
# In bee_server.py, replace the prompt building section with:

from chatbot.prompts.bee_prompt_config import BeePromptConfig

# Determine user sentiment
sentiment_category = "neutral"
if sentiment and sentiment.get('frustration', 0) > 0.5:
    sentiment_category = "frustrated"

# Generate customized prompt
system_prompt = BeePromptConfig.generate_prompt(
    user_role=user_role.value,
    sentiment=sentiment_category,
    conversation_id=conversation_id
)

# Add feature context
feature_context = BeePromptConfig.get_feature_context(message)
if feature_context:
    system_prompt += f"\n\n{feature_context}"

# Use the prompt with LLM
prompt = f"{system_prompt}\n\nUser: {message}\nBee: "
```

### Response Enhancement
```python
# After getting LLM response, enhance it based on sentiment
enhanced_response = BeePromptConfig.enhance_response(
    llm_response,
    sentiment_category
)
```

## Testing the Enhanced Prompts

1. **Test different sentiments**:
```bash
# Frustrated user
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "This login system is so confusing! Help!", "user_id": "test-user"}'

# Technical query
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I integrate the REST API with my Python app?", "user_id": "dev-user"}'
```

2. **Test role-based responses**:
   - Admin users get detailed technical information
   - End users get simplified, actionable guidance
   - Developers get code examples and API references

## Benefits

1. **Consistency**: All responses follow STING branding and tone
2. **Context-Awareness**: Responses adapt to user needs and emotional state
3. **Knowledge Integration**: Automatic inclusion of relevant platform features
4. **Maintainability**: Centralized prompt configuration
5. **Extensibility**: Easy to add new personalities or response patterns

## Customization

To add new features or modify behavior:

1. **Add new personality types** in `PERSONALITIES` dict
2. **Define new response guidelines** in `RESPONSE_GUIDELINES`
3. **Add feature knowledge** in `FEATURE_KNOWLEDGE`
4. **Create sentiment adjustments** in `SENTIMENT_ADJUSTMENTS`

## Monitoring

Log prompt generation for debugging:
```python
logger.debug(f"Generated prompt for {user_role} with {sentiment_category} sentiment")
logger.debug(f"Feature context included: {bool(feature_context)}")
```

## Future Enhancements

1. **Multi-language support**: Add language detection and localized responses
2. **Learning system**: Track successful response patterns
3. **A/B testing**: Compare different prompt strategies
4. **Custom tools integration**: Add tool-specific response formatting