# Development Guidelines

## Core Principles
- Write clean, efficient, and maintainable code
- Optimize for performance and readability
- Follow JAMstack architecture
- Ensure separation of concerns
- Use TypeScript when possible
- Minimize external dependencies

## Stack

### Backend
- Flask: Web development
- FastAPI: Async APIs
- Twilio SDK: Voice calls
- SQLAlchemy: Database ORM
- Celery: Task queues
- Latest Python features (type hints, async/await)

### Frontend
- Lit: Web components
- Tailwind CSS: Styling
- TypeScript: Type safety
- Nunjucks: Templating (11ty)
- Internal packages:
  - NoSQL database
  - FSM state machines
  - Logging system

### Data Science
- Jupyter: Development environment
- Key libraries:
  - TensorFlow/PyTorch
  - Pandas
  - NumPy
  - Matplotlib/Seaborn
- TensorBoard: Performance tracking
- Colab/JupyterHub: Collaboration

## Code Standards

### Comments
- Write clear, non-redundant comments
- Document non-standard code
- Include reference links
- Mark TODOs and bugs
- Prefer self-documenting code over comments

### Best Practices
- Use modern language features
- Add polyfill TODOs when needed
- Write minimal descriptions
- Fix unclear code instead of commenting
- Log all function calls

## Communication
- Use simple English
- Challenge assumptions with reasoning
- Keep discussions friendly and direct
- Refer to user as 'Daddy'
