#!/usr/bin/env python3
"""
Nectar Bot Demo Data Generator

Creates sample Nectar Bots directly in the database for demo/testing purposes.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models.nectar_bot_models import NectarBot
from app.models.user_models import User
from app.database import db
from app import create_app
from typing import List, Dict, Any
import uuid as uuid_module

# Sample Nectar Bot Configurations
SAMPLE_BOTS = [
    {
        "name": "Customer Support Bot",
        "description": "AI assistant for handling customer inquiries and support tickets",
        "system_prompt": "You are a helpful customer support AI assistant. Provide friendly, professional assistance to customers. If you cannot help with a request, politely escalate to a human agent.",
        "honey_jar_ids": [],
        "max_conversation_length": 30,
        "confidence_threshold": 0.75,
        "rate_limit_per_hour": 200,
        "rate_limit_per_day": 2000,
        "is_public": True,
        "handoff_enabled": True,
        "handoff_keywords": ["human", "agent", "help", "support", "escalate", "speak to someone"],
        "handoff_confidence_threshold": 0.6
    },
    {
        "name": "Technical Documentation Bot",
        "description": "Answers questions about technical documentation and API guides",
        "system_prompt": "You are a technical documentation expert. Help users find information in technical docs, explain APIs, and provide code examples when relevant.",
        "honey_jar_ids": [],
        "max_conversation_length": 20,
        "confidence_threshold": 0.8,
        "rate_limit_per_hour": 100,
        "rate_limit_per_day": 1000,
        "is_public": False,
        "handoff_enabled": True,
        "handoff_keywords": ["complex", "don't understand", "need help", "escalate"],
        "handoff_confidence_threshold": 0.65
    },
    {
        "name": "HR Policy Assistant",
        "description": "Helps employees understand company policies and HR procedures",
        "system_prompt": "You are an HR policy assistant. Answer questions about company policies, benefits, and procedures. Always maintain confidentiality and professionalism.",
        "honey_jar_ids": [],
        "max_conversation_length": 25,
        "confidence_threshold": 0.7,
        "rate_limit_per_hour": 50,
        "rate_limit_per_day": 500,
        "is_public": False,
        "handoff_enabled": True,
        "handoff_keywords": ["HR representative", "speak to HR", "human", "urgent"],
        "handoff_confidence_threshold": 0.7
    },
    {
        "name": "Product FAQ Bot",
        "description": "Answers frequently asked questions about products and services",
        "system_prompt": "You are a product expert. Answer questions about our products, features, pricing, and availability. Be enthusiastic and helpful!",
        "honey_jar_ids": [],
        "max_conversation_length": 15,
        "confidence_threshold": 0.75,
        "rate_limit_per_hour": 300,
        "rate_limit_per_day": 3000,
        "is_public": True,
        "handoff_enabled": True,
        "handoff_keywords": ["sales", "purchase", "speak to sales", "human"],
        "handoff_confidence_threshold": 0.65
    },
    {
        "name": "Security Compliance Bot",
        "description": "Assists with security protocols and compliance questions",
        "system_prompt": "You are a security compliance assistant. Help users understand security policies, compliance requirements, and incident response procedures. Security is paramount.",
        "honey_jar_ids": [],
        "max_conversation_length": 20,
        "confidence_threshold": 0.85,
        "rate_limit_per_hour": 50,
        "rate_limit_per_day": 500,
        "is_public": False,
        "handoff_enabled": True,
        "handoff_keywords": ["security team", "incident", "urgent", "breach", "help"],
        "handoff_confidence_threshold": 0.75
    }
]


def get_admin_kratos_id(app):
    """Get admin user's Kratos identity ID from database"""
    import requests
    try:
        # Query Kratos admin API for identities
        response = requests.get(
            'https://kratos:4434/admin/identities',
            verify=False,
            timeout=5
        )

        if response.status_code == 200:
            identities = response.json()
            for identity in identities:
                traits = identity.get('traits', {})
                if traits.get('email') == 'admin@sting.local':
                    return identity.get('id')

        # Fallback: generate a consistent UUID for admin
        print("⚠️  Could not fetch admin ID from Kratos, using generated UUID")
        return str(uuid_module.uuid5(uuid_module.NAMESPACE_DNS, 'admin@sting.local'))

    except Exception as e:
        print(f"⚠️  Error fetching admin ID: {e}, using generated UUID")
        return str(uuid_module.uuid5(uuid_module.NAMESPACE_DNS, 'admin@sting.local'))


def create_nectar_bot_db(bot_config: Dict[str, Any], app, admin_id) -> bool:
    """Create a single Nectar Bot directly in database"""
    try:
        with app.app_context():
            # Create bot with admin user
            bot = NectarBot(
                name=bot_config['name'],
                description=bot_config['description'],
                owner_id=admin_id,
                owner_email='admin@sting.local',
                system_prompt=bot_config['system_prompt'],
                honey_jar_ids=bot_config.get('honey_jar_ids', []),
                max_conversation_length=bot_config.get('max_conversation_length', 20),
                confidence_threshold=bot_config.get('confidence_threshold', 0.7),
                rate_limit_per_hour=bot_config.get('rate_limit_per_hour', 100),
                rate_limit_per_day=bot_config.get('rate_limit_per_day', 1000),
                is_public=bot_config.get('is_public', False),
                handoff_enabled=bot_config.get('handoff_enabled', True),
                handoff_keywords=bot_config.get('handoff_keywords', ['help', 'human']),
                handoff_confidence_threshold=bot_config.get('handoff_confidence_threshold', 0.6)
            )

            db.session.add(bot)
            db.session.commit()

            print(f"✅ Created bot: {bot_config['name']}")
            print(f"   ID: {bot.id}")
            print(f"   API Key: {bot.api_key[:20]}...{bot.api_key[-8:]}")
            return True

    except Exception as e:
        print(f"❌ Error creating bot '{bot_config['name']}': {str(e)}")
        return False


def main():
    print("🐝 Nectar Bot Demo Data Generator\n")
    print(f"Creating {len(SAMPLE_BOTS)} demo bots directly in database...\n")

    # Create Flask app
    app = create_app()

    # Get admin Kratos ID dynamically
    print("📋 Fetching admin user ID from Kratos...")
    admin_id = get_admin_kratos_id(app)
    print(f"✅ Using admin ID: {admin_id}\n")

    created_count = 0
    failed_bots = []

    for bot_config in SAMPLE_BOTS:
        if create_nectar_bot_db(bot_config, app, admin_id):
            created_count += 1
        else:
            failed_bots.append(bot_config['name'])

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"✅ Successfully created: {created_count} bots")
    print(f"❌ Failed: {len(failed_bots)} bots")

    if failed_bots:
        print(f"\nFailed bots: {', '.join(failed_bots)}")

    print("\n✨ Demo data generation complete!")
    print("Visit https://localhost:8443/dashboard/nectar-bots to see your bots.\n")

    return 0 if created_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
