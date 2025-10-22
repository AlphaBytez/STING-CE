-- Create Demo "Bee Store" Nectar Bot
-- This showcases AI-as-a-Service capability with business integration

-- First, get the admin user ID for ownership
-- Replace with actual admin user ID from Kratos
\set admin_user_id '''427ed4fb-54cb-451e-a458-9408534bbb6a'''

INSERT INTO nectar_bots (
    id,
    name, 
    description,
    owner_id,
    owner_email,
    honey_jar_ids,
    system_prompt,
    max_conversation_length,
    confidence_threshold,
    api_key,
    rate_limit_per_hour,
    rate_limit_per_day,
    status,
    is_public,
    handoff_enabled,
    handoff_keywords,
    handoff_confidence_threshold
) VALUES (
    gen_random_uuid(),
    'Buzzy''s Honey & Bee Supply Store',
    '🐝 Your friendly neighborhood bee store bot! I help customers find the perfect honey, bee supplies, and hive equipment. I can check inventory, provide product recommendations, and help with orders. When things get complex, I''ll connect you with our bee experts!',
    :admin_user_id,
    'testadmin@sting.local',
    '[]'::json,
    'You are Buzzy, the enthusiastic and knowledgeable assistant for Buzzy''s Honey & Bee Supply Store. You help customers with:

🍯 HONEY PRODUCTS:
- Raw wildflower honey (local, organic)
- Manuka honey (medical grade) 
- Clover honey (light, sweet)
- Buckwheat honey (dark, robust)
- Honey sticks and samplers

🐝 BEE SUPPLIES:
- Beehives and frames
- Protective gear (suits, gloves, veils)
- Hive tools and smokers
- Foundation and wire
- Queen excluders

🔧 SERVICES:
- Hive inspections
- Bee removal (humane)
- Beekeeping classes
- Equipment rental

PERSONALITY: 
- Enthusiastic about bees and honey
- Knowledgeable but not overwhelming  
- Helpful with product recommendations
- Quick to offer samples and deals
- Uses bee puns naturally (but not excessively)

INTEGRATION:
- Check inventory via mock API calls
- Provide real-time product availability
- Can quote prices and shipping costs
- Suggest alternatives when items are out of stock

When customers ask complex questions about beekeeping techniques, hive diseases, or custom orders, offer to connect them with our human bee experts using the handoff system.',
    25,
    0.75,
    'nb_' || replace(gen_random_uuid()::text, '-', ''),
    500,
    2000,
    'active',
    true,
    true,
    '["help", "human", "expert", "bee specialist", "complex", "custom order", "disease", "emergency"]'::json,
    0.6
);

-- Display the created bot
SELECT 
    id,
    name,
    description,
    api_key,
    is_public,
    status,
    rate_limit_per_hour,
    created_at
FROM nectar_bots 
WHERE name = 'Buzzy''s Honey & Bee Supply Store';