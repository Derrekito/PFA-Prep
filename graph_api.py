#!/usr/bin/env python3
"""
Enhanced Memory Palace API for LLM Agents
Provides semantic queries for understanding code relationships
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
import json

app = FastAPI(title="PFA Knowledge Graph API", version="2.0")

# Neo4j connection
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

class Query(BaseModel):
    cypher: str
    params: dict = {}

def run_query(cypher: str, params: dict = None) -> List[Dict[str, Any]]:
    """Execute Cypher query and return results"""
    try:
        with driver.session() as session:
            result = session.run(cypher, params or {})
            return [dict(record) for record in result]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")

@app.post("/graph/query")
def raw_query(q: Query):
    """Execute raw Cypher query - for advanced users"""
    return run_query(q.cypher, q.params)

# === SEMANTIC QUERY ENDPOINTS FOR AGENTS ===

@app.get("/graph/impact/{function_name}")
def impact_analysis(function_name: str):
    """🎯 What would break if I change this function?"""
    return run_query("""
        MATCH (f:Function {name: $fname})
        OPTIONAL MATCH (caller:Function)-[:CALLS]->(f)
        OPTIONAL MATCH (f)-[:CALLS]->(callee:Function)
        RETURN {
            function: f.fqname,
            path: f.path,
            line: f.lineno,
            callers: collect(DISTINCT {
                name: caller.fqname,
                path: caller.path,
                line: caller.lineno
            }),
            callees: collect(DISTINCT {
                name: callee.fqname,
                path: callee.path,
                line: callee.lineno
            })
        } as impact
    """, {"fname": function_name})

@app.get("/graph/dependencies/{module_name}")
def dependency_tree(module_name: str):
    """📦 What does this module depend on (and what depends on it)?"""
    return run_query("""
        MATCH (m:Module {name: $mname})
        OPTIONAL MATCH (m)-[:IMPORTS]->(dep:Module)
        OPTIONAL MATCH (dependent:Module)-[:IMPORTS]->(m)
        RETURN {
            module: m.name,
            path: m.path,
            dependencies: collect(DISTINCT dep.name),
            dependents: collect(DISTINCT dependent.name)
        } as dependencies
    """, {"mname": module_name})

@app.get("/graph/config-usage/{config_key}")
def config_usage(config_key: str):
    """⚙️ What code uses this config parameter?"""
    return run_query("""
        MATCH (c:Config)
        WHERE c.key CONTAINS $key
        OPTIONAL MATCH (f:Function)-[:USES_CONFIG]->(c)
        RETURN {
            config_key: c.key,
            config_value: c.value,
            config_path: c.path,
            used_by: collect(DISTINCT {
                function: f.fqname,
                path: f.path,
                line: f.lineno
            })
        } as usage
        ORDER BY c.key
    """, {"key": config_key})

@app.get("/graph/call-chain/{from_func}/{to_func}")
def call_chain(from_func: str, to_func: str):
    """🔗 How does function A reach function B?"""
    return run_query("""
        MATCH path = shortestPath(
            (start:Function {name: $from})-[:CALLS*1..10]->(end:Function {name: $to})
        )
        RETURN [node in nodes(path) | {
            function: node.fqname,
            path: node.path,
            line: node.lineno
        }] as call_chain
    """, {"from": from_func, "to": to_func})

@app.get("/graph/module-functions/{module_name}")
def module_functions(module_name: str):
    """📄 What functions are in this module?"""
    return run_query("""
        MATCH (m:Module {name: $mname})<-[:DEFINED_IN]-(f:Function)
        RETURN {
            module: m.name,
            functions: collect({
                name: f.name,
                fqname: f.fqname,
                line: f.lineno,
                type: f.type,
                args: f.args,
                docstring: f.docstring
            })
        } as module_info
    """, {"mname": module_name})

@app.get("/graph/function-details/{function_fqname}")
def function_details(function_fqname: str):
    """🔍 Deep dive into a specific function"""
    return run_query("""
        MATCH (f:Function {fqname: $fqname})
        OPTIONAL MATCH (f)-[:CALLS]->(callee:Function)
        OPTIONAL MATCH (caller:Function)-[:CALLS]->(f)
        OPTIONAL MATCH (f)-[:USES_CONFIG]->(config:Config)
        OPTIONAL MATCH (f)-[:METHOD_OF]->(class:Class)
        RETURN {
            function: {
                name: f.name,
                fqname: f.fqname,
                path: f.path,
                line: f.lineno,
                type: f.type,
                args: f.args,
                returns: f.returns,
                docstring: f.docstring
            },
            class: class.name,
            calls: collect(DISTINCT callee.fqname),
            called_by: collect(DISTINCT caller.fqname),
            uses_config: collect(DISTINCT config.key)
        } as details
    """, {"fqname": function_fqname})

@app.get("/graph/config-hierarchy/{root_key}")
def config_hierarchy(root_key: str = ""):
    """🌳 Show config structure and relationships"""
    return run_query("""
        MATCH (c:Config)
        WHERE c.key STARTS WITH $root OR $root = ""
        OPTIONAL MATCH (c)-[:HAS_CHILD]->(child:Config)
        RETURN {
            key: c.key,
            value: c.value,
            type: c.type,
            path: c.path,
            children: collect(DISTINCT child.key)
        } as config
        ORDER BY c.key
    """, {"root": root_key})

@app.get("/graph/search/functions")
def search_functions(q: str):
    """🔎 Search functions by name or docstring"""
    return run_query("""
        MATCH (f:Function)
        WHERE toLower(f.name) CONTAINS toLower($query)
           OR toLower(f.docstring) CONTAINS toLower($query)
        RETURN {
            function: f.fqname,
            name: f.name,
            path: f.path,
            line: f.lineno,
            docstring: f.docstring
        } as result
        LIMIT 20
    """, {"query": q})

@app.get("/graph/stats")
def graph_stats():
    """📊 Knowledge graph statistics"""
    stats = {}

    # Node counts
    node_stats = run_query("""
        MATCH (n)
        RETURN labels(n)[0] as type, count(n) as count
        ORDER BY count DESC
    """)
    stats["nodes"] = {stat["type"]: stat["count"] for stat in node_stats}

    # Relationship counts
    rel_stats = run_query("""
        MATCH ()-[r]->()
        RETURN type(r) as relationship, count(r) as count
        ORDER BY count DESC
    """)
    stats["relationships"] = {stat["relationship"]: stat["count"] for stat in rel_stats}

    # Most connected functions
    popular_funcs = run_query("""
        MATCH (f:Function)
        OPTIONAL MATCH (f)-[:CALLS]->(out)
        OPTIONAL MATCH (in)-[:CALLS]->(f)
        WITH f, count(DISTINCT out) as out_degree, count(DISTINCT in) as in_degree
        RETURN f.fqname as function, in_degree + out_degree as connections
        ORDER BY connections DESC
        LIMIT 10
    """)
    stats["most_connected_functions"] = popular_funcs

    return stats

@app.get("/")
def root():
    """🏠 API documentation and usage guide"""
    return {
        "title": "PFA Knowledge Graph Memory Palace",
        "description": "Semantic code analysis API for LLM agents",
        "endpoints": {
            "/graph/impact/{function}": "Impact analysis - what breaks if I change this?",
            "/graph/dependencies/{module}": "Module dependency tree",
            "/graph/config-usage/{key}": "Find code that uses config parameters",
            "/graph/call-chain/{from}/{to}": "Path from function A to function B",
            "/graph/function-details/{fqname}": "Deep dive into specific function",
            "/graph/module-functions/{module}": "All functions in a module",
            "/graph/config-hierarchy/{root}": "Config structure and nesting",
            "/graph/search/functions?q=term": "Search functions by name/docs",
            "/graph/stats": "Knowledge graph statistics",
            "/graph/query": "Raw Cypher query endpoint"
        },
        "example_queries": [
            "curl /graph/impact/calculate_progression",
            "curl /graph/dependencies/fitness_calculator",
            "curl /graph/config-usage/timeline.weeks",
            "curl /graph/search/functions?q=calendar"
        ]
    }

