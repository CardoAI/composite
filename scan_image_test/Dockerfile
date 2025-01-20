FROM public.ecr.aws/amazonlinux/amazonlinux:latest
 
RUN dnf install python3 aws-cli -y

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

COPY ./entrypoint . 
COPY image.tar .
RUN chmod 0500 main.py

# Install any required Python dependencies (if needed, update requirements.txt with dependencies)
# RUN pip install -r requirements.txt

# Run the script with the required arguments
CMD [ "python3", "main.py", \
      "--artifact-type=container", \
      "--artifact-path=image.tar", \
      "--display-vuln-findings=enabled", \
      "--out-sbom=./sbom.json", \
      "--out-scan=inspector_scan_.json", \
      "--out-scan-csv=inspector_scan_.csv", \
      "--out-scan-markdown=inspector_scan_.md", \
      "--out-dockerfile-scan-csv=inspector_dockerfile_scan_.csv", \
      "--out-dockerfile-scan-md=inspector_dockerfile_scan_.md", \
      "--sbomgen-version=1.5.5" ]
