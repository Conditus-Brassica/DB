# Создание контейнеров с базами данных

Необходимо создать сеть пользовательскую сеть в docker:

```
docker network create -d bridge custom-bridge-network
```

## Создание контейнера базы Neo4j

Из этого репозитория нужно взять только dockerfile и собрать его: 

```
docker build -t neo4j-image .
```

Запустить контейнер следующей командой: 

```
docker run --network=bridge custom-bridge-network -p 7474:7474 -p 7687:7687 --name neo4j-db neo4j-image
```

Посмотреть базу можно через браузер по адресу localhost:7474

## Создание контейнера базы postgres

Создание образа:

```
docker build -t sql-img .
```

Запуск контейнера

```
docker run --network=bridge custom-bridge-network -p 7688:7687 -p 5432:5432 --name sql-db sql-img
```

**_можно добаить флаг `-d` чтобы освободить терминал_**


<img src="https://i.scdn.co/image/ab67616d0000b2730ce52f4ba340a1e459e6a978" Title="Vileyskiye cowboys">
