#!/usr/bin/env python3
"""
Build a Neo4j knowledge graph for the PFA Planning System.
- Scans configs/ for YAML parameters
- Scans src/ for Python modules and functions
- Inserts nodes + edges into Neo4j
"""

import os, ast, yaml
from neo4j import GraphDatabase

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "src")
CONFIG_DIR = os.path.join(HERE, "configs")

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def run(q, p=None):
    with driver.session() as s:
        s.run(q, p or {})

def parse_python_file(path):
    with open(path, "r") as f:
        tree = ast.parse(f.read(), filename=path)
    module = os.path.splitext(os.path.basename(path))[0]
    run("MERGE (:Module {name:$n, path:$p, lang:'python'})", {"n":module, "p":path})

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            fq = f"{module}.{node.name}"
            run(
                "MERGE (f:Function {name:$n,fqname:$fq,path:$p,lineno:$l}) "
                "MERGE (m:Module {name:$m}) "
                "MERGE (f)-[:DEFINED_IN]->(m)",
                {"n":node.name,"fq":fq,"p":path,"l":node.lineno,"m":module}
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                run("MERGE (m1:Module {name:$m1}) MERGE (m2:Module {name:$m2}) "
                    "MERGE (m1)-[:IMPORTS]->(m2)",
                    {"m1":module,"m2":alias.name.split(".")[0]})
        elif isinstance(node, ast.ImportFrom) and node.module:
            run("MERGE (m1:Module {name:$m1}) MERGE (m2:Module {name:$m2}) "
                "MERGE (m1)-[:IMPORTS]->(m2)",
                {"m1":module,"m2":node.module.split(".")[0]})

def parse_yaml_file(path):
    with open(path) as f:
        data = yaml.safe_load(f)

    def recurse(prefix, obj):
        if isinstance(obj, dict):
            for k,v in obj.items():
                recurse(f"{prefix}.{k}" if prefix else k, v)
        else:
            run("MERGE (:Config {key:$k, value:$v, path:$p})",
                {"k":prefix,"v":str(obj),"p":path})
    recurse("", data)

def main():
    for root,_,files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".py"): parse_python_file(os.path.join(root,f))
    for root,_,files in os.walk(CONFIG_DIR):
        for f in files:
            if f.endswith((".yml",".yaml")): parse_yaml_file(os.path.join(root,f))

if __name__=="__main__":
    main()
