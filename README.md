# Создание контейнера базы Neo4j

Из этого репозитория нужно взять только dockerfile и собрать его: 

```
docker build -t neo4j-image .
```

Запустить контейнер следующей командой: 

```
docker run -p 7474:7474 -p 7687:7687 --name neo4j-db neo4j-image
```

Посмотреть базу можно через браузер по адресу localhost:7474

# Создание контейнера базы postgres

Пока что необходимо создавать все вручную

<img src="https://i.scdn.co/image/ab67616d0000b2730ce52f4ba340a1e459e6a978" Title="Vileyskiye cowboys">
