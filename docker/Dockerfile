FROM ubuntu:24.04

RUN apt update && \
    apt install python3 -y && \
    apt install python3-pip -y

WORKDIR /app
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt --break-system-packages


COPY ./app.py ./app.py
COPY ./tools.py ./tools.py

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py"]