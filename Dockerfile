FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /usr/src/app
COPY . .

# Make sure run_all_services.sh is executable
RUN chmod +x run_all_services.sh

CMD ["./run_all_services.sh"]

