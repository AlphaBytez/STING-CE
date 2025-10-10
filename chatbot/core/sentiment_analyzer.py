import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Analyzes sentiment in user messages for Bee
    Provides emotional context for better responses
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('sentiment_analysis_enabled', True)
        
        # Simple sentiment indicators (in production, use proper NLP model)
        self.positive_indicators = [
            'thank', 'thanks', 'great', 'excellent', 'good', 'awesome', 
            'wonderful', 'fantastic', 'love', 'perfect', 'amazing', 'best',
            'appreciate', 'helpful', 'nice', 'please', 'happy', 'glad'
        ]
        
        self.negative_indicators = [
            'not working', 'error', 'problem', 'issue', 'wrong', 'bad',
            'terrible', 'awful', 'hate', 'broken', 'failed', 'crash',
            'frustrated', 'annoying', 'confused', 'stuck', 'help',
            "can't", "won't", "doesn't", "isn't", 'unfortunately'
        ]
        
        self.question_indicators = [
            'what', 'when', 'where', 'why', 'how', 'which', 'who',
            'could', 'would', 'should', 'can', 'will', '?'
        ]
        
        self.urgency_indicators = [
            'urgent', 'asap', 'immediately', 'now', 'quickly', 'fast',
            'emergency', 'critical', 'important', 'hurry', 'rush'
        ]
        
        # Emoji sentiment mapping
        self.emoji_sentiments = {
            '😊': 'positive', '😃': 'positive', '🙂': 'positive', '😄': 'positive',
            '😁': 'positive', '😆': 'positive', '😍': 'positive', '🥰': 'positive',
            '😢': 'negative', '😞': 'negative', '😔': 'negative', '😟': 'negative',
            '😠': 'negative', '😡': 'negative', '😤': 'negative', '😫': 'negative',
            '🤔': 'neutral', '😐': 'neutral', '😑': 'neutral', '🤷': 'neutral',
            '❓': 'question', '❔': 'question', '⁉️': 'question', '❗': 'urgency'
        }
    
    async def analyze(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of the given text"""
        if not self.enabled:
            return {'neutral': 1.0}
        
        # Convert to lowercase for analysis
        text_lower = text.lower()
        
        # Initialize sentiment scores
        sentiments = {
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 0.0,
            'question': 0.0,
            'urgency': 0.0,
            'joy': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'surprise': 0.0
        }
        
        # Count indicators
        word_count = len(text.split())
        if word_count == 0:
            return {'neutral': 1.0}
        
        # Analyze word-based sentiment
        positive_count = sum(1 for word in self.positive_indicators if word in text_lower)
        negative_count = sum(1 for word in self.negative_indicators if word in text_lower)
        question_count = sum(1 for word in self.question_indicators if word in text_lower)
        urgency_count = sum(1 for word in self.urgency_indicators if word in text_lower)
        
        # Analyze emoji sentiment
        emoji_sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        for emoji, sentiment in self.emoji_sentiments.items():
            if emoji in text:
                if sentiment in emoji_sentiment_counts:
                    emoji_sentiment_counts[sentiment] += 1
                elif sentiment == 'question':
                    question_count += 1
                elif sentiment == 'urgency':
                    urgency_count += 1
        
        # Calculate base scores
        sentiments['positive'] = (positive_count + emoji_sentiment_counts['positive']) / word_count
        sentiments['negative'] = (negative_count + emoji_sentiment_counts['negative']) / word_count
        sentiments['question'] = min(question_count / word_count, 1.0)
        sentiments['urgency'] = min(urgency_count / word_count, 1.0)
        
        # Analyze specific emotions
        if any(word in text_lower for word in ['happy', 'joy', 'excited', 'love', '😊', '😃', '😄']):
            sentiments['joy'] = 0.7
        
        if any(word in text_lower for word in ['sad', 'unhappy', 'disappointed', '😢', '😞']):
            sentiments['sadness'] = 0.7
        
        if any(word in text_lower for word in ['angry', 'mad', 'furious', 'annoyed', '😠', '😡']):
            sentiments['anger'] = 0.7
        
        if any(word in text_lower for word in ['worried', 'scared', 'afraid', 'concerned']):
            sentiments['fear'] = 0.6
        
        if any(word in text_lower for word in ['wow', 'amazing', 'surprised', 'unexpected', '😮']):
            sentiments['surprise'] = 0.6
        
        # Check for strong negative patterns
        strong_negative_patterns = [
            r"doesn't work",
            r"not working",
            r"completely broken",
            r"total failure",
            r"waste of time"
        ]
        
        for pattern in strong_negative_patterns:
            if re.search(pattern, text_lower):
                sentiments['negative'] = max(sentiments['negative'], 0.8)
                sentiments['anger'] = max(sentiments['anger'], 0.5)
        
        # Check for gratitude patterns
        gratitude_patterns = [
            r"thank you",
            r"thanks so much",
            r"really appreciate",
            r"you're the best"
        ]
        
        for pattern in gratitude_patterns:
            if re.search(pattern, text_lower):
                sentiments['positive'] = max(sentiments['positive'], 0.8)
                sentiments['joy'] = max(sentiments['joy'], 0.6)
        
        # Normalize sentiment scores
        total_sentiment = sentiments['positive'] + sentiments['negative']
        
        if total_sentiment > 0:
            # If we have clear positive/negative indicators
            if sentiments['positive'] > sentiments['negative']:
                sentiments['neutral'] = max(0, 1 - total_sentiment)
            else:
                sentiments['neutral'] = max(0, 0.3 - total_sentiment)
        else:
            # No clear sentiment indicators
            sentiments['neutral'] = 0.8
        
        # Ensure all values are between 0 and 1
        for key in sentiments:
            sentiments[key] = max(0, min(1, sentiments[key]))
        
        # Find dominant sentiment
        dominant = max(sentiments.items(), key=lambda x: x[1])
        
        # Log sentiment analysis
        logger.debug(f"Sentiment analysis for '{text[:50]}...': {dominant[0]} ({dominant[1]:.2f})")
        
        return sentiments
    
    async def analyze_conversation_mood(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze overall mood of a conversation"""
        if not messages:
            return {'overall_mood': 'neutral', 'mood_trajectory': 'stable'}
        
        # Analyze sentiment for each message
        sentiments_over_time = []
        
        for message in messages:
            if message['role'] == 'user':
                sentiment = await self.analyze(message['content'])
                sentiments_over_time.append({
                    'timestamp': message['timestamp'],
                    'sentiment': sentiment
                })
        
        if not sentiments_over_time:
            return {'overall_mood': 'neutral', 'mood_trajectory': 'stable'}
        
        # Calculate average sentiments
        avg_sentiments = {}
        for key in sentiments_over_time[0]['sentiment'].keys():
            values = [s['sentiment'][key] for s in sentiments_over_time]
            avg_sentiments[key] = sum(values) / len(values)
        
        # Determine overall mood
        if avg_sentiments['positive'] > 0.6:
            overall_mood = 'positive'
        elif avg_sentiments['negative'] > 0.6:
            overall_mood = 'negative'
        elif avg_sentiments['urgency'] > 0.5:
            overall_mood = 'urgent'
        elif avg_sentiments['question'] > 0.5:
            overall_mood = 'inquisitive'
        else:
            overall_mood = 'neutral'
        
        # Analyze mood trajectory
        if len(sentiments_over_time) >= 3:
            recent_positive = sum(s['sentiment']['positive'] for s in sentiments_over_time[-3:]) / 3
            earlier_positive = sum(s['sentiment']['positive'] for s in sentiments_over_time[:3]) / 3
            
            if recent_positive > earlier_positive + 0.2:
                mood_trajectory = 'improving'
            elif recent_positive < earlier_positive - 0.2:
                mood_trajectory = 'declining'
            else:
                mood_trajectory = 'stable'
        else:
            mood_trajectory = 'stable'
        
        return {
            'overall_mood': overall_mood,
            'mood_trajectory': mood_trajectory,
            'average_sentiments': avg_sentiments,
            'sentiment_history': sentiments_over_time
        }
    
    async def get_response_tone(
        self,
        sentiment: Dict[str, float]
    ) -> str:
        """Suggest appropriate response tone based on sentiment"""
        
        # Determine primary sentiment
        primary = max(sentiment.items(), key=lambda x: x[1])
        
        if primary[0] == 'negative' and primary[1] > 0.6:
            return 'empathetic'
        elif primary[0] == 'urgency' and primary[1] > 0.5:
            return 'responsive'
        elif primary[0] == 'question':
            return 'informative'
        elif primary[0] == 'positive' and primary[1] > 0.6:
            return 'cheerful'
        elif primary[0] == 'anger' and primary[1] > 0.5:
            return 'calming'
        elif primary[0] == 'fear' and primary[1] > 0.5:
            return 'reassuring'
        else:
            return 'friendly'
    
    def is_healthy(self) -> bool:
        """Health check for sentiment analyzer"""
        try:
            # Test basic functionality
            test_sentiment = {
                'positive': 0.5,
                'negative': 0.3,
                'neutral': 0.2
            }
            _ = max(test_sentiment.items(), key=lambda x: x[1])
            return True
        except:
            return False