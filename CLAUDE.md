# Arthsutra – CLAUDE.md

This document contains helpful terminal commands for working with the Arthsutra project.

## Build & Run

### Backend
The backend is a FastAPI application written in Python.

```bash
# Activate virtual environment (if you have one)
source .venv\Scripts\activate

# Install dependencies – if you have a `requirements.txt` run:
# pip install -r requirements.txt

# Or install the project in editable mode (if a `setup.py` or `pyproject.toml` exists):
# pip install -e .

# Run the API server
uvicorn backend.main:app --host 0.0.0.0 --port 5174 --reload
```

The `--reload` flag restarts the server on code changes.

### Frontend
The frontend is a Vite + React app located under `frontend/`.

```bash
# Ensure you have Node.js installed. Then:
cd frontend
# Install frontend dependencies (if a package.json exists)
npm install

# Start the development server
npm run dev
```

If the frontend repository is not yet initialized, create a `package.json` with the following minimal configuration:

```json
{
  "name": "arthsutra-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0"
  }
}
```

### Linting & Formatting

```bash
# Install linting tools (example using flake8)
pip install flake8

# Run linting on the backend code
flake8 backend
```

For the frontend you can use ESLint if set up:

```bash
# Assuming an ESLint configuration
npm run lint
```

### Running Tests

The project uses `pytest` for unit tests.

```bash
# Install pytest (if not already present)
pip install pytest

# Run all tests
pytest

# Run a specific test file or test function
pytest tests/test_something.py::TestClass::test_method
```

If you only have backend tests located under `tests/`, adjust the path accordingly.

---

## Quick Start Summary

| Purpose | Command |
|---------|---------|
| Start backend | `uvicorn backend.main:app --reload --port 5174` |
| Start frontend | `npm run dev` (inside `frontend/`) |
| Lint backend | `flake8 backend` |
| Run tests | `pytest` |

Feel free to adjust the commands to match your project's exact dependency files if they differ.
