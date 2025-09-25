#!/usr/bin/env python3
"""
Build a Neo4j knowledge graph for the PFA Planning System.
Enhanced "Memory Palace" for LLM agents:
- Rich semantic relationships between code elements
- Function call graphs and dependency tracking
- Config usage analysis
- Class hierarchy and inheritance
- Test coverage mapping
"""

import os, ast, yaml, hashlib
from pathlib import Path
from neo4j import GraphDatabase
from typing import Dict, Set, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "src")
CONFIG_DIR = os.path.join(HERE, "configs")
TEST_DIR = os.path.join(HERE, "tests")  # For future test mapping

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def run(q, p=None):
    with driver.session() as s:
        return s.run(q, p or {})

def clear_graph():
    """Clear existing graph for fresh extraction"""
    run("MATCH (n) DETACH DELETE n")
    print("🧹 Cleared existing graph")

class CodeAnalyzer(ast.NodeVisitor):
    """Enhanced AST analyzer for building rich knowledge graphs"""

    def __init__(self, module_name: str, file_path: str):
        self.module_name = module_name
        self.file_path = file_path
        self.current_class = None
        self.current_function = None
        self.function_calls = []
        self.config_accesses = []

    def visit_ClassDef(self, node):
        """Track class definitions and inheritance"""
        class_fq = f"{self.module_name}.{node.name}"

        # Create class node
        run("""
            MERGE (c:Class {name:$name, fqname:$fqname, path:$path, lineno:$lineno})
            MERGE (m:Module {name:$module})
            MERGE (c)-[:DEFINED_IN]->(m)
        """, {
            "name": node.name,
            "fqname": class_fq,
            "path": self.file_path,
            "lineno": node.lineno,
            "module": self.module_name
        })

        # Track inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                run("""
                    MERGE (c1:Class {fqname:$child})
                    MERGE (c2:Class {name:$parent})
                    MERGE (c1)-[:INHERITS]->(c2)
                """, {"child": class_fq, "parent": base.id})

        old_class = self.current_class
        self.current_class = class_fq
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Track function definitions with rich metadata"""
        if self.current_class:
            func_fq = f"{self.current_class}.{node.name}"
            func_type = "method"
        else:
            func_fq = f"{self.module_name}.{node.name}"
            func_type = "function"

        # Extract function signature
        args = [arg.arg for arg in node.args.args]
        returns = ast.unparse(node.returns) if node.returns else None

        # Create function node with rich metadata
        run("""
            MERGE (f:Function {
                name:$name,
                fqname:$fqname,
                path:$path,
                lineno:$lineno,
                type:$type,
                args:$args,
                returns:$returns,
                docstring:$docstring
            })
            MERGE (m:Module {name:$module})
            MERGE (f)-[:DEFINED_IN]->(m)
        """, {
            "name": node.name,
            "fqname": func_fq,
            "path": self.file_path,
            "lineno": node.lineno,
            "type": func_type,
            "args": args,
            "returns": returns,
            "docstring": ast.get_docstring(node),
            "module": self.module_name
        })

        # Link methods to classes
        if self.current_class:
            run("""
                MERGE (f:Function {fqname:$func})
                MERGE (c:Class {fqname:$class})
                MERGE (f)-[:METHOD_OF]->(c)
            """, {"func": func_fq, "class": self.current_class})

        old_function = self.current_function
        self.current_function = func_fq
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node):
        """Track function calls - THE MONEY SHOT"""
        if not self.current_function:
            return

        callee = None

        # Simple function call: foo()
        if isinstance(node.func, ast.Name):
            callee = node.func.id

        # Method call: obj.method()
        elif isinstance(node.func, ast.Attribute):
            callee = node.func.attr

        # Module function call: module.function()
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            callee = f"{node.func.value.id}.{node.func.attr}"

        if callee:
            self.function_calls.append((self.current_function, callee, node.lineno))

        self.generic_visit(node)

    def visit_Subscript(self, node):
        """Track config access patterns like config['key'] or config.get('key')"""
        if isinstance(node.value, ast.Name) and 'config' in node.value.id.lower():
            if isinstance(node.slice, ast.Constant):
                config_key = node.slice.value
                self.config_accesses.append((self.current_function, config_key, node.lineno))
        self.generic_visit(node)

def parse_python_file(path):
    """Parse Python file with enhanced analysis"""
    try:
        with open(path, "r") as f:
            content = f.read()
            tree = ast.parse(content, filename=path)
    except Exception as e:
        print(f"⚠️  Failed to parse {path}: {e}")
        return

    module_name = os.path.splitext(os.path.basename(path))[0]
    file_hash = hashlib.md5(content.encode()).hexdigest()

    # Create module node with metadata
    run("""
        MERGE (m:Module {
            name:$name,
            path:$path,
            lang:'python',
            file_hash:$hash,
            last_modified:$modified
        })
    """, {
        "name": module_name,
        "path": path,
        "hash": file_hash,
        "modified": os.path.getmtime(path)
    })

    # Analyze the AST
    analyzer = CodeAnalyzer(module_name, path)
    analyzer.visit(tree)

    # Create function call relationships
    for caller, callee, lineno in analyzer.function_calls:
        run("""
            MERGE (f1:Function {fqname:$caller})
            MERGE (f2:Function {name:$callee})
            MERGE (f1)-[:CALLS {lineno:$lineno}]->(f2)
        """, {"caller": caller, "callee": callee, "lineno": lineno})

    # Create config usage relationships
    for function, config_key, lineno in analyzer.config_accesses:
        run("""
            MERGE (f:Function {fqname:$function})
            MERGE (c:Config {key:$key})
            MERGE (f)-[:USES_CONFIG {lineno:$lineno}]->(c)
        """, {"function": function, "key": config_key, "lineno": lineno})

    # Handle imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_module = alias.name.split(".")[0]
                run("""
                    MERGE (m1:Module {name:$importer})
                    MERGE (m2:Module {name:$imported})
                    MERGE (m1)-[:IMPORTS]->(m2)
                """, {"importer": module_name, "imported": imported_module})

        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_module = node.module.split(".")[0]
            run("""
                MERGE (m1:Module {name:$importer})
                MERGE (m2:Module {name:$imported})
                MERGE (m1)-[:IMPORTS]->(m2)
            """, {"importer": module_name, "imported": imported_module})

def parse_yaml_file(path):
    """Parse YAML config with hierarchical structure"""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️  Failed to parse {path}: {e}")
        return

    config_name = os.path.splitext(os.path.basename(path))[0]

    # Create config file node
    run("""
        MERGE (cf:ConfigFile {
            name:$name,
            path:$path,
            type:$type
        })
    """, {
        "name": config_name,
        "path": path,
        "type": "yaml"
    })

    def recurse(prefix, obj, parent_key=None):
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_key = f"{prefix}.{k}" if prefix else k

                # Create config node
                run("""
                    MERGE (c:Config {
                        key:$key,
                        path:$path,
                        parent:$parent,
                        type:$type
                    })
                    MERGE (cf:ConfigFile {name:$file})
                    MERGE (c)-[:DEFINED_IN]->(cf)
                """, {
                    "key": current_key,
                    "path": path,
                    "parent": parent_key,
                    "type": "dict" if isinstance(v, dict) else "value",
                    "file": config_name
                })

                # Create parent-child relationships
                if parent_key:
                    run("""
                        MERGE (parent:Config {key:$parent})
                        MERGE (child:Config {key:$child})
                        MERGE (parent)-[:HAS_CHILD]->(child)
                    """, {"parent": parent_key, "child": current_key})

                recurse(current_key, v, current_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                item_key = f"{prefix}[{i}]"
                recurse(item_key, item, prefix)
        else:
            # Leaf value - update the config node
            run("""
                MERGE (c:Config {key:$key})
                SET c.value = $value, c.type = 'value'
            """, {"key": prefix, "value": str(obj)})

    recurse("", data)

def should_update_file(file_path: str) -> bool:
    """Check if file needs updating based on modification time and hash"""
    try:
        current_mtime = os.path.getmtime(file_path)
        with open(file_path, 'r') as f:
            current_hash = hashlib.md5(f.read().encode()).hexdigest()

        # Check if we have this file in the graph
        result = run("""
            MATCH (m:Module {path: $path})
            RETURN m.last_modified as stored_mtime, m.file_hash as stored_hash
        """, {"path": file_path})

        records = list(result)
        if not records:
            return True  # File not in graph, needs to be added

        stored = records[0]
        return (current_mtime != stored['stored_mtime'] or
                current_hash != stored['stored_hash'])

    except Exception:
        return True  # On error, assume needs update

def remove_file_from_graph(file_path: str):
    """Remove all nodes related to a specific file"""
    run("""
        MATCH (m:Module {path: $path})
        OPTIONAL MATCH (m)<-[:DEFINED_IN]-(f:Function)
        OPTIONAL MATCH (m)<-[:DEFINED_IN]-(c:Class)
        DETACH DELETE m, f, c
    """, {"path": file_path})

def main(incremental: bool = True):
    """Build the complete knowledge graph"""
    print("🏗️  Building Knowledge Graph Memory Palace...")

    if not incremental:
        print("🔄 Full rebuild requested - clearing existing graph")
        clear_graph()
    else:
        print("⚡ Incremental update mode")

    # Parse Python source files
    python_files = []
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".py"):
                python_files.append(os.path.join(root, f))

    # Add main script
    main_script = os.path.join(HERE, "generate_pfa_plan.py")
    if os.path.exists(main_script):
        python_files.append(main_script)

    print(f"📁 Found {len(python_files)} Python files")
    updated_count = 0
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, HERE)
        if incremental and not should_update_file(file_path):
            print(f"   ⏭️  Skipping {rel_path} (unchanged)")
            continue

        print(f"   📄 Parsing {rel_path}")
        if incremental:
            remove_file_from_graph(file_path)
        parse_python_file(file_path)
        updated_count += 1

    # Parse config files
    config_files = []
    for root, _, files in os.walk(CONFIG_DIR):
        for f in files:
            if f.endswith((".yml", ".yaml")):
                config_files.append(os.path.join(root, f))

    print(f"⚙️  Found {len(config_files)} config files")
    for file_path in config_files:
        rel_path = os.path.relpath(file_path, HERE)
        if incremental and not should_update_file(file_path):
            print(f"   ⏭️  Skipping {rel_path} (unchanged)")
            continue

        print(f"   📄 Parsing {rel_path}")
        if incremental:
            # For config files, we need different cleanup
            run("MATCH (c:Config {path: $path}) DETACH DELETE c", {"path": file_path})
            run("MATCH (cf:ConfigFile {path: $path}) DETACH DELETE cf", {"path": file_path})
        parse_yaml_file(file_path)
        updated_count += 1

    # Print summary
    with driver.session() as session:
        stats = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as type, count(n) as count
            ORDER BY count DESC
        """).data()

        if incremental:
            print(f"\n⚡ Updated {updated_count} files")
        else:
            print(f"\n📊 Processed {len(python_files) + len(config_files)} files total")

        print("\n📊 Knowledge Graph Summary:")
        for stat in stats:
            print(f"   {stat['type']}: {stat['count']}")

    print("\n✅ Memory Palace construction complete!")
    print("🔗 Access via: curl -X POST http://127.0.0.1:8000/graph/query")
    print("📖 Documentation: curl http://127.0.0.1:8000/")

if __name__ == "__main__":
    import sys
    full_rebuild = "--full" in sys.argv or "--rebuild" in sys.argv
    main(incremental=not full_rebuild)
