# Use a Python runtime as a base image
FROM python:3.8-slim
# Set the working directory in the container
WORKDIR /app
# Copy the current directory contents into the container at /app
COPY . .
# Add Env.
ARG OPENAI_API_KEY
ENV OPENAI_API_KEY_=$OPENAI_API_KEY

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port streamlit runs on
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "onow_assistant.py"]