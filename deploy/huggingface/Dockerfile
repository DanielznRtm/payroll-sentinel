# Hugging Face Space for Payroll Sentinel. Spaces run Streamlit apps as Docker Spaces.
#
# The app is not copied into the Space: the image installs one pinned commit of the
# GitHub repository, so GitHub stays the only source of code. To deploy a newer
# version, change REF to that commit and upload this file to the Space again.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as the user with id 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DEMO_MODE=1
WORKDIR /home/user/app

ARG REPO=https://github.com/DanielznRtm/payroll-sentinel.git
ARG REF=212b1dd17a97b5cff5ad3b34dbd67aeaec4c7a33
RUN git init -q . \
    && git fetch -q --depth 1 "$REPO" "$REF" \
    && git checkout -q FETCH_HEAD \
    && pip install --no-cache-dir --user ".[ui]"

EXPOSE 8501
# Streamlit's XSRF protection needs a cookie, and browsers block cookies inside the
# huggingface.co iframe, so uploads would fail with HTTP 403 (Hub docs, "Cookie
# limitations in Spaces"). The app has no login and keeps no data to protect.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.enableXsrfProtection=false"]
