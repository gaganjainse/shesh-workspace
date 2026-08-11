# Shesh Ecosystem — reproducible dev container (Arch-based, matches CachyOS)
# Build: podman build -f Containerfile -t shesh-ecosystem:canary .
# Run: podman run --rm -it shesh-ecosystem:canary bash
# Distrobox: distrobox create -i shesh-ecosystem:canary -n shesh

FROM archlinux:latest

LABEL org.opencontainers.image.title="shesh-ecosystem"
LABEL org.opencontainers.image.description="Federated AI body: brain/mind/soma MCP components — offline gates"
LABEL org.opencontainers.image.source="https://github.com/gaganjainse/shesh-ecosystem"

# Cache buster: update base weekly
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm \
      python python-pip python-pipx base-devel git curl jq \
      podman buildah distrobox \
      nodejs npm  \
      restic \
      android-tools \
      && pacman -Sc --noconfirm

# uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# Python deps for all gates (offline)
WORKDIR /src
COPY pyproject.toml ./
COPY manifests/ manifests/
COPY scripts/ scripts/
COPY tests/ tests/
COPY policies/ policies/
COPY Makefile ./

# ruff + pytest + mcp are needed for gates
RUN pip install --break-system-packages -q ruff pytest mcp fastmcp tomli \
    && python -m pytest tests/ -q || true

# Entrypoint runs gates
COPY . /src
RUN python scripts/resolve_manifest.py --channel canary --out /tmp/canary.lock && \
    python scripts/check_licenses.py manifests/components.toml

ENTRYPOINT ["make", "check"]
CMD ["check"]
