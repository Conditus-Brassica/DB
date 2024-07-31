FROM ubuntu:24.04

WORKDIR service

# install python (common)
RUN apt-get update &&\
    apt-get install python3 -y &&\
    apt-get install python3-venv -y &&\
    apt-get install git -y &&\
    apt-get clean

RUN apt-get install wget gnupg &&\
    git clone https://github.com/Conditus-Brassica/DB.git &&\
    cd DB &&\
    chmod 777 neo4j_installation_script.sh &&\
    python3 -m venv .venv &&\
    . .venv/bin/activate &&\
    pip install -r requirements.txt &&\
    echo $(ls -al) &&\
    sh neo4j_installation_script.sh &&\
    mv ./landmarks.json /var/lib/neo4j/import &&\
    mv ./map_sectors.json /var/lib/neo4j/import &&\
    mv ./regions.json /var/lib/neo4j/import &&\
    mv ./apoc-5.18.0-extended.jar /var/lib/neo4j/plugins &&\
    mv ./neo4j.service /lib/systemd/system/ &&\
    systemctl enable neo4j.service
#    apt-get install iproute2 -y

EXPOSE 7474 7687

ENTRYPOINT . .venv/bin/activate &&\
    python3 import_kb.py user=neo4j password=ostisGovno host=localhost port=7687 regions_filename=regions.json landmarks_filename=landmarks.json map_sectors_filename=map_sectors.json base_dir= landmarks_dirs &&\
    echo "Done"