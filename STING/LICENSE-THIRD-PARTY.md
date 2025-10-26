# Third-Party Licenses

This document contains the licensing information for all third-party software used in the STING Platform.

## Table of Contents

1. [Docker Base Images](#docker-base-images)
2. [Python Dependencies](#python-dependencies)
3. [JavaScript/Node.js Dependencies](#javascriptnodejs-dependencies)
4. [Infrastructure Services](#infrastructure-services)

---

## Docker Base Images

### Python Official Images
- **Image**: python:3.9-slim, python:3.11-slim, python:3.12.8-slim
- **License**: PSF License Agreement
- **Website**: https://hub.docker.com/_/python
- **Note**: Python Software Foundation License is a BSD-style, permissive license

### Nginx
- **Image**: nginx:1.27-alpine
- **License**: 2-clause BSD License
- **Website**: https://nginx.org/LICENSE
- **Copyright**: Copyright (C) 2011-2024 Nginx, Inc.

### PostgreSQL
- **Image**: postgres:16
- **License**: PostgreSQL License (similar to BSD/MIT)
- **Website**: https://www.postgresql.org/about/licence/
- **Note**: Very permissive, allows use in commercial applications

### Redis
- **Image**: redis:7-alpine
- **License**: BSD 3-Clause License
- **Website**: https://redis.io/docs/about/license/
- **Copyright**: Copyright (c) 2006-2024 Salvatore Sanfilippo

### ChromaDB
- **Image**: chromadb/chroma:0.5.20
- **License**: Apache License 2.0
- **Website**: https://github.com/chroma-core/chroma
- **Copyright**: Copyright 2023 Chroma

### Ory Kratos
- **Image**: oryd/kratos:v1.3.0
- **License**: Apache License 2.0
- **Website**: https://github.com/ory/kratos
- **Copyright**: Copyright © 2020 Ory Corp

### Mailpit
- **Image**: axllent/mailpit:v1.21.5
- **License**: MIT License
- **Website**: https://github.com/axllent/mailpit
- **Copyright**: Copyright (c) 2022 Axllent

---

## Python Dependencies

### Core Web Framework

#### Flask and Extensions
- **Flask** (2.2.5) - BSD 3-Clause License
- **Flask-SocketIO** (5.1.0) - MIT License
- **Flask-Login** (0.6.3) - MIT License
- **Flask-Security** (3.0.0) - MIT License
- **Flask-SQLAlchemy** (3.0.2) - BSD 3-Clause License
- **Flask-WTF** (1.2.1) - BSD 3-Clause License
- **Flask-Script** (2.0.6) - BSD License
- **Flask-Migrate** (3.1.0) - MIT License
- **Flask-Session** (0.5.0) - BSD 3-Clause License
- **Flask-CORS** - MIT License
- **Flask-OIDC** - BSD 2-Clause License

#### FastAPI and Extensions
- **FastAPI** (>=0.95.0) - MIT License
- **Uvicorn** (>=0.22.0) - BSD 3-Clause License
- **Pydantic** (>=2.0.0) - MIT License

### Database and Storage

#### PostgreSQL
- **psycopg2-binary** (>=2.9.3) - LGPL with exceptions
- **asyncpg** (>=0.29.0) - Apache License 2.0
- **SQLAlchemy** (<2.0) - MIT License

#### Redis
- **redis** (5.0.1) - MIT License

### Security and Authentication
- **cryptography** (>=41.0.0) - Apache License 2.0 and BSD License
- **supertokens-python** (>=0.27.0) - Apache License 2.0
- **hvac** (>=1.2.1) - Apache License 2.0

### AI/ML Libraries

#### Language Models
- **langchain** (>=0.1.0) - MIT License
- **langchain-core** (>=0.1.0) - MIT License
- **llama-index** (>=0.10.0) - MIT License
- **llama-index-core** (>=0.10.0) - MIT License
- **tiktoken** (>=0.5.2) - MIT License

#### Data Science
- **pandas** (>=2.0.0) - BSD 3-Clause License
- **scikit-learn** (>=1.1.3) - BSD 3-Clause License
- **spacy** (3.7.4) - MIT License
- **joblib** (1.2.0) - BSD 3-Clause License

### Utilities
- **boto3** (>=1.34.0) - Apache License 2.0
- **docker** (>=6.1.0) - Apache License 2.0
- **gunicorn** (20.1.0) - MIT License
- **httpx** (>=0.24.0, >=0.25.0) - BSD 3-Clause License
- **pyyaml** (>=6.0, >=6.0.1) - MIT License
- **python-dotenv** (0.19.1, >=1.0.0) - BSD 3-Clause License
- **python-multipart** (>=0.0.6) - Apache License 2.0
- **requests** (>=2.31.0) - Apache License 2.0
- **typer** - MIT License
- **click** (>=8.1.7) - BSD 3-Clause License
- **cerberus** (1.3.5) - ISC License
- **toml** (0.10.2) - MIT License
- **phonenumbers** (>=8.13.0) - Apache License 2.0
- **nanoid** (5.1.5, >=2.0.0) - MIT License
- **reportlab** (>=4.0.0) - BSD License
- **xlsxwriter** (>=3.1.0) - BSD 2-Clause License
- **psutil** (>=5.9.0) - BSD 3-Clause License
- **Werkzeug** (3.0.2) - BSD 3-Clause License
- **Jinja2** (>=3.1.2) - BSD 3-Clause License
- **MarkupSafe** (>=2.1.0) - BSD 3-Clause License
- **itsdangerous** (>=2.1.0) - BSD 3-Clause License
- **typing-extensions** (>=4.7.0, >=4.8.0) - Python Software Foundation License
- **idna** (>=3.4) - BSD 3-Clause License
- **urllib3** (>=1.26.0,<2.0.0) - MIT License

---

## JavaScript/Node.js Dependencies

### Core React Framework
- **react** (^18.2.0) - MIT License
- **react-dom** (^18.2.0) - MIT License
- **react-scripts** (5.0.1) - MIT License
- **react-router-dom** (^6.22.1) - MIT License

### UI Libraries

#### Ant Design
- **antd** (^5.26.2) - MIT License
- **@ant-design/icons** (^6.0.0) - MIT License

#### Material-UI
- **@mui/material** (^7.1.0) - MIT License
- **@mui/icons-material** (^7.1.0) - MIT License
- **@emotion/react** (^11.14.0) - MIT License
- **@emotion/styled** (^11.14.0) - MIT License

#### Other UI Libraries
- **tailwindcss** (^3.3.5) - MIT License
- **tailwind-merge** (^2.2.1) - MIT License
- **class-variance-authority** (^0.7.0) - Apache License 2.0
- **clsx** (^2.1.0) - MIT License
- **lucide-react** (^0.294.0) - ISC License
- **react-icons** (^5.5.0) - MIT License

### Authentication
- **@ory/client** (^1.20.10) - Apache License 2.0
- **@ory/elements** (^0.6.0-pre.2) - Apache License 2.0
- **@simplewebauthn/browser** (^13.0.0) - MIT License
- **keycloak-js** (^22.0.5) - Apache License 2.0
- **@react-keycloak/web** (^3.4.0) - MIT License

### Build Tools
- **@craco/craco** (^7.0.0) - Apache License 2.0
- **@babel/core** (^7.23.0) - MIT License
- **@babel/plugin-proposal-private-property-in-object** (^7.21.11) - MIT License
- **@babel/preset-env** (^7.22.20) - MIT License
- **@babel/preset-react** (^7.22.15) - MIT License

### Utilities
- **axios** (^1.7.9) - MIT License
- **nanoid** (^5.1.5) - MIT License
- **react-markdown** (^10.1.0) - MIT License
- **remark-gfm** (^4.0.1) - MIT License
- **react-intl** (^6.6.1) - BSD 3-Clause License

### Data Visualization
- **chart.js** (^4.4.1) - MIT License
- **react-chartjs-2** (^5.2.0) - MIT License
- **recharts** (^2.15.4) - MIT License

### Testing
- **@testing-library/jest-dom** (^5.17.0) - MIT License
- **@testing-library/react** (^13.4.0) - MIT License
- **@testing-library/user-event** (^13.5.0) - MIT License

### Development Dependencies
- **@tailwindcss/postcss7-compat** (^2.2.17) - MIT License
- **autoprefixer** (^10.4.5) - MIT License
- **postcss** (^8.4.31) - MIT License

### Polyfills
- **https-browserify** (^1.0.0) - MIT License
- **stream-browserify** (^3.0.0) - MIT License
- **stream-http** (^3.2.0) - MIT License

### Other Dependencies
- **@radix-ui/react-slot** (^1.0.2) - MIT License
- **web-vitals** (^2.1.4) - Apache License 2.0

---

## Infrastructure Services

### HashiCorp Vault
- **Service**: HashiCorp Vault (via Docker)
- **License**: Mozilla Public License 2.0
- **Website**: https://www.vaultproject.io/
- **Note**: MPL is a copyleft license but allows proprietary use

### Ollama (LLM Service)
- **Service**: Ollama
- **License**: MIT License
- **Website**: https://github.com/ollama/ollama
- **Note**: Used for local LLM model serving

---

## License Compatibility Notes

1. **MIT, BSD, Apache 2.0**: These are permissive licenses that allow commercial use, modification, and distribution with minimal restrictions.

2. **LGPL (psycopg2)**: The LGPL allows linking with proprietary software. Since we're using psycopg2-binary, we're dynamically linking, which is compliant.

3. **Mozilla Public License 2.0 (Vault)**: File-level copyleft. Since we're using Vault as a separate service via Docker, this doesn't affect our codebase.

4. **ISC License**: Very similar to MIT/BSD, fully permissive.

5. **Python Software Foundation License**: BSD-style, very permissive.

## Acknowledgments

Special thanks to all the open source projects that make STING possible. For specific acknowledgments and credits, see the CREDITS.md file.

---

*This document is automatically generated and maintained. Last updated: January 2025*