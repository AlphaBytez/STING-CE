# STING Development Guide for AI Agents

## Build/Test Commands
- **Frontend**: `cd frontend && npm start` (dev), `npm run build` (production), `npm test` (single test)
- **Backend**: `python app/run.py` or `docker-compose up`
- **Install**: `./install_sting.sh install --debug`
- **Single Test**: `python test_<module>.py` or `cd frontend && npm test -- <test-file>`

## Code Style Guidelines
- **Python**: Follow PEP 8, use type hints, prefer `from module import specific_item`
- **JavaScript/React**: ES6+ modules, functional components with hooks, Material-UI + Tailwind CSS
- **Imports**: Group by stdlib → third-party → local, alphabetical within groups
- **Naming**: snake_case (Python), camelCase (JS), PascalCase (React components/classes)
- **Error Handling**: Try-except with specific exceptions (Python), try-catch with proper logging (JS)
- **Files**: Lowercase with underscores (Python), camelCase/PascalCase (JS/React)

## Project Structure
- **Frontend**: React 18 app in `/frontend` with Material-UI, Ory Kratos auth
- **Backend**: Flask API in `/app` with PostgreSQL, Redis, vector DB (Chroma)
- **Services**: Docker microservices including LLM gateway, authentication, knowledge management
- **Config**: YAML files in `/conf`, Docker Compose orchestration