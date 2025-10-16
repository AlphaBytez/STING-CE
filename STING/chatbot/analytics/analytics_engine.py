import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import asyncio

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """
    Analytics and reporting engine for Bee
    Tracks usage, performance, and generates insights
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('analytics_enabled', True)
        
        # In-memory storage (replace with database in production)
        self.interactions = []
        self.user_metrics = defaultdict(lambda: {
            'total_interactions': 0,
            'total_messages': 0,
            'tools_used': defaultdict(int),
            'sentiment_scores': [],
            'average_response_time': 0,
            'last_interaction': None
        })
        
        self.system_metrics = {
            'total_interactions': 0,
            'total_users': 0,
            'average_response_time': 0,
            'errors': [],
            'popular_tools': defaultdict(int),
            'peak_usage_times': defaultdict(int)
        }
        
        self.admin_actions = []
        self.error_logs = []
        
        # Aggregation task will be started when event loop is available
        self._aggregation_task = None
    
    async def initialize(self):
        """Initialize analytics engine"""
        logger.info("Analytics engine initialized")
        
        # Start aggregation task
        if self._aggregation_task is None:
            self._aggregation_task = asyncio.create_task(self._periodic_aggregation())
        
        # Load any persisted metrics
        # TODO: Implement persistence
    
    async def log_interaction(
        self,
        user_id: str,
        conversation_id: str,
        message_length: int,
        response_length: int,
        sentiment: Optional[Dict[str, float]],
        tools_used: List[Dict[str, Any]],
        processing_time: float,
        user_role: str = 'end_user'
    ):
        """Log a chat interaction"""
        if not self.enabled:
            return
        
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'conversation_id': conversation_id,
            'message_length': message_length,
            'response_length': response_length,
            'sentiment': sentiment,
            'tools_used': [t['name'] for t in tools_used] if tools_used else [],
            'processing_time': processing_time,
            'user_role': user_role
        }
        
        # Store interaction
        self.interactions.append(interaction)
        
        # Update user metrics
        user_metric = self.user_metrics[user_id]
        user_metric['total_interactions'] += 1
        user_metric['total_messages'] += 2  # User message + Bee response
        user_metric['last_interaction'] = datetime.now().isoformat()
        
        # Update tools usage
        for tool in tools_used:
            tool_name = tool['name']
            user_metric['tools_used'][tool_name] += 1
            self.system_metrics['popular_tools'][tool_name] += 1
        
        # Update sentiment tracking
        if sentiment:
            user_metric['sentiment_scores'].append(sentiment)
            # Keep only last 100 sentiment scores
            if len(user_metric['sentiment_scores']) > 100:
                user_metric['sentiment_scores'] = user_metric['sentiment_scores'][-100:]
        
        # Update response time
        current_avg = user_metric['average_response_time']
        total_interactions = user_metric['total_interactions']
        user_metric['average_response_time'] = (
            (current_avg * (total_interactions - 1) + processing_time) / total_interactions
        )
        
        # Update system metrics
        self.system_metrics['total_interactions'] += 1
        
        # Track peak usage times
        hour = datetime.now().hour
        self.system_metrics['peak_usage_times'][hour] += 1
        
        # Update system average response time
        sys_avg = self.system_metrics['average_response_time']
        sys_total = self.system_metrics['total_interactions']
        self.system_metrics['average_response_time'] = (
            (sys_avg * (sys_total - 1) + processing_time) / sys_total
        )
        
        # Keep only recent interactions (last 1000)
        if len(self.interactions) > 1000:
            self.interactions = self.interactions[-1000:]
    
    async def log_error(
        self,
        user_id: str,
        error_type: str,
        error_message: str,
        context: Dict[str, Any]
    ):
        """Log an error occurrence"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'error_type': error_type,
            'error_message': error_message,
            'context': context
        }
        
        self.error_logs.append(error_entry)
        self.system_metrics['errors'].append(error_entry)
        
        # Keep only recent errors
        if len(self.error_logs) > 500:
            self.error_logs = self.error_logs[-500:]
        
        if len(self.system_metrics['errors']) > 100:
            self.system_metrics['errors'] = self.system_metrics['errors'][-100:]
        
        logger.error(f"Analytics: Error logged - {error_type}: {error_message}")
    
    async def log_admin_action(
        self,
        admin_id: str,
        action: str,
        details: Dict[str, Any]
    ):
        """Log administrative actions"""
        action_entry = {
            'timestamp': datetime.now().isoformat(),
            'admin_id': admin_id,
            'action': action,
            'details': details
        }
        
        self.admin_actions.append(action_entry)
        
        # Keep only recent actions
        if len(self.admin_actions) > 1000:
            self.admin_actions = self.admin_actions[-1000:]
        
        logger.info(f"Analytics: Admin action - {admin_id} performed {action}")
    
    async def log_user_action(
        self,
        user_id: str,
        action: str,
        details: Dict[str, Any]
    ):
        """Log user actions (like clearing conversation)"""
        # For now, we'll track this as part of interactions
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details,
            'type': 'user_action'
        }
        
        self.interactions.append(interaction)
    
    async def generate_report(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        report_type: str = 'summary',
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Generate analytics report"""
        
        # Parse dates
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        else:
            start_dt = datetime.now() - timedelta(days=7)  # Default to last 7 days
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = datetime.now()
        
        # Filter interactions by date range
        filtered_interactions = [
            i for i in self.interactions
            if start_dt <= datetime.fromisoformat(i['timestamp']) <= end_dt
        ]
        
        # Generate report based on type
        if report_type == 'summary':
            return await self._generate_summary_report(
                filtered_interactions, 
                user_id, 
                start_dt, 
                end_dt,
                include_sensitive
            )
        elif report_type == 'detailed':
            return await self._generate_detailed_report(
                filtered_interactions,
                user_id,
                start_dt,
                end_dt,
                include_sensitive
            )
        elif report_type == 'usage':
            return await self._generate_usage_report(
                filtered_interactions,
                user_id,
                start_dt,
                end_dt
            )
        else:
            return {'error': f'Unknown report type: {report_type}'}
    
    async def _generate_summary_report(
        self,
        interactions: List[Dict[str, Any]],
        user_id: Optional[str],
        start_date: datetime,
        end_date: datetime,
        include_sensitive: bool
    ) -> Dict[str, Any]:
        """Generate summary report"""
        
        if user_id:
            # User-specific report
            user_interactions = [i for i in interactions if i.get('user_id') == user_id]
            user_metric = self.user_metrics.get(user_id, {})
            
            # Calculate sentiment summary
            sentiment_summary = {}
            if user_metric.get('sentiment_scores'):
                sentiment_keys = set()
                for score in user_metric['sentiment_scores']:
                    sentiment_keys.update(score.keys())
                
                for key in sentiment_keys:
                    values = [s.get(key, 0) for s in user_metric['sentiment_scores']]
                    sentiment_summary[key] = {
                        'average': sum(values) / len(values) if values else 0,
                        'trend': 'improving' if len(values) > 1 and values[-1] > values[0] else 'stable'
                    }
            
            report = {
                'report_type': 'user_summary',
                'user_id': user_id,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'metrics': {
                    'total_interactions': len(user_interactions),
                    'average_response_time': user_metric.get('average_response_time', 0),
                    'tools_used': dict(user_metric.get('tools_used', {})),
                    'sentiment_summary': sentiment_summary,
                    'last_interaction': user_metric.get('last_interaction')
                }
            }
            
            if include_sensitive:
                # Add conversation topics and other sensitive data
                report['metrics']['conversation_topics'] = self._extract_topics(user_interactions)
            
        else:
            # System-wide report
            report = {
                'report_type': 'system_summary',
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'metrics': {
                    'total_interactions': len(interactions),
                    'unique_users': len(set(i.get('user_id') for i in interactions)),
                    'average_response_time': self.system_metrics['average_response_time'],
                    'popular_tools': dict(self.system_metrics['popular_tools']),
                    'peak_hours': self._get_peak_hours(),
                    'error_count': len([e for e in self.system_metrics['errors'] 
                                      if start_date <= datetime.fromisoformat(e['timestamp']) <= end_date])
                }
            }
            
            if include_sensitive:
                report['metrics']['recent_errors'] = self.system_metrics['errors'][-10:]
        
        return report
    
    async def _generate_detailed_report(
        self,
        interactions: List[Dict[str, Any]],
        user_id: Optional[str],
        start_date: datetime,
        end_date: datetime,
        include_sensitive: bool
    ) -> Dict[str, Any]:
        """Generate detailed report with interaction breakdown"""
        
        # Start with summary
        report = await self._generate_summary_report(
            interactions, user_id, start_date, end_date, include_sensitive
        )
        
        # Add detailed breakdowns
        report['detailed_metrics'] = {
            'daily_breakdown': self._get_daily_breakdown(interactions),
            'tool_usage_timeline': self._get_tool_usage_timeline(interactions),
            'sentiment_timeline': self._get_sentiment_timeline(interactions),
            'response_time_distribution': self._get_response_time_distribution(interactions)
        }
        
        if include_sensitive and not user_id:
            # Add user rankings for admins
            report['user_rankings'] = {
                'most_active': self._get_most_active_users(interactions),
                'highest_tool_usage': self._get_highest_tool_users()
            }
        
        return report
    
    async def _generate_usage_report(
        self,
        interactions: List[Dict[str, Any]],
        user_id: Optional[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate usage-focused report"""
        
        report = {
            'report_type': 'usage',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'usage_metrics': {
                'total_messages': len(interactions) * 2,  # User + Bee messages
                'average_message_length': sum(i.get('message_length', 0) for i in interactions) / len(interactions) if interactions else 0,
                'average_response_length': sum(i.get('response_length', 0) for i in interactions) / len(interactions) if interactions else 0,
                'tool_usage_rate': len([i for i in interactions if i.get('tools_used')]) / len(interactions) if interactions else 0,
                'hourly_distribution': self._get_hourly_distribution(interactions),
                'weekday_distribution': self._get_weekday_distribution(interactions)
            }
        }
        
        if user_id:
            report['user_id'] = user_id
            report['usage_metrics']['user_rank'] = self._get_user_rank(user_id)
        
        return report
    
    def _extract_topics(self, interactions: List[Dict[str, Any]]) -> List[str]:
        """Extract conversation topics from interactions"""
        # Placeholder - in production, use NLP to extract topics
        return ['general', 'support', 'analytics']
    
    def _get_peak_hours(self) -> List[int]:
        """Get top 3 peak usage hours"""
        peak_times = sorted(
            self.system_metrics['peak_usage_times'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [hour for hour, _ in peak_times[:3]]
    
    def _get_daily_breakdown(self, interactions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get interaction count by day"""
        daily_counts = defaultdict(int)
        
        for interaction in interactions:
            date = datetime.fromisoformat(interaction['timestamp']).date()
            daily_counts[date.isoformat()] += 1
        
        return dict(daily_counts)
    
    def _get_tool_usage_timeline(self, interactions: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Get tool usage over time"""
        timeline = defaultdict(list)
        
        for interaction in interactions:
            if interaction.get('tools_used'):
                date = datetime.fromisoformat(interaction['timestamp']).date().isoformat()
                for tool in interaction['tools_used']:
                    timeline[date].append(tool)
        
        return dict(timeline)
    
    def _get_sentiment_timeline(self, interactions: List[Dict[str, Any]]) -> List[Dict]:
        """Get sentiment changes over time"""
        timeline = []
        
        for interaction in interactions:
            if interaction.get('sentiment'):
                timeline.append({
                    'timestamp': interaction['timestamp'],
                    'sentiment': interaction['sentiment']
                })
        
        return timeline
    
    def _get_response_time_distribution(self, interactions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get distribution of response times"""
        distribution = {
            '<1s': 0,
            '1-2s': 0,
            '2-5s': 0,
            '5-10s': 0,
            '>10s': 0
        }
        
        for interaction in interactions:
            time = interaction.get('processing_time', 0)
            if time < 1:
                distribution['<1s'] += 1
            elif time < 2:
                distribution['1-2s'] += 1
            elif time < 5:
                distribution['2-5s'] += 1
            elif time < 10:
                distribution['5-10s'] += 1
            else:
                distribution['>10s'] += 1
        
        return distribution
    
    def _get_hourly_distribution(self, interactions: List[Dict[str, Any]]) -> Dict[int, int]:
        """Get interaction count by hour"""
        hourly = defaultdict(int)
        
        for interaction in interactions:
            hour = datetime.fromisoformat(interaction['timestamp']).hour
            hourly[hour] += 1
        
        return dict(hourly)
    
    def _get_weekday_distribution(self, interactions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get interaction count by weekday"""
        weekdays = defaultdict(int)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for interaction in interactions:
            weekday = datetime.fromisoformat(interaction['timestamp']).weekday()
            weekdays[day_names[weekday]] += 1
        
        return dict(weekdays)
    
    def _get_most_active_users(self, interactions: List[Dict[str, Any]], limit: int = 10) -> List[Dict]:
        """Get most active users"""
        user_counts = defaultdict(int)
        
        for interaction in interactions:
            user_counts[interaction.get('user_id')] += 1
        
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'user_id': user_id, 'interaction_count': count}
            for user_id, count in sorted_users[:limit]
        ]
    
    def _get_highest_tool_users(self, limit: int = 10) -> List[Dict]:
        """Get users who use tools the most"""
        tool_users = []
        
        for user_id, metrics in self.user_metrics.items():
            total_tool_usage = sum(metrics['tools_used'].values())
            if total_tool_usage > 0:
                tool_users.append({
                    'user_id': user_id,
                    'total_tool_usage': total_tool_usage,
                    'favorite_tools': sorted(
                        metrics['tools_used'].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:3]
                })
        
        return sorted(tool_users, key=lambda x: x['total_tool_usage'], reverse=True)[:limit]
    
    def _get_user_rank(self, user_id: str) -> Dict[str, Any]:
        """Get user's rank in various metrics"""
        all_users = list(self.user_metrics.keys())
        
        # Sort by total interactions
        interaction_rank = sorted(
            all_users,
            key=lambda u: self.user_metrics[u]['total_interactions'],
            reverse=True
        ).index(user_id) + 1 if user_id in all_users else None
        
        return {
            'interaction_rank': interaction_rank,
            'total_users': len(all_users),
            'percentile': (1 - interaction_rank / len(all_users)) * 100 if interaction_rank else None
        }
    
    async def get_total_interactions(self) -> int:
        """Get total number of interactions"""
        return self.system_metrics['total_interactions']
    
    async def flush(self):
        """Flush any pending analytics data"""
        # In production, this would persist data to database
        logger.info(f"Flushing analytics data: {self.system_metrics['total_interactions']} interactions")
    
    async def _periodic_aggregation(self):
        """Periodically aggregate and clean up metrics"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Update unique users count
                self.system_metrics['total_users'] = len(self.user_metrics)
                
                # Clean up old interactions (keep last 7 days)
                cutoff = datetime.now() - timedelta(days=7)
                self.interactions = [
                    i for i in self.interactions
                    if datetime.fromisoformat(i['timestamp']) > cutoff
                ]
                
                # Clean up old errors
                self.error_logs = [
                    e for e in self.error_logs
                    if datetime.fromisoformat(e['timestamp']) > cutoff
                ]
                
                logger.info("Completed periodic analytics aggregation")
                
            except Exception as e:
                logger.error(f"Error in periodic aggregation: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Health check for analytics engine"""
        try:
            # Check if aggregation task is running (if started)
            if self._aggregation_task and self._aggregation_task.done():
                return False
            
            # Basic functionality check
            _ = len(self.interactions)
            _ = len(self.user_metrics)
            
            return True
        except:
            return False