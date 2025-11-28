# Build and run this container

This repository contains a `Dockerfile` that builds an image based on `khaledhassan/simplescalar:latest` and prepares a `/workspace` directory.

## How to build
- Build the local image (run from the `ca1` directory where the `Dockerfile` lives):

```bash
docker build -t simplescalar .
```

## How to run
- Start an interactive shell in the container with the current directory mounted into `/workspace`:

```bash
docker run --rm -it -v "$(pwd)":/workspace simplescalar /bin/bash
```

- If you prefer to run the upstream base image without building locally:

```bash
docker run --rm -it -v "$(pwd)":/workspace khaledhassan/simplescalar:latest /bin/bash
```

Now you can edit your file directly in you pwd while run the Simplescalar inside the container to simulate your benchmark.