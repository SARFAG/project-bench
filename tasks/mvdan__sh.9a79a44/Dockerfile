# syntax=docker/dockerfile:1
#
# Task image for mvdan__sh.9a79a44.
#
# One image serves both inference and evaluation, matching the ProgramBench
# contract (programbench/<id>:task_cleanroom_v6):
#
#   inference  the agent starts in /workspace and finds the reference binary at
#              ./executable and its documentation in ./docs
#   evaluation the harness wipes /workspace, unpacks the submission, builds it
#              with the network cut, and deletes any file whose sha256 appears in
#              task.yaml `eval_clean_hashes`, so the reference cannot be reused
#
# The reference SOURCE never enters the final stage; only the compiled binary
# and agent_docs/ are copied in.
#
#   docker build -t programbench/mvdan_1776_sh.9a79a44:task_cleanroom_v6 .

ARG GO_VERSION=1.26
ARG PYTHON_VERSION=3.12

FROM golang:${GO_VERSION}-bookworm AS gotoolchain

FROM golang:${GO_VERSION}-bookworm AS reference

# Optional trust anchors for an intercepting TLS proxy; empty in a normal build.
COPY ca/ /usr/local/share/ca-certificates/extra/
RUN find /usr/local/share/ca-certificates/extra -name '*.crt' -print -quit | grep -q . \
      && update-ca-certificates || true

COPY reference/src /src

# -trimpath and -s -w keep host paths and debug info out of the binary.
RUN cd /src \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /ref/bin/shfmt ./cmd/shfmt

# `eval_clean_hashes` in task.yaml is the sha256 of this binary; the harness uses it
# to delete copies of the reference from submissions. If a toolchain update ever
# changes the bytes, fail the build here rather than silently disarm that check.
ARG REFERENCE_SHA256=6334e7d5c5a7c535ea72f8511325ef3549e448169c60b476b03af26181079830
RUN echo "${REFERENCE_SHA256}  /ref/bin/shfmt" | sha256sum -c -

# The documentation must match the binary it describes.
COPY agent_docs /ref/doc
SHELL ["/bin/bash", "-c"]
RUN diff <(/ref/bin/shfmt --help 2>&1) /ref/doc/shfmt-help.txt


FROM python:${PYTHON_VERSION}-bookworm

COPY ca/ /usr/local/share/ca-certificates/extra/
RUN find /usr/local/share/ca-certificates/extra -name '*.crt' -print -quit | grep -q . \
      && update-ca-certificates || true

# Go toolchain for the rebuild, copied rather than installed so the image needs no
# package manager access.
COPY --from=gotoolchain /usr/local/go /usr/local/go
ENV GOPATH=/go
ENV PATH=/usr/local/go/bin:/go/bin:$PATH
# The harness runs every command through `bash -lc`. A login shell re-sources
# /etc/profile, which resets PATH and discards the ENV line above, so tools must
# also be reachable from the default login PATH.
RUN ln -s /usr/local/go/bin/go /usr/local/bin/go \
 && ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt

# Test runner. The harness executes pytest in this image and reads
# eval/results.xml afterwards.
RUN pip install --no-cache-dir "pytest>=8" "pytest-timeout>=2.4" "pytest-xdist>=3" "pytest-rerunfailures==16.4"

# The agent runner starts the container with `--user agent`, but the harness
# unpacks and builds the submission as root, keeping the agent's file ownership.
# Without this, root's git refuses the agent-owned repository ("dubious
# ownership") and any build that stamps VCS info (go build) fails at evaluation
# even though it worked for the agent -- an unfair, invisible failure.
RUN git config --system --add safe.directory '*'

# The agent runner starts the container with `--user agent`.
RUN useradd --create-home --uid 1000 --shell /bin/bash agent \
 && mkdir -p /go /workspace \
 && chown -R agent:agent /go /workspace

# What the agent sees: the reference binary and its documentation, in a git
# repository (the agent is told to commit) that ignores the binary.
COPY --from=reference --chown=agent:agent /ref/bin/shfmt /workspace/executable
COPY --from=reference --chown=agent:agent /ref/doc /workspace/docs
USER agent
RUN cd /workspace \
 && printf 'executable\n' > .gitignore \
 && git init -q \
 && git -c user.name=task -c user.email=task@localhost add .gitignore docs \
 && git -c user.name=task -c user.email=task@localhost commit -q -m "Task workspace"
USER root

WORKDIR /workspace
