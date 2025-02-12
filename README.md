# Wayfinder

Wayfinder is a service discovery and navigation tool designed to work with HashiCorp Nomad and Consul. It provides a clean, modern interface for discovering and accessing services across your infrastructure.

## Features

- 🔍 Unified view of services from both Nomad and Consul
- 🏷️ Namespace-aware service organization
- 💡 Dark/Light mode support
- 🔒 Token-based authentication support
- ❤️ Real-time health status monitoring
- 🔄 Automatic service refresh
- 📋 One-click URL copying

## Prerequisites

- Python 3.7+
- HashiCorp Nomad (required)
- HashiCorp Consul (optional)
- Docker (for container deployment)

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/wayfinder.git
cd wayfinder
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install flask requests
```

3. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment to Nomad

### 1. Build the Docker Image

First, create a Dockerfile in your project root:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install flask requests

EXPOSE 5000
CMD ["python", "app.py"]
```

Build and tag the image:
```bash
docker build -t wayfinder:latest .
```

### 2. Deploy using Nomad

The provided `wayfinder.nomad` job specification can be used to deploy Wayfinder:

```bash
nomad job run wayfinder.nomad
```

The job specification includes:
- Service registration with health checks
- Docker task driver configuration
- Resource allocation (CPU and Memory)
- Network port mapping

### 3. Accessing Wayfinder

Once deployed, Wayfinder will be accessible through the Nomad service discovery:

1. Find the allocated port:
```bash
nomad job status wayfinder
```

2. Access the UI through your browser:
```
http://<nomad-client-ip>:<allocated-port>
```

## Configuration

### Nomad Integration

1. Access the Wayfinder UI
2. Enter your Nomad server URL (e.g., `http://nomad-server:4646`)
3. (Optional) Add your Nomad ACL token if authentication is enabled

### Consul Integration (Optional)

1. In the setup page, expand "Consul Integration"
2. Enter your Consul server URL (e.g., `http://consul-server:8500`)
3. (Optional) Add your Consul ACL token if authentication is enabled

## Security Considerations

- Wayfinder supports both Nomad and Consul ACL tokens
- Tokens are stored securely in the Flask session
- All service communication uses HTTPS when configured with TLS
- Service health data is updated every 30 seconds

## Directory Structure

```
wayfinder/
├── app.py              # Main application code
├── templates/
│   ├── index.html     # Main service dashboard
│   └── setup.html     # Configuration page
├── logos/             # Service logos
│   ├── consul-dark.svg
│   ├── consul-light.svg
│   ├── nomad-dark.svg
│   └── nomad-light.svg
├── wayfinder.nomad    # Nomad job specification
└── README.md          # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.