import sqlalchemy


engine = sqlalchemy.create_engine("postgresql://postgres:ostisGovno@0.0.0.0:5432/postgres")

with engine.begin() as tx:
    tx.execute(sqlalchemy.text("CREATE SCHEMA ostisGovno;"))
    tx.execute(
        sqlalchemy.text(
            """
            CREATE TABLE ostisGovno.landmarks_embeddings(
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                landmark_name       TEXT NOT NULL,
                landmark_latitude   FLOAT NOT NULL,
                landmark_longitude  FLOAT NOT NULL,
                embedding           FLOAT[],
                UNIQUE (landmark_name, landmark_latitude, landmark_longitude)
            );
            """
        )
    )
    tx.execute(
        sqlalchemy.text(
            """
            CREATE INDEX IF NOT EXISTS landmark_name_latitude_longitude_b_tree_index
            ON ostisGovno.landmarks_embeddings
            USING btree
            (landmark_name, landmark_latitude, landmark_longitude); 
            """
        )
    )
