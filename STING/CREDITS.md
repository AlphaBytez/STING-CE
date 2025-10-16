# Open Source Credits & Acknowledgements

STING (Security Threat Intelligence Next Generation) is built upon the incredible work of many open source projects and communities. We extend our heartfelt gratitude to all the maintainers, contributors, and organizations that make these projects possible.

## Frontend (React Application)

### Core Framework & Build Tools
- **[React](https://reactjs.org/)** - Meta (Facebook) - MIT License
  - The foundational JavaScript library powering our user interface
  - Enables component-based architecture and modern UI development
- **[Create React App](https://create-react-app.dev/)** - Meta (Facebook) - MIT License
  - Zero-configuration build tooling and development environment
- **[CRACO](https://craco.js.org/)** - CRACO Team - MIT License
  - Configuration override for Create React App
- **[React Router](https://reactrouter.com/)** - Remix Software - MIT License
  - Declarative routing for single-page applications

### UI Framework & Design System
- **[Ant Design](https://ant.design/)** - Ant Design Team - MIT License
  - Enterprise-class UI design language and comprehensive React component library
  - Provides our primary design system foundation with theming capabilities
  - Built-in accessibility features and internationalization support
- **[Material-UI (MUI)](https://mui.com/)** - MUI Team - MIT License
  - React components implementing Google's Material Design
  - Rich component library with advanced theming
- **[Tailwind CSS](https://tailwindcss.com/)** - Tailwind Labs - MIT License
  - Utility-first CSS framework for rapid custom styling
  - Enables responsive design and consistent spacing
- **[Lucide React](https://lucide.dev/)** - Lucide Contributors - ISC License
  - Beautiful and consistent icon library with extensive icon set
- **[Chart.js](https://www.chartjs.org/)** - Chart.js Contributors - MIT License
  - Simple yet flexible JavaScript charting library
- **[Recharts](https://recharts.org/)** - Recharts Group - MIT License
  - Composable charting library built on React components

### State Management & Utilities
- **[React Intl](https://formatjs.io/docs/react-intl/)** - FormatJS - BSD-3-Clause License
  - Internationalization and localization library
- **[Axios](https://axios-http.com/)** - Matt Zabriskie - MIT License
  - Promise-based HTTP client for API communication
- **[nanoid](https://github.com/ai/nanoid)** - Andrey Sitnik - MIT License
  - Tiny, secure, URL-safe unique string ID generator
- **[react-markdown](https://remarkjs.github.io/react-markdown/)** - Titus Wormer - MIT License
  - Markdown component for React applications
- **[remark-gfm](https://github.com/remarkjs/remark-gfm)** - Titus Wormer - MIT License
  - GitHub Flavored Markdown plugin for remark
- **[qrcode](https://www.npmjs.com/package/qrcode)** - Ryan Day - MIT License
  - QR code generation for TOTP enrollment flows
- **[class-variance-authority](https://cva.style/)** - Joe Bell - Apache License 2.0
  - Utility for managing CSS class name variants
- **[clsx](https://github.com/lukeed/clsx)** - Luke Edwards - MIT License
  - Tiny utility for constructing className strings conditionally
- **[tailwind-merge](https://github.com/dcastil/tailwind-merge)** - Dany Castillo - MIT License
  - Utility for merging Tailwind CSS classes without conflicts

### Authentication & Security (Frontend)
- **[@ory/client](https://www.npmjs.com/package/@ory/client)** - Ory Corp - Apache License 2.0
  - Official Ory Kratos JavaScript client library
  - Handles authentication flows and identity management
- **[@ory/elements](https://www.npmjs.com/package/@ory/elements)** - Ory Corp - Apache License 2.0
  - Pre-built React components for Ory authentication flows
  - Provides styled forms for login, registration, and settings
- **[@simplewebauthn/browser](https://simplewebauthn.dev/)** - Matthew Miller - MIT License
  - WebAuthn/Passkey client library for browser
  - Simplifies biometric and hardware key authentication

## Authentication & Security

### Identity Management
- **[Ory Kratos](https://www.ory.sh/kratos/)** - Ory Corp - Apache License 2.0
  - Modern, cloud-native identity and user management system
  - Provides secure authentication flows and session management
  - WebAuthn and passwordless authentication support

### Security Standards
- **[WebAuthn](https://webauthn.io/)** - W3C Standard
  - Web Authentication API for passwordless authentication
  - Enables biometric and hardware key authentication
- **[HashiCorp Vault](https://www.vaultproject.io/)** - HashiCorp - Mozilla Public License 2.0
  - Secrets management and data protection platform
  - Secure storage for API keys, passwords, and certificates

## Development Tools & Code Quality

### Linting & Formatting
- **[ESLint](https://eslint.org/)** - ESLint Team - MIT License
  - JavaScript and React code linting and style enforcement
- **[Prettier](https://prettier.io/)** - Prettier Team - MIT License
  - Opinionated code formatter for consistent code style

### Package Management
- **[npm](https://www.npmjs.com/)** - npm, Inc. - Artistic License 2.0
  - Package manager for JavaScript and Node.js

## Backend & Infrastructure

### Python Ecosystem
- **[Python](https://www.python.org/)** - Python Software Foundation - PSF License
  - Core programming language for backend services
- **[FastAPI](https://fastapi.tiangolo.com/)** - Sebastián Ramírez - MIT License
  - Modern, fast web framework for building APIs and external AI service bridge
- **[Pydantic](https://pydantic-docs.helpmanual.io/)** - Samuel Colvin - MIT License
  - Data validation and settings management using Python type annotations
- **[Flask](https://flask.palletsprojects.com/)** - Pallets Team - BSD-3-Clause License
  - Lightweight WSGI web application framework for main API
- **[gunicorn](https://gunicorn.org/)** - Benoit Chesneau - MIT License
  - Python WSGI HTTP Server for production Flask deployments
- **[uvicorn](https://www.uvicorn.org/)** - Tom Christie - BSD 3-Clause License
  - Lightning-fast ASGI server implementation
- **[httpx](https://www.python-httpx.org/)** - Tom Christie - BSD 3-Clause License
  - Modern HTTP client for Python with async support
- **[cryptography](https://cryptography.io/)** - Python Cryptographic Authority - Apache License 2.0 and BSD
  - Cryptographic recipes and primitives for Python
- **[pandas](https://pandas.pydata.org/)** - NumFOCUS - BSD 3-Clause License
  - Powerful data analysis and manipulation library
- **[scikit-learn](https://scikit-learn.org/)** - scikit-learn developers - BSD 3-Clause License
  - Machine learning library for predictive data analysis
- **[spacy](https://spacy.io/)** - Explosion AI - MIT License
  - Industrial-strength natural language processing

### Flask Extensions
- **[Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)** - Pallets - BSD-3-Clause License
  - Flask extension for SQLAlchemy database integration
- **[Flask-Migrate](https://flask-migrate.readthedocs.io/)** - Miguel Grinberg - MIT License
  - Database migrations for Flask with Alembic
- **[Flask-CORS](https://flask-cors.readthedocs.io/)** - Cory Dolphin - MIT License
  - Cross-Origin Resource Sharing (CORS) handling for Flask
- **[Flask-SocketIO](https://flask-socketio.readthedocs.io/)** - Miguel Grinberg - MIT License
  - WebSocket support for real-time communication
- **[Flask-Session](https://flask-session.readthedocs.io/)** - Pallets Community - BSD-3-Clause License
  - Server-side session support for Flask

### Python Utilities
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - Saurabh Kumar - BSD-3-Clause License
  - Read environment variables from .env files
- **[PyYAML](https://pyyaml.org/)** - Ingy döt Net, Kirill Simonov - MIT License
  - YAML parser and emitter for Python configuration files
- **[python-multipart](https://github.com/andrew-d/python-multipart)** - Andrew Dunham - Apache License 2.0
  - Streaming multipart parser for Python, used in file uploads
- **[hvac](https://hvac.readthedocs.io/)** - Ian Unruh - Apache License 2.0
  - HashiCorp Vault API client for Python secrets management
- **[pyotp](https://github.com/pyauth/pyotp)** - PyAuth - MIT License
  - Python One-Time Password library for TOTP/HOTP implementation
- **[phonenumbers](https://github.com/daviddrysdale/python-phonenumbers)** - David Drysdale - Apache License 2.0
  - Python port of Google's libphonenumber for phone number validation
- **[qrcode](https://github.com/lincolnloop/python-qrcode)** - Lincoln Loop - BSD License
  - QR code generation for TOTP enrollment
- **[reportlab](https://www.reportlab.com/)** - ReportLab - BSD-like License
  - PDF generation library for Python reports and exports
- **[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)** - Amazon Web Services - Apache License 2.0
  - AWS SDK for Python, used for S3 and cloud storage integration

### AI & Machine Learning Infrastructure
- **[Ollama](https://ollama.ai/)** - Ollama Team - MIT License
  - Local LLM server providing cross-platform AI model deployment
  - Enables Mac, Linux, and Windows WSL compatibility
  - Primary AI inference engine for modern STING deployments
- **[Microsoft Phi-3](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)** - Microsoft - MIT License
  - Compact, high-performance language model (phi3:mini default)
  - Optimized for speed and quality balance in enterprise environments
- **[Transformers](https://huggingface.co/transformers/)** - Hugging Face - Apache License 2.0
  - State-of-the-art machine learning library for natural language processing
- **[Sentence Transformers](https://www.sbert.net/)** - UKP Lab - Apache License 2.0
  - Framework for sentence, text and image embeddings using BERT/RoBERTa/XLM-R models

### LLM Application Framework
- **[LangChain](https://www.langchain.com/)** - Harrison Chase and LangChain Team - MIT License
  - Powerful framework for developing applications powered by language models
  - Provides abstractions for chains, agents, memory, and tools
  - Powers Bee's conversational capabilities and context management
- **[tiktoken](https://github.com/openai/tiktoken)** - OpenAI - MIT License
  - Fast BPE tokenizer for OpenAI models and compatible tokenization
  - Critical for accurate token counting in Bee's conversation management
  - Enables precise context window management and automatic pruning
  - Supports multiple model families including GPT, Llama, and Claude

### Document Processing (Honey Jar System)
- **[PyPDF2](https://pypdf2.readthedocs.io/)** - Mathieu Fenniak, PyPDF2 Contributors - BSD 3-Clause License
  - PDF document reading and text extraction for knowledge ingestion
- **[python-docx](https://python-docx.readthedocs.io/)** - Steve Canny - MIT License
  - Microsoft Word document (.docx) reading and processing
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** - Leonard Richardson - MIT License
  - HTML and XML parsing for web content extraction
- **[markdown](https://python-markdown.github.io/)** - Manfred Stienstra, Yuri Takhteyev, Waylan Limberg - BSD License
  - Markdown to HTML conversion and processing
- **[NLTK](https://www.nltk.org/)** - NLTK Project - Apache License 2.0
  - Natural Language Toolkit for text processing and tokenization
  - Used in Honey Jar document chunking and analysis
- **[python-magic](https://github.com/ahupp/python-magic)** - Adam Hupp - MIT License
  - File type detection using libmagic for robust document identification

### Database & Storage
- **[PostgreSQL](https://www.postgresql.org/)** - PostgreSQL Global Development Group - PostgreSQL License
  - Advanced open source relational database system
- **[psycopg2](https://www.psycopg.org/)** - Federico Di Gregorio, Daniele Varrazzo - LGPL License
  - PostgreSQL database adapter for Python
  - Binary distribution (psycopg2-binary) for easy installation
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - Mike Bayer - MIT License
  - Python SQL toolkit and Object-Relational Mapping library
- **[Chroma](https://www.trychroma.com/)** - Chroma Team - Apache License 2.0
  - Open-source embedding database for vector similarity search
  - Powers Honey Jar semantic search with vector embeddings
- **[Redis](https://redis.io/)** - Redis Ltd. - BSD-3-Clause License
  - In-memory data structure store for caching and session management
- **[asyncpg](https://github.com/MagicStack/asyncpg)** - MagicStack Inc. - Apache License 2.0
  - Fast PostgreSQL database client library for Python/asyncio

## Deployment & Infrastructure

### Containerization
- **[Docker](https://www.docker.com/)** - Docker, Inc. - Apache License 2.0
  - Containerization platform for application deployment
- **[Docker Compose](https://docs.docker.com/compose/)** - Docker, Inc. - Apache License 2.0
  - Tool for defining and running multi-container Docker applications

### Web Servers & Proxies
- **[Nginx](https://nginx.org/)** - Igor Sysoev, Nginx Inc. - BSD-2-Clause License
  - High-performance web server and reverse proxy
- **[Traefik](https://traefik.io/)** - Traefik Labs - MIT License
  - Modern HTTP reverse proxy and load balancer

### Observability & Monitoring
- **[Grafana](https://grafana.com/)** - Grafana Labs - AGPLv3 License
  - Observability platform for visualizing metrics, logs, and traces
  - Provides dashboards for monitoring STING services
- **[Loki](https://grafana.com/oss/loki/)** - Grafana Labs - AGPLv3 License
  - Log aggregation system optimized for Kubernetes and cloud-native apps
  - Collects and indexes logs from all STING services
- **[Promtail](https://grafana.com/docs/loki/latest/clients/promtail/)** - Grafana Labs - AGPLv3 License
  - Log collection agent that ships logs to Loki
  - Runs as a sidecar to gather container logs

### Development & Testing Tools
- **[Mailpit](https://github.com/axllent/mailpit)** - Axllent - MIT License
  - Modern SMTP testing tool for development environments
  - Email capture and testing with web UI
- **[curl](https://curl.se/)** - Daniel Stenberg - MIT License
  - Command line tool for transferring data with URLs, used for health checks

## Design & Assets

### Fonts
- **[Inter](https://rsms.me/inter/)** - Rasmus Andersson - SIL Open Font License 1.1
  - Modern typeface designed for computer screens
  - Used throughout the STING interface for optimal readability

### Color Palette
Our STING V2 theme builds upon established design principles:
- **Material Design Color System** - Google - Apache License 2.0
  - Color theory and accessibility guidelines
- **Tailwind CSS Color Palette** - Tailwind Labs - MIT License
  - Consistent color naming and shade variations

## Documentation & Standards

### API Documentation
- **[OpenAPI Specification](https://swagger.io/specification/)** - OpenAPI Initiative - Apache License 2.0
  - Standard for describing REST APIs

### Accessibility
- **[WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)** - W3C - W3C Software License
  - Web Content Accessibility Guidelines ensuring inclusive design

## Special Thanks

### Community Contributions
We acknowledge the broader open source security community whose tools, methodologies, and shared knowledge contribute to making cybersecurity more accessible and effective.

### AI & Machine Learning Community
- **[Ollama Community](https://github.com/ollama/ollama)** for creating an accessible, cross-platform LLM deployment solution
- **[Hugging Face](https://huggingface.co/)** for democratizing access to state-of-the-art AI models and tools
- **[Microsoft AI Research](https://www.microsoft.com/en-us/research/lab/microsoft-research-ai/)** for developing and open-sourcing the Phi-3 model family
- **Open source AI researchers** who contribute to model development, optimization, and accessibility

### Design Inspiration
- **[Ant Design](https://ant.design/)** design principles and component patterns
- **[Material Design](https://material.io/)** system for interaction and motion guidelines
- **Modern cybersecurity dashboards** from the security community for UX patterns
- **AI chat interfaces** from the open source community for conversational UX patterns

## Contributing Back

STING is committed to giving back to the open source community:
- Reporting bugs and contributing fixes to upstream projects
- Sharing security research and methodologies
- Contributing to documentation and educational resources
- Supporting diversity and inclusion in the cybersecurity field

## License Compatibility

All incorporated open source libraries have been selected for license compatibility. The combination of MIT, Apache 2.0, BSD, and other permissive licenses allows for both open source and commercial use while respecting the original authors' terms.

## Updating Credits

When adding new dependencies or tools to STING:
1. Add the project name, maintainer, and license to the appropriate section
2. Include a brief description of how the tool is used in STING
3. Verify license compatibility
4. Update relevant README files with integration details

## Contact

For questions about licensing, credits, or to report missing attributions, please:
- Open an issue in the STING repository
- Contact the STING development team

---

**Last Updated**: October 2025

Thank you to all the open source maintainers and contributors who make projects like STING-CE possible. Your dedication to building, maintaining, and sharing these tools drives innovation and progress in software development, artificial intelligence, and cybersecurity.

Special recognition goes to the AI/ML open source community for making advanced language models accessible to developers worldwide, enabling projects like STING-CE to provide enterprise-grade AI capabilities while maintaining complete data sovereignty and privacy.

*Bee Smart. Bee Secure.*