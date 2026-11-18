# One image for both shop roles: shop-tools (MCP server) and shop-front (chat and desk).
FROM registry.access.redhat.com/ubi9/python-312:latest

USER 0
# OpenShell CLI for shop-front: the static release binary, checked against the release checksums.
ARG OPENSHELL_VERSION=v0.0.116
RUN cd /tmp \
 && F=openshell-x86_64-unknown-linux-musl.tar.gz \
 && U=https://github.com/NVIDIA/OpenShell/releases/download/${OPENSHELL_VERSION} \
 && curl -fsSL --retry 3 -O "$U/$F" -O "$U/openshell-checksums-sha256.txt" \
 && grep " \*\?$F\$" openshell-checksums-sha256.txt | sed 's/\*//' | sha256sum -c --quiet \
 && tar -xzf "$F" && install -m 0755 "$(find . -type f -name openshell | head -1)" /usr/local/bin/openshell \
 && rm -rf /tmp/*

COPY requirements.txt /opt/app-root/src/
RUN pip install --no-cache-dir -r /opt/app-root/src/requirements.txt
COPY shop /opt/app-root/src/shop
RUN chown -R 1001:0 /opt/app-root/src && chmod -R g=u /opt/app-root/src
USER 1001
WORKDIR /opt/app-root/src
ENV PYTHONUNBUFFERED=1 HOME=/opt/app-root/src
CMD ["python", "-m", "shop.tools"]
