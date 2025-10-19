FROM python:3.13

ENV SMTP_HOST=localhost
ENV SMTP_PORT=1025
ENV MAIL_TEMPLATE=confirm.email.mustache
ENV MAIL_ADMIN=admin@localhost
ENV MAIL_FROM=admin@localhost
ENV HASH_KEY_FILE=/app/etc/key
ENV DB_HOST=postgres
ENV DB_NAME=postgres
ENV DB_USER=postgres
ENV DB_PASS=postgres
ENV DB_PORT=5432
ENV LOGLEVEL=DEBUG
ENV PURGE_TTL=86400

ADD  . /app

WORKDIR /app

RUN pip install -r requirements.txt \
    && adduser postconfirm

USER postconfirm

EXPOSE 1999

CMD ["python", "/app/postconfirm.py", "-c", "/app/etc/postconfirm.cfg"]
