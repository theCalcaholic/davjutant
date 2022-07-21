FROM python:alpine as builder

COPY . /app
RUN python -m venv /venv \
    && cd /app  \
    && /venv/bin/pip install .  \
    && /venv/bin/pip install waitress

FROM python:alpine
ENV CALDAV_URL=''
ENV CALDAV_USER=''
ENV CALDAV_PASSWORD=''
ENV PORT=80
ENV ADDRESS='0.0.0.0'
ENV WEBHOOKS_SECRET=''
ENV PYTHONUNBUFFERED=1

COPY --from=builder /venv /venv

CMD /venv/bin/waitress-serve --listen=$ADDRESS:$PORT --call davjutant:create_app

ENV FLASK_APP=davjutant

