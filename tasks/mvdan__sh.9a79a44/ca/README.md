# Optional extra CA certificates

Drop any `*.crt` files needed to trust an intercepting TLS proxy here before
building the image. The directory is empty by default and the build is a no-op
without it. `scripts/build_task_image.sh` populates it automatically when the
session runs behind such a proxy, and clears it afterwards.
