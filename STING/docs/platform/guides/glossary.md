# STING Glossary - The Hive Dictionary 🐝

## Core Concepts

### 🐝 **Bee (B. STING)**
The AI assistant at the heart of STING. A helpful, intelligent agent that processes requests, manages data, and provides insights while maintaining security and privacy.

### 🍯 **Honey Jar**
A secure data container that stores and protects sensitive information. Honey Jars can connect to external data sources and package knowledge for analysis or sharing. Think of it as a sealed jar of valuable data that only authorized users can access.

### 🏠 **Hive**
The administrative control center where system administrators manage the entire STING ecosystem. From the Hive, admins can:
- Configure data connections
- Manage user permissions
- Monitor system health
- Set security policies

### 🐝 **Worker Bee**
Specialized connectors that gather data from external sources (databases, APIs, file systems). Worker Bees:
- Fly out to collect "nectar" (data)
- Know which sources they're authorized to access
- Return data securely to Honey Jars
- Can work individually or in swarms for larger tasks

### 🌻 **Nectar**
Raw data collected from external sources by Worker Bees. This is unprocessed information that needs to be refined into "honey" (processed knowledge).

### 🍯 **Honey**
Processed, refined, and AI-ready knowledge derived from raw data. Honey is what makes reports sweet with insights!

### 🏭 **Hive Scrambler**
The privacy-preserving engine that detects and replaces sensitive information (PII) with temporary variables before sending data to external AI services. It ensures that personal information never leaves your infrastructure. Works in tandem with the Scrubbing Engine for comprehensive data privacy.

### 🧵 **Nectar Stitcher**
The component that reconstructs scrambled data back into readable reports. After AI processing, it replaces temporary variables with the original data, creating the final report.

### 💼 **Pollen**
Metadata and schema information about data sources. Pollen helps Worker Bees understand the structure and relationships in the data they collect.

### 🌺 **Pollen Basket**
A feature for collecting and organizing various types of data and insights from multiple sources, similar to how bees collect pollen from different flowers.

### 👑 **Queen Bee**
The system administrator or primary admin user with full control over the STING platform.

### 🛡️ **Drone**
- In security context: Read-only users who can view reports but not modify data
- In computing context: Distributed processing nodes for handling large-scale operations

### 🏠 **Honeycomb**
The structured storage system within Honey Jars, organizing data in efficient, hexagonal patterns (metaphorically speaking).

### 🏗️ **Honey Comb**
Reusable data source configuration templates that define how Worker Bees connect to and extract data from external sources. Honey Combs can either continuously feed existing Honey Jars or generate new ones through snapshots and dumps. Think of them as blueprints for building data connections.

### 📚 **Comb Library**
A collection of pre-built Honey Comb templates for common data sources (databases, APIs, file systems). The library accelerates data integration by providing tested, secure configurations.

### 🔧 **Custom Comb**
A user-defined Honey Comb configuration tailored to specific data sources or unique requirements. Custom Combs can be shared within teams or published to the Comb Library.

### 🧹 **Scrubbing Engine**
The privacy-preserving component that detects and removes/masks sensitive information during data ingestion. Works in conjunction with Honey Combs to ensure compliance with data protection regulations like GDPR, CCPA, and HIPAA.

### 💃 **Bee Dance**
The synchronization protocol between different components of STING, ensuring all parts work in harmony. Named after the waggle dance bees use to communicate.

### 💃 **Waggles**
Intelligent notifications in STING, named after the bee waggle dance. Waggles can be:
- System-generated alerts (report complete, anomaly detected)
- Data-driven notifications (threshold breached, pattern matched)
- Custom-configured for specific business needs
- Installed locally for on-premise processing
- Routed to various channels (email, Slack, in-app)

### 🥇 **Royal Jelly**
Premium features or privileged data access available only to enterprise users or specific high-level roles.

### 🌐 **Swarm**
Multiple meanings in STING:
1. A coordinated group of Worker Bees working together on large data collection or processing tasks
2. In messaging: Group conversations in Swarm Chat (Enterprise feature) where teams collaborate with AI assistance

### 🔔 **Buzz**
Notifications, alerts, or messages within the STING system. When something important happens, STING will "buzz" you.

### 🏥 **Hive Doctor**
Diagnostic and troubleshooting tools that help maintain system health and resolve issues.

### 🗺️ **Flight Path**
The configured route or connection details for Worker Bees to reach external data sources.

### 🎯 **Sting Operation**
A security audit or penetration test to ensure system integrity.

## Technical Terms

### **PII (Personally Identifiable Information)**
Data that can identify a specific individual, such as names, email addresses, phone numbers, or social security numbers.

### **Scrambling**
The process of replacing sensitive data with temporary placeholders before external processing.

### **Tokenization**
Converting sensitive data into non-sensitive tokens that can be mapped back to the original data.

### **Air-gapped**
A security measure where a system is physically isolated from unsecured networks.

### **mTLS (Mutual TLS)**
A security protocol where both client and server authenticate each other using certificates.

### **WebAuthn**
A web standard for passwordless authentication using biometrics or security keys. Highly recommended for STING users handling sensitive data due to its superior security and convenience.

### **Passkey**
A passwordless authentication method using public key cryptography, often with biometric verification. STING's preferred authentication method for the best balance of security and user experience.

### **RAG (Retrieval-Augmented Generation)**
An AI technique that combines information retrieval with text generation for more accurate responses.

### **Vector Database**
A specialized database (like ChromaDB) optimized for storing and searching high-dimensional vectors, used for semantic search.

### **LLM (Large Language Model)**
AI models like GPT-4, Claude, or Llama that can understand and generate human-like text.

### **CE (Community Edition)**
The open-source version of STING with core features for individual and small team use.

### **Enterprise/Enterprise+**
Premium versions of STING with advanced features, support, and scalability options.

## Operations & Features

### **Bee Chat**
STING's intelligent messaging system for conversing with the AI assistant, accessing data insights, and managing tasks.

### **Swarm Chat**
Enterprise feature enabling group conversations with shared AI assistance and team collaboration.

### **Report Generation**
The process of creating AI-powered insights from your data while maintaining privacy through scrambling.

### **Knowledge Monetization**
The ability to package and sell insights or processed knowledge through the Honey Jar marketplace.

### **Compliance Mode**
Special operating modes that ensure adherence to regulations like HIPAA, GDPR, or SOX.

### **Audit Trail**
A comprehensive log of all actions taken within the system for security and compliance purposes.

### **Row-Level Security (RLS)**
Fine-grained access control that restricts data access at the individual record level.

### **Field-Level Encryption**
Encryption applied to specific sensitive fields within a dataset.

### **Zero Trust**
A security model that requires verification for every interaction, assuming no implicit trust.

## Common Phrases

### "Collecting Nectar"
The process of gathering data from external sources.

### "Making Honey"
Processing raw data into actionable insights.

### "Buzzing for Support"
Requesting help or raising a support ticket.

### "Sending a Waggle"
Dispatching a notification or alert to team members.

### "Dancing the Data"
Synchronizing information between systems or team members.

### "Joining the Swarm"
Adding a new node to distributed processing or becoming part of the STING community.

### "Sealed Honey Jar"
A finalized, encrypted data container ready for sharing or archival.

### "Empty Hive"
A fresh STING installation with no data or users configured.

### "Busy as a Bee"
System under high load or processing many requests.

### "Sweet as Honey"
Particularly valuable or well-processed insights.

## Acronyms

- **STING**: Secure Trusted Intelligence and Networking Guardian
- **B. STING**: The Bee assistant (the B can stand for "Bee" or "Bot")
- **API**: Application Programming Interface
- **RBAC**: Role-Based Access Control
- **SSO**: Single Sign-On
- **TLS**: Transport Layer Security
- **GDPR**: General Data Protection Regulation
- **HIPAA**: Health Insurance Portability and Accountability Act
- **SOX**: Sarbanes-Oxley Act
- **PCI-DSS**: Payment Card Industry Data Security Standard
- **MVP**: Minimum Viable Product
- **SLA**: Service Level Agreement
- **CSM**: Customer Success Manager

---

*This glossary is continuously updated as STING evolves. For technical API references, see the API documentation.*

*Last Updated: January 2025*