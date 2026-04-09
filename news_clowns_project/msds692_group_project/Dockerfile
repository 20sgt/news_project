# 1. Start from a lightweight Python image
FROM python:3.11-slim

# 2. Set a working directory
WORKDIR /streamlit_newscaster_draft

# 3. Copy all files from local folder into container
COPY . .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Set environment variables for Streamlit on Cloud Run
ENV PORT 8080
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHERUSAGESTATS=false

# 6. Expose the port for the app
EXPOSE 8080

# 7. Run Streamlit when the container starts
CMD ["streamlit", "run", "streamlit_newscaster_draft.py", "--server.port=8080", "--server.address=0.0.0.0"]
