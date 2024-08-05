# Author: Vodohleb04
import datetime
import sys
import os
import pathlib
from neo4j import GraphDatabase, Driver, exceptions


AVAILABLE_ARGS = [
    "user", "password", "host", "port",
    "regions_filename", "landmarks_filename", "map_sectors_filename",
    "base_dir", "save_existing_id_codes"
]


CONSTRAINTS_QUERIES = [
    """CREATE CONSTRAINT landmark_name_longitude_latitude_uniqueness IF NOT EXISTS
            FOR (landmark: Landmark) REQUIRE (landmark.name, landmark.longitude, landmark.latitude) IS UNIQUE;""",
    """CREATE CONSTRAINT region_name_uniqueness IF NOT EXISTS
            FOR (region: Region) REQUIRE region.name IS UNIQUE;""",
    """CREATE CONSTRAINT landmark_category_name_uniqueness IF NOT EXISTS
            FOR (landmarkCategory: LandmarkCategory) REQUIRE landmarkCategory.name IS UNIQUE;""",
    """CREATE CONSTRAINT map_sector_name_uniqueness IF NOT EXISTS
            FOR (mapSector: MapSector) REQUIRE mapSector.name IS UNIQUE;""",
    """CREATE CONSTRAINT user_account_login_uniqueness IF NOT EXISTS
            FOR (userAccount: UserAccount) REQUIRE userAccount.login IS UNIQUE;""",
    """CREATE CONSTRAINT guide_id_code_uniqueness IF NOT EXISTS
            FOR (guideAccount: GuideAccount) REQUIRE guideAccount.id_code IS UNIQUE;""",
    """CREATE CONSTRAINT note_category_name_uniqueness IF NOT EXISTS
            FOR (noteCategory: NoteCategory) REQUIRE noteCategory.name IS UNIQUE;""",
    """CREATE CONSTRAINT note_title_uniqueness IF NOT EXISTS
            FOR (note: Note) REQUIRE note.title IS UNIQUE;""",
    """CREATE CONSTRAINT route_index_id_uniqueness IF NOT EXISTS
            FOR (route: Route) REQUIRE route.index_id IS UNIQUE;
    """
]


INDEXES_QUERIES = [
    """ 
    CREATE LOOKUP INDEX labels_lookup_index IF NOT EXISTS
    FOR (n)
    ON EACH labels(n);
    """,
    """
    CREATE LOOKUP INDEX relationship_types_lookup_index IF NOT EXISTS
    FOR ()-[r]-()
    ON EACH type(r); 
    """,
    """
    CREATE FULLTEXT INDEX region_name_fulltext_index IF NOT EXISTS
    FOR (region:Region)
    ON EACH [region.name];
    """,
    """
    CREATE TEXT INDEX landmark_name_text_index IF NOT EXISTS
    FOR (landmark: Landmark)
    ON (landmark.name);
    """,
    """
    CREATE FULLTEXT INDEX landmark_category_name_fulltext_index IF NOT EXISTS
    FOR (landmarkCategory: LandmarkCategory)
    ON EACH [landmarkCategory.name];
    """,
    """
    CREATE INDEX landmark_longitude_latitude_range_index IF NOT EXISTS
    FOR (landmark:Landmark)
    ON (
        landmark.longitude,
        landmark.latitude
    );
    """,
    """
    CREATE FULLTEXT INDEX map_sector_name_fulltext_index IF NOT EXISTS
    FOR (mapSector: MapSector)
    ON EACH [mapSector.name];
    """,
    """
    CREATE INDEX map_sector_tl_longitude_latitude_range_index IF NOT EXISTS
    FOR (mapSector: MapSector)
    ON (
        mapSector.tl_longitude,
        mapSector.tl_latitude
    );
    """,
    """
    CREATE TEXT INDEX user_account_login_text_index IF NOT EXISTS
    FOR (userAccount: UserAccount)
    ON (userAccount.login);
    """,
    """
    CREATE FULLTEXT INDEX note_category_name_fulltext_index IF NOT EXISTS
    FOR (noteCategory: NoteCategory)
    ON EACH [noteCategory.name];
    """,
    """
    CREATE FULLTEXT INDEX note_title_fulltext_index IF NOT EXISTS
    FOR (note: Note)
    ON EACH [note.title];
    """,
    """  
    CREATE INDEX route_index_id_range_index IF NOT EXISTS
    FOR (route: Route)
    ON (route.index_id);
    """
]


def create_constraints(driver):
    with driver.session() as session:
        for query in CONSTRAINTS_QUERIES:
            session.run(query)


def create_indexes(driver):
    with driver.session() as session:
        for query in INDEXES_QUERIES:
            session.run(query)


def import_regions(driver, filename):
    filename = f"file:///{filename}"
    with driver.session() as session:
        session.run(
            """
            // Imports regions from json file (Regions of types: Country, State, District)
            CALL apoc.load.json($filename) YIELD value
            UNWIND value AS region_json
            WITH region_json,
                CASE
                    WHEN region_json.type = 'country' THEN 'Country'
                    WHEN region_json.type = 'state' THEN 'State'
                    WHEN region_json.type = 'district' THEN 'District'
                END AS regionType
            MERGE (region: Region {name: region_json.name})
            WITH *
            CALL apoc.create.addLabels(region, [regionType]) YIELD node AS labeledRegion
            WITH *
            UNWIND 
                CASE
                    WHEN region_json.include = [] THEN [null] 
                    WHEN region_json.include IS null THEN [null]
                    ELSE region_json.include
                END AS includedRegionName
            WITH *,
                CASE
                    WHEN region_json.type = 'country' THEN 'State'
                    WHEN region_json.type = 'state' THEN 'District'
                    WHEN region_json.type = 'district' THEN 'City'
                END AS subRegionType
            CALL apoc.do.when(
                includedRegionName IS NOT null,
                "
                    WITH *
                    MERGE (includedRegion: Region {name: includedRegionName})
                    WITH *
                    CALL apoc.create.addLabels(includedRegion, [subRegionType]) YIELD node AS labeledIncludedRegion
                    WITH *
                    MATCH (labeledRegion: Region {name: labeledRegionName})
                    MERGE (labeledRegion)-[:INCLUDE]->(labeledIncludedRegion)
                    RETURN True
                ",
                "RETURN False",
                {
                    labeledRegionName: labeledRegion.name,
                    includedRegionName: includedRegionName, 
                    subRegionType: subRegionType
                    
                }
            ) YIELD value AS included_value
            WITH *
            UNWIND 
                CASE 
                    WHEN region_json.bordered = [] THEN [null]
                    WHEN region_json.bordered IS null THEN [null]
                    ELSE region_json.bordered
                END AS borderedRegionName
            WITH *
            CALL apoc.do.when(
                borderedRegionName IS NOT null,
                "
                    MERGE (borderedRegion: Region {name: borderedRegionName})
                    WITH *
                    CALL apoc.create.addLabels(borderedRegion, [regionType]) YIELD node AS labeledBorderedRegion
                    WITH *
                    MATCH (labeledRegion: Region {name: labeledRegionName})
                    MERGE (labeledRegion)-[:NEIGHBOUR_REGION]-(labeledBorderedRegion)
                    RETURN True
                ",
                "RETURN False",
                {
                    labeledRegionName: labeledRegion.name,
                    borderedRegionName: borderedRegionName,
                    regionType: regionType
                }
            ) YIELD value AS neighbour_value
            WITH *
            RETURN 1 as res, included_value AS has_included, neighbour_value AS has_neighbour
            """,
            filename=filename
        )


def check_connection(driver):
    with driver.session() as session:
        session.run(
            """MERGE (n: CheckNode {name: "ostisGovno"});"""
        )


def import_landmarks(driver, filename):
    filename = f"file:///{filename}"
    with driver.session() as session:
        session.run(
            """
            // Importing landmarks from json
            CALL apoc.load.json($filename) YIELD value
            UNWIND value AS landmark_json
            WITH landmark_json
            MERGE (landmark: Landmark {name: landmark_json.name})
            SET 
                landmark.latitude = toFloat(landmark_json.coordinates.latitude),
                landmark.longitude = toFloat(landmark_json.coordinates.longitude)
            MERGE (category: LandmarkCategory {name: landmark_json.category})
            MERGE (landmark)-[refer:REFERS]->(category)
            SET refer.main_category_flag = True
            WITH landmark_json, landmark,
                CASE
                    WHEN landmark_json.subcategory = [] THEN [null]
                    WHEN landmark_json.subcategory IS null THEN [null]
                    ELSE landmark_json.subcategory
                END AS subcategories_names
            UNWIND subcategories_names AS subcategory_name
            WITH landmark_json, landmark, subcategory_name
            CALL apoc.do.when(
                subcategory_name IS NOT null,
                "
                    MERGE (subcategory: LandmarkCategory {name: subcategory_name})
                    MERGE (landmark)-[refer:REFERS]->(subcategory)
                    SET refer.main_category_flag = False
                    RETURN True
                ",
                "RETURN False",
                {
                    landmark: landmark,
                    subcategory_name: subcategory_name
                }
            ) YIELD value AS subcategory_result
            WITH landmark_json, landmark, subcategory_result
            CALL apoc.do.case(
                [
                    landmark_json.located.state IS null,
                    "
                        MATCH (state_city: Region {name: located.city})
                        SET state_city:State:City
                        WITH landmark, located, state_city
                        MATCH (district: Region {name: located.district})
                        SET district:District
                        MERGE (landmark)-[:LOCATED]->(district)
                        RETURN 'state-city'
                    ",
                    landmark_json.located.district IS null,
                    "
                        MERGE (district_city: Region {name: located.city})
                        SET district_city:District:City
                        MERGE (landmark)-[:LOCATED]->(district_city)
                        RETURN 'district-city'
                    "
                ],
                "
                    MATCH (district: District {name: located.district})
                    MERGE (city: Region {name: located.city})
                        ON CREATE SET city:City
                    WITH located, landmark, city, district
                    OPTIONAL MATCH (:District)-[inclusion:INCLUDE]->(city)
                    WITH located, landmark, city, district, inclusion
                    CALL apoc.do.when(
                        inclusion IS NULL,
                        'CREATE (district)-[:INCLUDE]->(city) RETURN True',
                        'RETURN False',
                        {district: district, city: city}
                    ) YIELD value AS inclusion_already_exists
                    WITH city, located, landmark
                    CALL {
                            WITH city, located, landmark
                            MATCH 
                                (city)
                                    <-[:INCLUDE]-
                                (district: District)
                                    <-[:INCLUDE]-
                                (state: State)
                                    <-[:INCLUDE]-
                                (country:Country)
                            WITH located, city, district, state, country, landmark
                            CALL apoc.do.case(
                                [
                                    country.name <> located.country,
                                    '
                                        MERGE (this_city:Region:City 
                                            {name: located.city + opened_parenthesis + located.country + closed_parenthesis}
                                        )
                                        WITH *
                                        MATCH (other_city: City WHERE other_city.name = city_name)
                                        WITH *
                                        SET other_city.name = toString(
                                            other_city.name + opened_parenthesis + other_country_name + closed_parenthesis
                                        )
                                        WITH this_city, landmark, located
                                        MATCH (this_district:District {name: located.district})
                                        MERGE (this_city)<-[:INCLUDE]-(this_district)
                                        MERGE (landmark)-[:LOCATED]->(this_city)
                                        RETURN 1
                                    ',
                                    district.name <> located.district,
                                    '
                                        MERGE (this_city:Region:City 
                                            {name: located.city + opened_parenthesis + located.district + closed_parenthesis}
                                        )
                                        WITH *
                                        MATCH (other_city: City WHERE other_city.name = city_name)
                                        WITH *
                                        SET other_city.name = toString(
                                            other_city.name + opened_parenthesis + other_district_name + closed_parenthesis
                                        )
                                        WITH this_city, landmark, located
                                        MATCH (this_district:District {name: located.district})
                                        MERGE (this_city)<-[:INCLUDE]-(this_district)
                                        MERGE (landmark)-[:LOCATED]->(this_city)
                                        RETURN 2
                                    ',
                                    state.name <> located.state,
                                    '
                                        MERGE (this_city:Region:City 
                                            {name: located.city + opened_parenthesis + located.district + spacer + located.state + closed_parenthesis}
                                        )
                                        WITH *
                                        MATCH (other_city: City WHERE other_city.name = city_name)
                                        WITH *
                                        SET other_city.name = toString(
                                            other_city.name + opened_parenthesis + other_district_name + spacer + other_state_name + closed_parenthesis
                                        )
                                        WITH this_city, landmark, located
                                        MATCH (this_district:District {name: located.district})
                                        MERGE (this_city)<-[:INCLUDE]-(this_district)
                                        MERGE (landmark)-[:LOCATED]->(this_city)
                                        RETURN 3
                                    '
                                ], 
                                '
                                    MATCH (this_city: City WHERE this_city.name = city_name)
                                    MERGE (landmark)-[:LOCATED]->(this_city)
                                    RETURN 4
                                ',
                                {
                                    landmark: landmark,
                                    city_name: city.name,
                                    other_country_name: country.name,
                                    other_state_name: state.name,
                                    other_district_name: district.name,
                                    located: located,
                                    opened_parenthesis: '(',
                                    closed_parenthesis: ')',
                                    spacer: ' '
                                }
                            ) YIELD value AS city_match
                            RETURN city_match
                        }
                        RETURN 'city'
                ",
                {
                    located: landmark_json.located,
                    landmark: landmark
                }
            ) YIELD value AS city_type
            WITH subcategory_result, city_type
            RETURN 1 as res, subcategory_result, city_type
            """,
            filename=filename
        )


def import_map_sectors(driver, filename):
    filename = f"file:///{filename}"
    with driver.session() as session:
        session.run(
            """
            // Imports map seqtors structured in form of quadtree 
            // (it may be not quadtree, but sector is presented in 
            // form of rectangle (top left corner and buttom right corner))
            MATCH (country:Country WHERE country.name = $country_name)
            MERGE (country_map_sectors: CountryMapSectors)
            MERGE (country_map_sectors)<-[:DIVIDED_ON_SECTORS]-(country)
            WITH country_map_sectors
            CALL apoc.load.json($filename) YIELD value
            UNWIND value AS sector_json
            WITH country_map_sectors, sector_json
            MERGE (sector: MapSector {name: sector_json.name})
            MERGE (country_map_sectors)-[:INCLUDE_SECTOR]->(sector)
            SET
                sector.tl_latitude = toFloat(sector_json.TL.latitude),
                sector.tl_longitude = toFloat(sector_json.TL.longitude),
                sector.br_latitude = toFloat(sector_json.BR.latitude),
                sector.br_longitude = toFloat(sector_json.BR.longitude)
            WITH sector_json, sector,
                CASE
                    WHEN sector_json.coordinates = [] THEN [null]
                    WHEN sector_json.coordinates IS null THEN [null]
                    ELSE sector_json.coordinates
                END AS included_landmarks_coordinates
            UNWIND included_landmarks_coordinates AS included_landmark_coordinates
            WITH sector_json, sector, included_landmark_coordinates
            CALL apoc.do.when(
                included_landmark_coordinates IS NOT null,
                "
                    MATCH (
                        landmark:Landmark {
                            latitude: included_landmark_coordinates.latitude,
                            longitude: included_landmark_coordinates.longitude
                        }
                    )
                    MERGE (landmark)-[:IN_SECTOR]->(sector)
                    RETURN True
                ",
                "RETURN False",
                {
                    included_landmark_coordinates: included_landmark_coordinates,
                    sector: sector
                }
            ) YIELD value AS included_landmark_function_result
            WITH
                sector_json,
                sector,
                CASE
                    WHEN sector_json.neighbours = [] THEN [null]
                    WHEN sector_json.neighbours IS null THEN [null]
                    ELSE sector_json.neighbours
                END AS neighbour_sectors_names
            UNWIND neighbour_sectors_names AS neighbour_sector_name
            CALL apoc.do.when(
                neighbour_sector_name IS NOT null,
                "
                    MERGE (neighbour: MapSector {name: $neighbour_sector_name})
                    MERGE (sector)-[:NEIGHBOUR_SECTOR]-(neighbour)
                    RETURN True
                ",
                "RETURN False",
                {
                    neighbour_sector_name: neighbour_sector_name,
                    sector: sector   
                }
            ) YIELD value AS neighbour_value
            WITH *
            RETURN 1 AS res, neighbour_value AS has_neighbour
            """,
            country_name="Беларусь", filename=filename
        )


def connect_landmarks_with_map_sectors(driver):
    with driver.session() as session:
        session.run(
            """
            // Connects all landmarks with their map sectors
            MATCH (landmark: Landmark)
                WHERE NOT (landmark)-[:IN_SECTOR]->(:MapSector)
            MATCH (mapSector: MapSector)
            CALL apoc.do.when(
                point.withinBBox(
                    point({latitude: landmark.latitude, longitude: landmark.longitude, crs:'WGS-84'}),
                    point({latitude: mapSector.br_latitude, longitude: mapSector.tl_longitude, crs:'WGS-84'}),
                    point({latitude: mapSector.tl_latitude, longitude: mapSector.br_longitude, crs:'WGS-84'})
                ) = True,
                "
                    MERGE (landmark)-[:IN_SECTOR]->(mapSector)
                    RETURN True;
                ",
                "
                    RETURN False;
                ",
                {landmark: landmark, mapSector: mapSector}
            ) YIELD value AS added_to_sector
            WITH added_to_sector
                WHERE added_to_sector = True
            RETURN count(added_to_sector) AS added_amount
            """
        )


def encoding_regions_and_landmarks_change_id_code(driver, base_dir):
    country_counter = 0
    current_country_name = ""
    state_counter = 0
    current_state_name = ""
    district_counter = 0
    current_district_name = ""
    city_counter = 0
    current_city_name = ""
    landmark_counter = 0

    def write_region_id_code(region_name, id_code):
        nonlocal session
        session.run(
            """
            CALL db.index.fulltext.queryNodes('region_name_fulltext_index', $region_name)
                YIELD score, node AS region
            WITH score, region
                ORDER BY score DESC
                LIMIT 1
            SET region.id_code = $id_code
            """,
            region_name=region_name, id_code=id_code
        )

    def write_landmark_id_code_and_path(landmark_name, landmark_latitude, landmark_longitude, id_code, path):
        nonlocal session
        session.run(
            """
            MATCH (landmark)
                WHERE landmark.name STARTS WITH $landmark_name 
                    AND landmark.latitude = toFloat($landmark_latitude)
                    AND landmark.longitude = toFloat($landmark_longitude)
            SET landmark.id_code = $id_code, landmark.path = $path
            """,
            landmark_name=landmark_name,
            landmark_latitude=landmark_latitude,
            landmark_longitude=landmark_longitude,
            id_code=id_code,
            path=path
        )

    def step_on_record(record):
        # Name constraints are unique, so there is no need to update current_name_<region_type> and
        # it's enough to update counter only for the next included region_type but not for every
        nonlocal session, base_dir
        nonlocal country_counter, state_counter, district_counter, city_counter, landmark_counter
        nonlocal current_country_name, current_state_name, current_district_name, current_city_name

        if record.get("country_name") != current_country_name:
            current_country_name = record.get("country_name")
            country_counter += 1
            state_counter = 0
            if current_country_name:
                write_region_id_code(current_country_name, country_counter)
        if record.get("state_name") != current_state_name:
            current_state_name = record.get("state_name")
            state_counter += 1
            district_counter = 0
            if current_state_name:
                write_region_id_code(current_state_name, state_counter)
        if record.get("district_name") != current_district_name:
            current_district_name = record.get("district_name")
            district_counter += 1
            city_counter = 0
            if current_district_name:
                write_region_id_code(current_district_name, district_counter)
        if record.get("city_name") != current_city_name:
            current_city_name = record.get("city_name")
            city_counter += 1
            landmark_counter = 1
            if current_city_name:
                write_region_id_code(current_city_name, city_counter)
        if record.get("landmark_name"):
            path = os.path.join(
                base_dir, f"{country_counter if current_country_name else 0}/"
                          f"{state_counter if current_state_name else 0}/"
                          f"{district_counter if current_district_name else 0}/"
                          f"{city_counter if current_city_name else 0}/"
                          f"{landmark_counter}"
            )
            write_landmark_id_code_and_path(
                record.get("landmark_name"), record.get("landmark_latitude"), record.get("landmark_longitude"),
                landmark_counter, path
            )

    with driver.session() as session:
        result = session.run(
            """
            MATCH (country: Country)
            OPTIONAL MATCH (state: State)<-[:INCLUDE]-(country) 
            OPTIONAL MATCH (district: District)<-[:INCLUDE]-(state)
            OPTIONAL MATCH (city: City)<-[:INCLUDE]-(district)
            CALL apoc.do.case(
                [
                    city IS NOT null,
                    "
                        OPTIONAL MATCH (landmark: Landmark)-[:LOCATED]->(city)
                        RETURN 
                            landmark.name AS landmark_name,
                            landmark.latitude AS landmark_latitude,
                            landmark.longitude AS landmark_longitude;
                    ",
                    district IS NOT null,
                    "
                        OPTIONAL MATCH (landmark: Landmark)-[:LOCATED]->(district)
                        RETURN 
                            landmark.name AS landmark_name,
                            landmark.latitude AS landmark_latitude,
                            landmark.longitude AS landmark_longitude;
                    "
                ],
                "
                    RETURN 
                        null as landmark_name,
                        null as landmark_latitude,
                        null as landmark_longitude;
                ",
                {city: city, district: district}
            ) YIELD value
            RETURN DISTINCT
                country.name AS country_name,
                state.name AS state_name,
                district.name AS district_name,
                city.name AS city_name,
                value.landmark_name AS landmark_name,
                value.landmark_latitude AS landmark_latitude,
                value.landmark_longitude AS landmark_longitude
            ORDER BY 
                country_name ASC,
                state_name ASC,
                district_name ASC,
                city_name ASC,
                landmark_name ASC
            """
        )
        for record in result:
            step_on_record(record)


def encoding_regions_and_landmarks_no_change_id_code(driver, base_dir):
    def find_last_used_id_code_country():
        nonlocal session
        last_used_id_code_res = session.run(
            """
            MATCH (country: Country) RETURN max(country.id_code) AS last_used_id_code;
            """
        )
        last_used_id_code = last_used_id_code_res.single().get("last_used_id_code")
        if last_used_id_code is None:
            return 0
        else:
            return last_used_id_code

    def find_last_used_id_code_state(country_name: str):
        nonlocal session
        last_used_id_code_res = session.run(
            """
            CALL db.index.fulltext.queryNodes('region_name_fulltext_index', $country_name)
                YIELD score, node AS country
            WITH score, country
                ORDER BY score DESC
                LIMIT 1
            OPTIONAL MATCH (country)-[:INCLUDE]->(state: State)
            RETURN country.name AS country_name, max(state.id_code) AS last_used_id_code;
            """,
            country_name=country_name
        )
        last_used_id_code = last_used_id_code_res.single().get("last_used_id_code")
        if last_used_id_code is None:
            return 0
        else:
            return last_used_id_code

    def find_last_used_id_code_district(state_name: str):
        nonlocal session
        last_used_id_code_res = session.run(
            """
            CALL db.index.fulltext.queryNodes('region_name_fulltext_index', $state_name)
                YIELD score, node AS state
            WITH score, state
                ORDER BY score DESC
                LIMIT 1
            OPTIONAL MATCH (state)-[:INCLUDE]->(district: District)
            RETURN state.name AS state_name, max(district.id_code) AS last_used_id_code;
            """,
            state_name=state_name
        )
        last_used_id_code = last_used_id_code_res.single().get("last_used_id_code")
        if last_used_id_code is None:
            return 0
        else:
            return last_used_id_code

    def find_last_used_id_code_city(district_name: str):
        nonlocal session
        last_used_id_code_res = session.run(
            """
            CALL db.index.fulltext.queryNodes('region_name_fulltext_index', $district_name)
                YIELD score, node AS district
            WITH score, district
                ORDER BY score DESC
                LIMIT 1
            OPTIONAL MATCH (district)-[:INCLUDE]->(city: City)
            RETURN district.name AS district_name, max(city.id_code) AS last_used_id_code;
            """,
            district_name=district_name
        )
        last_used_id_code = last_used_id_code_res.single().get("last_used_id_code")
        if last_used_id_code is None:
            return 0
        else:
            return last_used_id_code

    def find_last_used_id_code_landmark(region_name: str):
        nonlocal session
        last_used_id_code_res = session.run(
            """
            CALL db.index.fulltext.queryNodes('region_name_fulltext_index', $region_name)
                YIELD score, node AS region
            WITH score, region
                ORDER BY score DESC
                LIMIT 1
            OPTIONAL MATCH (region)<-[:LOCATED]-(landmark: Landmark)
            RETURN region.name AS region_name, max(landmark.id_code) AS last_used_id_code;
            """,
            region_name=region_name
        )
        last_used_id_code = last_used_id_code_res.single().get("last_used_id_code")
        if last_used_id_code is None:
            return 0
        else:
            return last_used_id_code

    def write_region_id_code(region_name, id_code):
        nonlocal session
        session.run(
            """
            CALL db.index.fulltext.queryNodes('region_name_fulltext_index', $region_name)
                YIELD score, node AS region
            WITH score, region
                ORDER BY score DESC
                LIMIT 1
            SET region.id_code = $id_code
            """,
            region_name=region_name, id_code=id_code
        )

    def write_landmark_id_code_and_path(landmark_name, landmark_latitude, landmark_longitude, id_code, path):
        nonlocal session
        session.run(
            """
            MATCH (landmark)
                WHERE landmark.name STARTS WITH $landmark_name 
                    AND landmark.latitude = toFloat($landmark_latitude)
                    AND landmark.longitude = toFloat($landmark_longitude)
            SET landmark.id_code = $id_code, landmark.path = $path
            """,
            landmark_name=landmark_name,
            landmark_latitude=landmark_latitude,
            landmark_longitude=landmark_longitude,
            id_code=id_code,
            path=path
        )

    def step_on_record(record):
        # Name constraints are unique, so there is no need to update current_name_<region_type> and
        # it's enough to update counter only for the next included region_type but not for every
        nonlocal session, base_dir

        country_id_code = record.get("country_id_code")
        if country_id_code is None:
            if record.get("country_name") is not None:
                last_used_country_id_code = find_last_used_id_code_country()
                write_region_id_code(record.get("country_name"), last_used_country_id_code + 1)
                country_id_code = last_used_country_id_code + 1

        state_id_code = record.get("state_id_code")
        if state_id_code is None:
            if record.get("state_name") is not None:
                last_used_state_id_code = find_last_used_id_code_state(record.get("country_name"))
                write_region_id_code(record.get("state_name"), last_used_state_id_code + 1)
                state_id_code = last_used_state_id_code + 1
            else:
                state_id_code = 0

        district_id_code = record.get("district_id_code")
        if district_id_code is None:
            if record.get("district_name") is not None:
                last_used_district_id_code = find_last_used_id_code_district(record.get("state_name"))
                write_region_id_code(record.get("district_name"), last_used_district_id_code + 1)
                district_id_code = last_used_district_id_code + 1
            else:
                district_id_code = 0

        city_id_code = record.get("city_id_code")
        if city_id_code is None:
            if record.get("city_name") is not None:
                last_used_city_id_code = find_last_used_id_code_city(record.get("district_name"))
                write_region_id_code(record.get("city_name"), last_used_city_id_code + 1)
                city_id_code = last_used_city_id_code + 1
            else:
                city_id_code = 0

        if record.get("landmark_id_code") is None:
            if record.get("landmark_name") is not None:
                if record.get("city_name") is None: 
                    last_used_landmark_id_code = find_last_used_id_code_landmark(record.get("district_name"))
                else:
                    last_used_landmark_id_code = find_last_used_id_code_landmark(record.get("city_name"))
                path = os.path.join(
                    base_dir, f"{country_id_code}/"
                              f"{state_id_code}/"
                              f"{district_id_code}/"
                              f"{city_id_code}/"
                              f"{last_used_landmark_id_code + 1}"
                )
                write_landmark_id_code_and_path(
                    record.get("landmark_name"), record.get("landmark_latitude"), record.get("landmark_longitude"),
                    last_used_landmark_id_code + 1, path
                )

    with driver.session() as session:
        amount_res = session.run(
            """
            MATCH (landmark: Landmark)
            WITH count(landmark) AS landmarks_amount
            MATCH (region: Region)
            RETURN count(region) AS regions_amount, landmarks_amount
            """
        )
        amount_record = amount_res.single()
        landmarks_amount = amount_record.get("landmarks_amount")
        regions_amount = amount_record.get("regions_amount")
        for i in range(landmarks_amount + regions_amount):  # max possible amount of records
            result = session.run(
                """
                MATCH (country: Country)
                OPTIONAL MATCH (state: State)<-[:INCLUDE]-(country) 
                OPTIONAL MATCH (district: District)<-[:INCLUDE]-(state)
                OPTIONAL MATCH (city: City)<-[:INCLUDE]-(district)
                CALL apoc.do.case(
                    [
                        city IS NOT null,
                        "
                            OPTIONAL MATCH (landmark: Landmark)-[:LOCATED]->(city)
                            RETURN 
                                landmark.name AS landmark_name,
                                landmark.latitude AS landmark_latitude,
                                landmark.longitude AS landmark_longitude,
                                landmark.id_code AS landmark_id_code;
                        ",
                        district IS NOT null,
                        "
                            OPTIONAL MATCH (landmark: Landmark)-[:LOCATED]->(district)
                            RETURN 
                                landmark.name AS landmark_name,
                                landmark.latitude AS landmark_latitude,
                                landmark.longitude AS landmark_longitude,
                                landmark.id_code AS landmark_id_code;
                        "
                    ],
                    "
                        RETURN 
                            null as landmark_name,
                            null as landmark_latitude,
                            null as landmark_longitude,
                            null as landmark_id_code;
                    ",
                    {city: city, district: district}
                ) YIELD value
                RETURN DISTINCT
                    country.name AS country_name,
                    country.id_code AS country_id_code,
                    state.name AS state_name,
                    state.id_code AS state_id_code,
                    district.name AS district_name,
                    district.id_code AS district_id_code,
                    city.name AS city_name,
                    city.id_code AS city_id_code,
                    value.landmark_name AS landmark_name,
                    value.landmark_latitude AS landmark_latitude,
                    value.landmark_longitude AS landmark_longitude,
                    value.landmark_id_code AS landmark_id_code
                ORDER BY 
                    country_name ASC,
                    state_name ASC,
                    district_name ASC,
                    city_name ASC,
                    landmark_name ASC
                SKIP $offset
                LIMIT 1
                """,
                offset=i
            )
            record = result.single()
            if record:
                step_on_record(record)
            else:
                break  # All available records has been used


def run_cypher_scripts(
    driver,
    regions_filename, landmarks_filename, map_sectors_filename,
    base_dir,
    save_existing_id_codes,
    start_time
):
    try:
        last_operation = datetime.datetime.now()

        print("Creating constraints...", flush=True)
        create_constraints(driver)
        print(f"Constraints are created in {datetime.datetime.now() - last_operation}", flush=True)
        last_operation = datetime.datetime.now()

        print("Creating indexes...", flush=True)
        create_indexes(driver)
        print(f"Indexes created in {datetime.datetime.now() - last_operation}", flush=True)
        last_operation = datetime.datetime.now()

        print(f"Importing regions from \"file:///{regions_filename}\"...", flush=True)
        import_regions(driver, regions_filename)
        print(f"Regions have been imported in {datetime.datetime.now() - last_operation}", flush=True)
        last_operation = datetime.datetime.now()

        print(f"Importing map sectors from \"file:///{map_sectors_filename}\"...", flush=True)
        import_map_sectors(driver, map_sectors_filename)
        print(f"Map sectors have been imported in {datetime.datetime.now() - last_operation}", flush=True)
        last_operation = datetime.datetime.now()

        print(f"Importing landmarks from \"file:///{landmarks_filename}\"...", flush=True)
        import_landmarks(driver, landmarks_filename)
        print(f"Landmarks have been imported in {datetime.datetime.now() - last_operation}", flush=True)
        last_operation = datetime.datetime.now()
        print("Connecting map sectors with landmarks...", flush=True)
        connect_landmarks_with_map_sectors(driver)
        print(f"Landmarks have been connected with map sectors in {datetime.datetime.now() - last_operation}", flush=True)
        last_operation = datetime.datetime.now()

        print("Encoding regions and landmarks...")
        if save_existing_id_codes:
            encoding_regions_and_landmarks_no_change_id_code(driver, base_dir)
        else:
            encoding_regions_and_landmarks_change_id_code(driver, base_dir)
        print(f"Landmarks and regions have been encoded in {datetime.datetime.now() - last_operation}", flush=True)

        print(f"Knowledge bas has been imported. Complete in {datetime.datetime.now() - start_time}", flush=True)

    except Exception as e:
        print("ERROR OCCURED!", flush=True)
        print(f"{e.args[0]}, Error type: {type(e)}", flush=True)


def import_function(
        user, password, host, port,
        regions_filename, landmarks_filename, map_sectors_filename,
        base_dir, save_existing_id_codes
):
    start = datetime.datetime.now()
    print("Trying to connect to the knowledge base...", flush=True)
    with GraphDatabase.driver(f'bolt://{host}:{port}', auth=(user, password)) as driver:
        check_connection(driver)
        print("Knowledge base is successfully connected", flush=True)

        run_cypher_scripts(driver, regions_filename, landmarks_filename, map_sectors_filename, base_dir, save_existing_id_codes, start)


def main():
    args = {}
    for arg in sys.argv[1:]:
        arg_pair = arg.split("=")
        if len(arg_pair) != 2:
            raise AttributeError(
                f"Invalid argument \"{arg}\"."
            )
        if arg_pair[0].strip() not in AVAILABLE_ARGS:
            raise AttributeError(
                f"Invalid argument: \"{arg_pair[0]}\". Call \"python3 import_kb.py --help\" or python3 import_kb.py -h for more information"
            )
        else:
            args[arg_pair[0].strip()] = arg_pair[1].strip()
    if len(AVAILABLE_ARGS) != len(args.keys()):
        raise AttributeError("Not all required attributes are given.")
    if args["save_existing_id_codes"].lower() == "true" or args["save_existing_id_codes"].lower() == 't':
        args["save_existing_id_codes"] = True
    elif args["save_existing_id_codes"].lower() == "false" or args["save_existing_id_codes"].lower() == 'f':
        args["save_existing_id_codes"] = False
    else:
        raise AttributeError("Available values for save_existing_id_codes are: True, T to set param to True; False, F to set param to False (case insensitive).")
    args["save_existing_id_codes"] = True if 
    import_function(**args)


if __name__ == "__main__":
    main()
