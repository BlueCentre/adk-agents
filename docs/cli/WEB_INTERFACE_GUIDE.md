---
layout: default
title: Web Interface Guide
parent: CLI Documentation
nav_order: 6
description: "Complete guide to using the DevOps Agent web interface with session management and deployment options."
---

# Web Interface Guide

The DevOps Agent web interface provides a modern, browser-based way to interact with your agents. This guide covers everything from basic setup to advanced configuration and troubleshooting.

## 🌐 Overview

The web interface offers:
- **Modern UI**: Responsive design accessible from any browser
- **Session Persistence**: Conversations survive server restarts
- **Automatic Recovery**: Graceful handling of interrupted sessions
- **Real-time Streaming**: Live responses via Server-Sent Events
- **Artifact Management**: Upload, download, and manage files
- **CORS Support**: Cross-origin integration capabilities

## 🚀 Quick Start

### Basic Usage

```bash
# Start the web interface
adk web agents/

# Access in browser
open http://localhost:8000
```

### Recommended Setup (Persistent Sessions)

```bash
# Use SQLite for session persistence
adk web agents/ --session_db_url "sqlite:///sessions.db"

# Access in browser
open http://localhost:8000
```

## 📋 Command Reference

### Basic Command

```bash
adk web AGENTS_DIR [OPTIONS]
```

### Common Examples

```bash
# Development setup with persistent sessions
adk web agents/ --session_db_url "sqlite:///sessions.db"

# Custom port and host
adk web agents/ --host 0.0.0.0 --port 8080

# Production configuration
adk web agents/ \
  --host 0.0.0.0 \
  --port 8080 \
  --session_db_url "postgresql://user:pass@host:port/db" \
  --artifact_storage_uri "gs://my-bucket" \
  --allow_origins "https://mydomain.com" \
  --trace_to_cloud

# Suppress auto-reload message
adk web agents/ --no-reload --session_db_url "sqlite:///sessions.db"
```

## ⚙️ Configuration Options

### Core Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--host` | Binding host | `127.0.0.1` | `--host 0.0.0.0` |
| `--port` | Server port | `8000` | `--port 8080` |
| `--reload/--no-reload` | Auto-reload | `True` | `--no-reload` |

### Session Management

| Option | Description | Use Case |
|--------|-------------|----------|
| *No option* | In-memory sessions | Quick testing, sessions lost on restart |
| `--session_db_url "sqlite:///sessions.db"` | SQLite database | Development, local persistence |
| `--session_db_url "postgresql://..."` | PostgreSQL | Production, shared database |
| `--session_db_url "agentengine://resource_id"` | Google Cloud | Managed cloud sessions |

### Advanced Options

| Option | Description | Example |
|--------|-------------|---------|
| `--artifact_storage_uri` | Artifact storage location | `gs://my-bucket` |
| `--allow_origins` | CORS allowed origins | `https://mydomain.com` |
| `--trace_to_cloud` | Enable cloud tracing | Flag only |
| `--log_level` | Logging verbosity | `DEBUG`, `INFO`, `WARNING` |

## 🗄️ Session Management

### Session Storage Types

#### 1. In-Memory Sessions (Default)
```bash
adk web agents/
```

**Characteristics:**
- ✅ Fast startup
- ✅ No setup required
- ❌ Sessions lost on restart
- ❌ Not suitable for production

**Use Cases:**
- Quick testing
- Development experiments
- Temporary interactions

#### 2. SQLite Sessions (Recommended for Development)
```bash
adk web agents/ --session_db_url "sqlite:///sessions.db"
```

**Characteristics:**
- ✅ Persistent across restarts
- ✅ Single file storage
- ✅ No external dependencies
- ✅ Automatic database creation
- ❌ Single-user only

**Use Cases:**
- Local development
- Personal projects
- Persistent testing

#### 3. PostgreSQL Sessions (Production)
```bash
adk web agents/ --session_db_url "postgresql://user:password@host:5432/dbname"
```

**Characteristics:**
- ✅ Multi-user support
- ✅ High availability
- ✅ Backup and recovery
- ✅ Scalable
- ❌ Requires database setup

**Use Cases:**
- Production deployments
- Team environments
- Enterprise usage

#### 4. Agent Engine Sessions (Google Cloud)
```bash
adk web agents/ --session_db_url "agentengine://your-resource-id"
```

**Characteristics:**
- ✅ Fully managed
- ✅ Google Cloud integration
- ✅ Automatic scaling
- ✅ Built-in monitoring
- ❌ Requires Google Cloud setup

**Use Cases:**
- Google Cloud environments
- Managed deployments
- Enterprise Google Cloud usage

## 🌍 Network Configuration

### Local Development
```bash
# Default - localhost only
adk web agents/ --session_db_url "sqlite:///sessions.db"
# Access: http://localhost:8000
```

### Network Access
```bash
# Allow network access
adk web agents/ --host 0.0.0.0 --port 8080 --session_db_url "sqlite:///sessions.db"
# Access: http://your-ip:8080
```

### CORS Configuration
```bash
# Single origin
adk web agents/ --allow_origins "https://mydomain.com"

# Multiple origins
adk web agents/ \
  --allow_origins "https://mydomain.com" \
  --allow_origins "https://app.mydomain.com" \
  --allow_origins "http://localhost:3000"
```

## 🔧 Troubleshooting

### Common Issues

#### Session Not Found Errors
**Problem:** Browser shows "Session not found" errors after server restart.

**Solution:**
```bash
# Use persistent sessions
adk web agents/ --session_db_url "sqlite:///sessions.db"
```

**Explanation:** In-memory sessions are lost when the server restarts. The web interface now includes automatic session recovery, but persistent storage is recommended.

#### Port Already in Use
**Problem:** `Address already in use` error.

**Solutions:**
```bash
# Use different port
adk web agents/ --port 8080

# Find and kill existing process
lsof -ti:8000 | xargs kill -9

# Check what's using the port
lsof -i :8000
```

#### Static Files Not Loading
**Problem:** Web interface shows blank page or missing styles.

**Solutions:**
1. **Restart the server** - Files are served automatically
2. **Check browser console** for error messages
3. **Clear browser cache** and refresh
4. **Verify server logs** for any errors

#### CORS Errors
**Problem:** Cross-origin requests blocked.

**Solution:**
```bash
# Add your domain to allowed origins
adk web agents/ --allow_origins "https://yourdomain.com"

# For development with multiple origins
adk web agents/ \
  --allow_origins "http://localhost:3000" \
  --allow_origins "https://yourdomain.com"
```

#### Auto-reload Warnings
**Problem:** Seeing "Reload mode is not supported" message.

**Solution:**
```bash
# Suppress the message (normal behavior)
adk web agents/ --no-reload --session_db_url "sqlite:///sessions.db"
```

**Explanation:** This is expected behavior. The web interface works correctly without reload mode.

### Database Issues

#### SQLite Permission Errors
```bash
# Check directory permissions
ls -la $(dirname sessions.db)

# Ensure write permissions
chmod 755 $(dirname sessions.db)

# Use absolute path
adk web agents/ --session_db_url "sqlite:///$(pwd)/sessions.db"
```

#### PostgreSQL Connection Issues
```bash
# Test connection
psql "postgresql://user:password@host:5432/dbname" -c "SELECT 1;"

# Check network connectivity
telnet host 5432

# Verify credentials and database exists
```

### Performance Issues

#### Slow Response Times
1. **Check system resources** (CPU, memory)
2. **Monitor database performance** for persistent sessions
3. **Enable tracing** for detailed analysis:
   ```bash
   adk web agents/ --trace_to_cloud --log_level DEBUG
   ```

#### Memory Usage
1. **Use persistent sessions** to reduce memory overhead
2. **Monitor session count** in production
3. **Implement session cleanup** for long-running deployments

## 🚀 Production Deployment

### Basic Production Setup
```bash
adk web agents/ \
  --host 0.0.0.0 \
  --port 8000 \
  --session_db_url "postgresql://user:pass@db:5432/sessions" \
  --artifact_storage_uri "gs://production-artifacts" \
  --allow_origins "https://yourapp.com" \
  --trace_to_cloud \
  --no-reload
```

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install google-adk
EXPOSE 8000
CMD ["adk", "web", "agents/", "--host", "0.0.0.0", "--session_db_url", "postgresql://..."]
```

### Environment Variables
```bash
# Set in production environment
export GOOGLE_API_KEY=your_api_key
export GOOGLE_CLOUD_PROJECT=your_project
export DATABASE_URL=postgresql://...
export ARTIFACT_STORAGE_URI=gs://...

# Use in command
adk web agents/ \
  --session_db_url "$DATABASE_URL" \
  --artifact_storage_uri "$ARTIFACT_STORAGE_URI"
```

### Health Checks
```bash
# Basic health check
curl http://localhost:8000/list-apps

# Detailed health check with session creation
curl -X POST http://localhost:8000/apps/devops/users/health/sessions \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 🔍 Monitoring and Debugging

### Enable Debug Logging
```bash
adk web agents/ \
  --log_level DEBUG \
  --trace_to_cloud \
  --session_db_url "sqlite:///sessions.db"
```

### Log Analysis
Key log messages to monitor:
- `Session {id} not found, creating new session` - Automatic recovery
- `INFO: Reload mode is not supported` - Expected behavior
- `Started server process` - Successful startup
- Database connection messages - Session storage health

### Performance Monitoring
- **Response times** for `/run` and `/run_sse` endpoints
- **Session creation/retrieval** times
- **Database query** performance
- **Memory usage** trends

## 📚 API Reference

The web interface exposes these key endpoints:

### Session Management
- `GET /apps/{app}/users/{user}/sessions` - List sessions
- `POST /apps/{app}/users/{user}/sessions` - Create session
- `GET /apps/{app}/users/{user}/sessions/{id}` - Get session

### Agent Interaction
- `POST /run` - Execute agent (non-streaming)
- `POST /run_sse` - Execute agent (streaming)

### Utility
- `GET /list-apps` - List available agents
- `GET /` - Redirect to web UI
- `GET /dev-ui/` - Web interface

## 🎯 Best Practices

### Development
1. **Use persistent sessions**: `--session_db_url "sqlite:///sessions.db"`
2. **Enable debug logging**: `--log_level DEBUG`
3. **Use custom ports**: Avoid conflicts with other services
4. **Regular database cleanup**: Monitor SQLite file size

### Production
1. **Use PostgreSQL**: For multi-user environments
2. **Configure CORS**: Restrict to known domains
3. **Enable tracing**: For monitoring and debugging
4. **Use environment variables**: For sensitive configuration
5. **Implement health checks**: Monitor service availability
6. **Regular backups**: For session databases

### Security
1. **Restrict host binding**: Use `127.0.0.1` for local-only access
2. **Configure CORS carefully**: Only allow necessary origins
3. **Use HTTPS**: In production environments
4. **Secure database connections**: Use encrypted connections
5. **Monitor access logs**: Track usage patterns

---

The web interface provides a powerful, modern way to interact with your DevOps agents. With proper session management and configuration, it offers a reliable, scalable solution for both development and production use cases. 