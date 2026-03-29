# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file into the container
COPY requirements.txt .

# 4. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy all the local code into the container
COPY . .

# 6. Expose the port the app runs on
EXPOSE 8000

# 7. Run the new app module entry point
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]