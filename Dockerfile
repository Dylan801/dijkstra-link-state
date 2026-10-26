# Image Python officielle figée, commune aux trois versions.
FROM python:3.13.16-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --create-home app \
    && mkdir /app/outputs && chown app:app /app/outputs

# Aucune installation Python supplémentaire n'est nécessaire.
COPY --chown=app:app dijkstra/ ./dijkstra/
COPY --chown=app:app data/ ./data/
COPY --chown=app:app scenarios/ ./scenarios/

USER app
ENTRYPOINT ["python", "-m"]
CMD ["dijkstra.v1"]
