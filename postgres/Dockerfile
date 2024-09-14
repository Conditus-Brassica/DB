FROM ubuntu:22.04

WORKDIR service

# install python (common)
RUN apt-get update &&\
    apt-get install python3 -y &&\
    apt-get install python3-venv -y &&\
    apt-get install git -y &&\
    apt-get clean

RUN git clone https://github.com/Conditus-Brassica/DB.git &&\
    cd DB &&\
    python3 -m venv .venv &&\
    . .venv/bin/activate &&\
    pip3 install -r ./postgres/requirements.txt &&\
    apt-get install -y \
    wget \
    curl &&\
    DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*


USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "ALTER USER postgres PASSWORD 'ostisGovno';"

EXPOSE 5432

WORKDIR DB

USER root

CMD service postgresql start &&\
    . .venv/bin/activate &&\
    echo "Fill DB with embeddings..." &&\
    python3 postgres/import_db.py json_path=./landmarks.json neo4j_host=neo4j-db neo4j_port=7687 neo4j_user=neo4j neo4j_password=ostisGovno postgres_host=127.0.0.1 postgres_port=5432 postgres_user=postgres postgres_password=ostisGovno &&\
    echo "Done." &&\
    tail -f /dev/null
