FROM pytorch/pytorch:2.4.0-cuda11.8-cudnn9-runtime

WORKDIR service

# install python (common)
RUN apt-get update &&\
    apt-get install python3 -y &&\
    apt-get install python3-venv -y &&\
    apt-get install git -y &&\
    apt-get clean

RUN DEBIAN_FRONTEND=noninteractive apt install postgresql -yq &&\
    git clone https://github.com/Conditus-Brassica/DB.git &&\
    cd DB &&\
    mv ./postgres/pg_hba.conf /etc/postgresql/14/main/pg_hba.conf &&\
    python3 -m venv .venv &&\
    . .venv/bin/activate &&\
    pip install -r ./postgres/requirements.txt &&\
    apt-get clean

EXPOSE 5432

WORKDIR DB

CMD CMD pg_ctlcluster 14 main start &&\
    psql -U postgres postgres -c "ALTER USER postgres PASSWORD 'ostisGovno'"&&\
    . .venv/bin/activate &&\
    echo "Fill DB with embeddings..." &&\
    python3 postgres/import_db.py json_path=./landmarks.json neo4j_host=0.0.0.0 neo4j_port=7687 neo4j_user=neo4j neo4j_password=ostisGovno postgres_host=0.0.0.0 postgres_port=5432 postgres_user=postgres postgres_password=ostisGovno &&\
    echo "Done." &&\
    tail -f /dev/null

