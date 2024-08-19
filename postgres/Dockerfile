FROM pytorch/pytorch:2.4.0-cuda11.8-cudnn9-runtime

WORKDIR service

# install python (common)
RUN apt-get update &&\
    apt-get install python3 -y &&\
    apt-get install python3-venv -y &&\
    apt-get install git -y &&\
    apt-get clean

RUN apt-get update &&\    
    apt-get install postgresql -y &&\
    apt-get install build-dep python-psycopg2 -y &&\
    git clone https://github.com/Conditus-Brassica/DB.git &&\
    cd DB &&\
    python3 -m venv .venv &&\
    . .venv/bin/activate &&\
    pip install -r ./postgres/requirements.txt &&\
    apt-get clean

EXPOSE 5432

WORKDIR DB

CMD sudo -u postgres psql &&\
    postgres=# ALTER USER postgres PASSWORD 'ostisGovno'; ALTER ROLE &&\
    postgres=# \q &&\
    . .venv/bin/activate &&\
    echo "Fill DB with embeddings..." &&\
    python3 python3 ./postgres/import_embeddings_db.py json_path=./landmarks.json neo4j_host=0.0.0.0 neo4j_port=7687 neo4j_user=neo4j neo4j_password=ostisGovno postgres_host=0.0.0.0 postgres_port=5432 postgres_user=postgres postgres_password=ostisGovno &&\
    echo "Done." &&\
    tail -f /dev/null
