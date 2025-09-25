#!/usr/bin/env python3
from fastapi import FastAPI
from pydantic import BaseModel
from neo4j import GraphDatabase

app = FastAPI()

# Neo4j connection (adjust password if you changed it in docker run)
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

class Query(BaseModel):
    cypher: str
    params: dict = {}

@app.post("/graph/query")
def run_query(q: Query):
    with driver.session() as session:
        result = session.run(q.cypher, q.params)
        return [dict(r) for r in result]

