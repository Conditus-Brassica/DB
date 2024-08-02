# Создание контейнера базы Neo4j

Из этого репозитория нужно взять только dockerfile и собрать его: 

```
docker build -t db_img .
```

Запустить контейнер следующей командой: 

```
docker run -p 7474:7474 -p 7687:7687 db_img
```

Посмотреть базу можно через браузер по адресу localhost:7474
<img src="https://i.scdn.co/image/ab67616d0000b2730ce52f4ba340a1e459e6a978" Title="Vileyskiye cowboys">
