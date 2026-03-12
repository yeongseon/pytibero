ARG BASE_IMAGE=tiberoofficial/tibero:latest
FROM ${BASE_IMAGE}

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER root

RUN if command -v apt-get >/dev/null 2>&1; then \
        apt-get update && apt-get install -y --no-install-recommends python3 python3-pip gcc g++ unixodbc-dev && rm -rf /var/lib/apt/lists/*; \
    elif command -v dnf >/dev/null 2>&1; then \
        dnf install -y python3 python3-pip gcc gcc-c++ unixODBC-devel && dnf clean all; \
    elif command -v yum >/dev/null 2>&1; then \
        yum install -y python3 python3-pip gcc gcc-c++ unixODBC-devel && yum clean all; \
    else \
        echo "Unsupported base image for e2e runner" && exit 1; \
    fi

WORKDIR /workspace

COPY . .

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install -e ".[dev]"

CMD ["python3", "-m", "pytest", "tests/e2e", "-m", "e2e", "-v"]

