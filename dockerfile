FROM neo4j:5.18.0

WORKDIR service

# install python (common)

RUN apt-get update &&\
    apt-get install python3 -y &&\
    apt-get install python3-venv -y &&\
    apt-get install git -y &&\
    apt-get clean

# clone data (../ is dir service in this script)
RUN git clone https://github.com/Conditus-Brassica/DB.git &&\
    cd DB &&\
    python3 -m venv .venv &&\
    . .venv/bin/activate &&\
    pip install -r requirements.txt &&\
    mv ./landmarks.json /import &&\
    mv ./map_sectors.json /import &&\
    mv ./regions.json /import

WORKDIR DB

# Neo4j settings
ENV NEO4J_AUTH=neo4j/ostisGovno \
    NEO4J_apoc_export_file_enabled=true \
    NEO4J_apoc_import_file_enabled=true \
    NEO4J_apoc_import_file_useneo4jconfig=true \
    NEO4J_PLUGINS=["apoc"] 

VOLUME $HOME/neo4j/data:/data

EXPOSE 7474
EXPOSE 7678

ENTRYPOINT ./wait_db.sh &&\
    . .venv/bin/activate &&\
    python3 import_kb.py user=neo4j password=ostisGovno host=localhost port=7678 regions_filename=regions.json landmarks_filename=landmarks.json map_sectors_filename=map_sectors.json base_dir=landmarks_dirs
