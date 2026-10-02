# syntax=docker/dockerfile:1
#
# Task image for mvdan__sh.9a79a44.
#
# Stage "reference" builds the original program from its pinned upstream commit.
# The final stage keeps ONLY the compiled binary and the documentation -- no
# upstream source, no build artifacts, no module cache -- which is what makes
# the task a rebuild-from-behavior exercise.
#
#   inference image:  docker build -t mvdan_1776_sh.9a79a44:task_cleanroom_v1 .
#   eval image:       docker build -t mvdan_1776_sh.9a79a44:eval_v1 \
#                       --build-arg KEEP_REFERENCE=0 .
#
# The eval image drops /opt/reference entirely so a submission cannot discover
# or copy the reference binary at build time.

ARG GO_VERSION=1.26
ARG PYTHON_VERSION=3.12

FROM golang:${GO_VERSION}-bookworm AS gotoolchain

FROM golang:${GO_VERSION}-bookworm AS reference

# Optional trust anchors for an intercepting TLS proxy; empty in a normal build.
COPY ca/ /usr/local/share/ca-certificates/extra/
RUN find /usr/local/share/ca-certificates/extra -name '*.crt' -print -quit | grep -q . \
      && update-ca-certificates || true

# The reference source ships in the task package (reference/src) and is built
# here; the final stage never copies it, so the agent image has no source.
COPY reference/src /src

# -trimpath and -s -w keep host paths and debug info out of the binary.
RUN cd /src \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /ref/bin/shfmt ./cmd/shfmt

# Documentation handed to the agent: only the man page (scdoc source, readable
# prose) and the program's own --help text. Nothing else from the project.
COPY agent_docs /ref/doc
SHELL ["/bin/bash", "-c"]
RUN diff <(/ref/bin/shfmt --help 2>&1) /ref/doc/shfmt-help.txt


FROM python:${PYTHON_VERSION}-bookworm

COPY ca/ /usr/local/share/ca-certificates/extra/
RUN find /usr/local/share/ca-certificates/extra -name '*.crt' -print -quit | grep -q . \
      && update-ca-certificates || true

# Go toolchain for the rebuild. Copied wholesale rather than installed, so the
# image needs no package manager access.
COPY --from=gotoolchain /usr/local/go /usr/local/go
ENV GOPATH=/go
ENV PATH=/usr/local/go/bin:/go/bin:$PATH
# The harness runs every command through `bash -lc`. A login shell re-sources
# /etc/profile, which resets PATH and discards the ENV line above, so tools must
# also be reachable from the default login PATH.
RUN ln -s /usr/local/go/bin/go /usr/local/bin/go \
 && ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

# Test runner. The harness executes pytest inside this image and reads
# eval/results.xml afterwards.
RUN pip install --no-cache-dir "pytest>=8" "pytest-timeout>=2.4" "pytest-xdist>=3" "pytest-rerunfailures==16.4"

COPY --from=reference /ref /opt/reference

# KEEP_REFERENCE=0 produces the evaluation image: the reference program and its
# documentation are removed so only the submission's own build is measured.
ARG KEEP_REFERENCE=1
RUN if [ "${KEEP_REFERENCE}" = "0" ]; then rm -rf /opt/reference; \
    else ln -s /opt/reference/bin/shfmt /usr/local/bin/shfmt; fi

WORKDIR /workspace
