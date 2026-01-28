/*
 * STING Capabilities Guard & Standard Prompt Templates
 * Use these to prevent hallucination and ensure accurate STING documentation
 */

/*
 ============================================================================
 SECTION 1: STING VERIFIED CAPABILITIES (Use for reference)
 ============================================================================

 CORE FEATURES (Verified - DO NOT hallucinate beyond these):
 -------------------------------------------------------------------------
 • Knowledge management platform
 • AI document analysis & Q&A (via RAG pipeline)
 • Document storage, indexing, and retrieval
 • Chat interface with Bee assistant
 • Kratos authentication (Ory Kratos)
 • Vault integration for secrets management
 • PostgreSQL database
 • Redis caching
 • Multi-theme support (Modern, Retro, ASCII, Garden Galaxy, etc.)
 • Docker containerized deployment
 • Theme system with CSS variables
 • Bee Reports (QEBee/Report Bee) - quality assurance reporting

 SERVICES (Verified):
 -------------------------------------------------------------------------
 • app: Main Flask application
 • frontend: React/Ant Design UI
 • chatbot: Chat service
 • knowledge: Knowledge base service
 • external-ai: External AI integrations
 • kratos: Authentication
 • vault: Secrets management
 • report-bee: Quality assurance reporting
 • public-bee: Public-facing AI
 • report-worker: Report generation

 WHAT STING DOES NOT HAVE (Hallucination Red Flags):
 -------------------------------------------------------------------------
 ✗ Threat detection / intrusion detection
 ✗ Honey pots / honey jars / deception technology
 ✗ Real-time security monitoring
 ✗ Automated incident response
 ✗ Encrypted data stream analysis
 ✗ Network security features
 ✗ GPS spoofing protection
 ✗ Drone/UAV specific security
 ✗ Automated breach detection
 ✗ Anomaly detection in data streams

 ============================================================================
 SECTION 2: STANDARD PROMPT TEMPLATES
 ============================================================================

 ----------------------------------------------------------------------------
 TEMPLATE A: Accurate STING Feature Report
 ----------------------------------------------------------------------------
 Generate a report about STING's capabilities for: [FEATURE_AREA]

 RULES:
 1. Only include features from the VERIFIED CAPABILITIES list above
 2. If a requested feature is not in the verified list, state "STING does
    not currently have this capability - it may be planned for a future release"
 3. Do NOT elaborate on features not in the verified list
 4. Do NOT invent technical details to sound authoritative
 5. If the prompt assumes STING has a feature it doesn't have, clarify this
    before proceeding

 EXAMPLE:
 User: "Generate a report about STING's security features"
 Response should include:
   - Kratos authentication
   - Vault integration
   - Audit logging
   - What STING does NOT have (threat detection, IDS, etc.)

 ----------------------------------------------------------------------------
 TEMPLATE B: Feature Comparison (Actual vs Requested)
 ----------------------------------------------------------------------------
 Compare STING's capabilities to: [COMPETITOR_OR_FEATURE]

 VERIFICATION STEP FIRST:
   □ Is this feature in STING's verified capabilities?
   □ If NO, clearly state the feature doesn't exist in STING
   □ If YES, describe only the verified implementation

 DO NOT:
   - Invent capabilities to make STING seem competitive
   - Extrapolate "planned" features as if they exist
   - Confuse "on roadmap" with "implemented"

 ----------------------------------------------------------------------------
 TEMPLATE C: Technical Documentation
 ----------------------------------------------------------------------------
 Generate technical documentation for: [COMPONENT_OR_FEATURE]

 CONSTRAINTS:
 1. Base all claims on actual STING codebase / architecture
 2. Include file paths and code references where possible
 3. Distinguish between:
    - "STING has X" (verified)
    - "STING is planned to have X" (roadmap)
    - "X is a common feature in similar platforms" (general knowledge)
 4. Do not conflate general industry knowledge with STING-specific features

 ----------------------------------------------------------------------------
 TEMPLATE D: Use Case Generation (Conservative)
 ----------------------------------------------------------------------------
 Generate use cases for: [USE_CASE_DOMAIN]

 RULES:
 1. Start with STING's actual capabilities
 2. Only propose use cases that match those capabilities
 3. If the domain requires features STING doesn't have, say:
    "This use case would require [missing feature], which STING does not
    currently support. STING could support this use case if that feature
    were implemented."

 EXAMPLE DOMAIN: Cybersecurity
   STING can:
   - Store and analyze security documentation
   - Answer questions from knowledge base
   - Provide audit logs of document access

   STING cannot (do not claim):
   - Detect threats in real-time
   - Deploy honey pots
   - Monitor network traffic

 ============================================================================
 SECTION 3: HALLUCINATION PREVENTION CHECKLIST
 ============================================================================

 Before generating ANY response about STING capabilities:

 1. CAPABILITY VERIFICATION
    □ Is this feature in the verified capabilities list?
    □ Can I point to actual code/repository that implements this?

 2. SOURCE VERIFICATION
    □ Am I citing actual STING documentation or code?
    □ Am I citing external sources and presenting them as STING features?

 3. CLAIM ACCURACY
    □ Are all technical details verified from STING source?
    □ Am I using passive voice to avoid committing to unverified claims?

 4. ROADMAP vs IMPLEMENTED
    □ Is this feature implemented or just planned?
    □ Am I presenting roadmap items as if they're shipped features?

 RESPONSE STRUCTURE FOR UNVERIFIED FEATURES:
 -------------------------------------------------------------------------
 "STING does not currently have [FEATURE].

 This feature is:
   □ On the roadmap for future development
   □ Not currently planned (as of my knowledge date)

 STING's current security capabilities include:
   - [Actual capability 1]
   - [Actual capability 2]

 If you need [FEATURE], this would require:
   - [Implementation requirements]
"

 ============================================================================
 SECTION 4: QUICK REFERENCE - WHAT STING IS
 ============================================================================

 STING IS:
 • A secure knowledge management system
 • An AI-powered document Q&A platform
 • A RAG (Retrieval-Augmented Generation) application
 • A document repository with search and chat interfaces
 • A multi-theme web application

 STING IS NOT:
 • A security monitoring system
 • A threat detection platform
 • A deception technology (honeypot) system
 • An intrusion detection system
 • A network security tool
 • A drone/UAV security solution

 ============================================================================
 */

 /*
  * Usage in Bee System Prompt:
  *
  * Include this file's content (Section 1 + Section 3) in Bee's system prompt
  * to establish baseline accuracy requirements.
  *
  * For specific report generation, use Section 2 templates as guides.
  */
