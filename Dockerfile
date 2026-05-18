FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python, Node.js, npm, and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    nodejs \
    npm \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set Python aliases
RUN ln -s /usr/bin/python3 /usr/bin/python

# Create app directory
WORKDIR /app

# Copy service code
COPY medical-system-backend-fastapi/medical-system-backend-fastapi/ /app/backend/
COPY medical-system-backend-fastapi/medical-system-backend-fastapi/frontend/ /app/frontend/

# Install Python dependencies for Backend
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    sqlalchemy==2.0.25 \
    python-jose==3.3.0 \
    passlib==1.7.4 \
    python-multipart==0.0.9 \
    httpx \
    pillow

# Install Node dependencies for Frontend
RUN cd /app/frontend && npm install

# Expose ports
EXPOSE 8000 3000

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting Backend (Qwen-VL powered)..."\n\
cd /app/backend && uvicorn main:app --host 0.0.0.0 --port 8000 &\n\
echo "Starting Frontend..."\n\
cd /app/frontend && npm run dev\n\
wait' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
