from transformers import BertTokenizer, BertModel
import torch
import sqlalchemy
import neo4j
import json

json_path = "/home/vodohleb/Downloads/landmarks.json"
neo4j_host = "localhost"
neo4j_port = 7687
neo4j_user = "neo4j"
neo4j_password = "ostisGovno"
postgres_host = "0.0.0.0"
postgres_port = 5432
postgres_user = "postgres"
postgres_password = "ostisGovno"

postgres_engine = sqlalchemy.create_engine(
    f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/postgres"
)

neo4j_driver = neo4j.GraphDatabase.driver(f"bolt://{neo4j_host}:{neo4j_port}", auth=(neo4j_user, neo4j_password))

if torch.cuda.is_available():
    device = torch.device("cuda:0")
else:
    device = torch.device("cpu")

tokenizer = BertTokenizer.from_pretrained("DeepPavlov/rubert-base-cased")
model = BertModel.from_pretrained("DeepPavlov/rubert-base-cased")
model = model.to(device)

with open(json_path, 'r', encoding='utf-8') as landmarks_file:
    json_landmarks_list = json.load(landmarks_file)

# All process should be a transaction
with postgres_engine.begin() as tx:
    for json_landmark in json_landmarks_list:
        with torch.no_grad():
            # Get the embedding tensor
            tokenized_landmark_summary = tokenizer(
                json_landmark["summary"], return_tensors='pt', padding=True, truncation=True, max_length=512
            )

            for key, value in tokenized_landmark_summary.items():
                tokenized_landmark_summary[key] = tokenized_landmark_summary[key].type(torch.int32).to(device)

            # mean of last hidden state of model is used as embedding
            landmark_embedding_torch = model(**tokenized_landmark_summary).last_hidden_state.mean(dim=1)[0]

            landmark_embedding = landmark_embedding_torch.detach().cpu().tolist()
            del landmark_embedding_torch


        # Get the correct landmark info from neo4j
        neo4j_landmark = neo4j_driver.execute_query(
            """
            MATCH (landmark: Landmark)
                WHERE
                    landmark.latitude = $latitude AND
                    landmark.longitude = $longitude AND
                    landmark.name STARTS WITH $name
            RETURN
                landmark.name AS landmark_name,
                landmark.latitude AS landmark_latitude,
                landmark.longitude AS landmark_longitude
            LIMIT 1;
            """,
            result_transformer_=neo4j.Result.single,
            latitude=json_landmark["coordinates"]["latitude"],
            longitude=json_landmark["coordinates"]["longitude"],
            name=json_landmark["name"]
        )

        # Write embedding to postgres
        tx.execute(
            sqlalchemy.text(
                """
                INSERT INTO ostisGovno.landmarks_embeddings
                    (landmark_name, landmark_latitude, landmark_longitude, embedding)
                    VALUES (:landmark_name, :landmark_latitude, :landmark_longitude, :embedding)
                    ON CONFLICT ON CONSTRAINT landmarks_embeddings_landmark_name_landmark_latitude_landma_key 
                        DO UPDATE SET embedding = :embedding;
                """
            ),
            {
                "landmark_name": neo4j_landmark.get("landmark_name"),
                "landmark_latitude": neo4j_landmark.get("landmark_latitude"),
                "landmark_longitude": neo4j_landmark.get("landmark_longitude"),
                "embedding": landmark_embedding
            }
        )


neo4j_driver.close()



