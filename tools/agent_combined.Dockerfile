FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libgomp1 curl git gh python3 python3-pip ripgrep tar && rm -rf /var/lib/apt/lists/*
# Reuse the existing LiteLLM configuration and model pool unchanged.
RUN pip3 install 'litellm[proxy]' --break-system-packages
RUN curl -fL --retry 3 https://github.com/adolfousier/opencrabs/releases/download/v0.5.4/opencrabs-v0.5.4-linux-amd64.tar.gz -o /tmp/opencrabs.tar.gz && \
    echo 'b70cda5ae37c90960be20e7cc4554286b98248572374f37e69ca71a2fab20b4a  /tmp/opencrabs.tar.gz' | sha256sum -c - && \
    tar -xzf /tmp/opencrabs.tar.gz -C /usr/local/bin && chmod +x /usr/local/bin/opencrabs && rm /tmp/opencrabs.tar.gz
# Fail at build time if the binary has unresolved runtime libraries.
RUN opencrabs --version
WORKDIR /opt/nova-agent
COPY litellm_config.yaml ./litellm_config.yaml
COPY tools/agent_bootstrap.py tools/agent_repo_read.py tools/agent_git_guard.py tools/agent_preflight.py tools/agent_combined.py tools/agent_council.py tools/agent_background.py tools/agent_leaders.py tools/agent_advice.py tools/agent_atlas.py tools/agent_mini_benchmark.py tools/agent_deliberation.py tools/agent_council_transport.py tools/agent_router.py ./
COPY tools/benchmarks/atlas4_exam.md ./benchmarks/atlas4_exam.md
RUN mkdir -p /root && ln -s /state/opencrabs /root/.opencrabs
EXPOSE 10000
CMD ["python3", "/opt/nova-agent/agent_combined.py"]
