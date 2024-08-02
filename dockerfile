FROM ubuntu:24.04

WORKDIR service

# install python (common)
RUN apt-get update &&\
    apt-get install python3 -y &&\
    apt-get install python3-venv -y &&\
    apt-get install git -y &&\
    apt-get clean

ENV NEO4J_apoc_export_file_enabled=true \
    NEO4J_apoc_import_file_enabled=true \
    NEO4J_apoc_import_file_useneo4jconfig=true

RUN apt-get install wget -y &&\
    apt-get install gnupg -y &&\
    git clone https://github.com/Conditus-Brassica/DB.git &&\
    cd DB &&\
    python3 -m venv .venv &&\
    . .venv/bin/activate &&\
    pip install -r requirements.txt &&\
    wget -O - https://debian.neo4j.com/neotechnology.gpg.key | apt-key add - &&\
    echo 'deb https://debian.neo4j.com stable latest' | tee /etc/apt/sources.list.d/neo4j.list &&\
    apt-get update &&\
    apt-get install neo4j=1:5.18.0 -y &&\
    mv ./landmarks.json /var/lib/neo4j/import &&\
    mv ./map_sectors.json /var/lib/neo4j/import &&\
    mv ./regions.json /var/lib/neo4j/import &&\
    mv neo4j.conf /etc/neo4j/neo4j.conf &&\
    mv apoc.conf /etc/neo4j/apoc.conf &&\
    mv /var/lib/neo4j/labs/apoc-5.18.0-core.jar /var/lib/neo4j/plugins &&\
    apt-get clean

EXPOSE 7474 7687

WORKDIR DB

ENTRYPOINT neo4j-admin dbms set-initial-password  ostisGovno &&\
    . .venv/bin/activate &&\
    sh -c neo4j start &&\
    python3 import_kb.py user=neo4j password=ostisGovno host=localhost port=7687 regions_filename=regions.json landmarks_filename=landmarks.json map_sectors_filename=map_sectors.json base_dir=landmarks_dirs &&\
    tail -f /dev/null &&\
    echo "Done"