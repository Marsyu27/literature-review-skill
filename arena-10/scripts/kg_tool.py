#!/usr/bin/env python3
"""Execute and validate the small literature knowledge-graph query DSL.

Standard library only.  The JSON main graph is the sole source of query edges
and evidence; no database or model-generated query evidence is involved.
"""

import argparse
import copy
import json
import os
import sys
import tempfile
from collections import deque


OPERATIONS = {"filter_edges", "neighbors", "path"}
EVIDENCE_FIELDS = ("source_id", "paragraph_id", "quote", "strength")


class ToolError(Exception):
    """A user-facing input, execution, or output error."""


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ToolError("cannot read JSON %s: %s" % (path, exc))


def atomic_write_json(path, value):
    """Write JSON by fsync + os.replace in the destination directory."""
    target = os.path.abspath(path)
    parent = os.path.dirname(target)
    try:
        os.makedirs(parent, exist_ok=True)
        old_mode = os.stat(target).st_mode & 0o777 if os.path.exists(target) else None
        fd, temporary = tempfile.mkstemp(prefix=".kg_tool-", suffix=".json", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if old_mode is not None:
                os.chmod(temporary, old_mode)
            os.replace(temporary, target)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
    except OSError as exc:
        raise ToolError("cannot atomically write JSON %s: %s" % (target, exc))


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def check_evidence_item(item, location, registered_sources, errors):
    if not isinstance(item, dict):
        errors.append(location + ": evidence item must be an object")
        return set()
    for field in EVIDENCE_FIELDS:
        if not nonempty_string(item.get(field)):
            errors.append("%s: evidence.%s must be a non-empty string" % (location, field))
    source_id = item.get("source_id")
    if nonempty_string(source_id) and source_id not in registered_sources:
        errors.append("%s: evidence source_id %r is not registered in sources" % (location, source_id))
    return {source_id} if nonempty_string(source_id) else set()


def iter_edge_id_references(value, location):
    """Yield every explicit edge_id anywhere inside a query record."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "edge_id":
                yield location + "." + key, child
            else:
                for found in iter_edge_id_references(child, location + "." + key):
                    yield found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            for found in iter_edge_id_references(child, "%s[%d]" % (location, index)):
                yield found


def graph_structure_errors(graph):
    """Validate graph invariants without parsing or trusting external JATS data."""
    errors = []
    if not isinstance(graph, dict):
        return ["graph root must be an object"], {}, {}, set()

    sources = graph.get("sources")
    registered_sources = set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
        sources = sources if isinstance(sources, list) else []
    for index, source in enumerate(sources):
        location = "sources[%d]" % index
        if not isinstance(source, dict):
            errors.append(location + ": must be an object")
            continue
        source_id = source.get("source_id")
        if not nonempty_string(source_id):
            errors.append(location + ": source_id must be a non-empty string")
        elif source_id in registered_sources:
            errors.append(location + ": duplicate source_id %r" % source_id)
        else:
            registered_sources.add(source_id)

    raw_nodes = graph.get("nodes")
    if not isinstance(raw_nodes, list):
        errors.append("nodes must be an array")
        raw_nodes = []
    nodes = {}
    node_sources = {}
    for index, node in enumerate(raw_nodes):
        location = "nodes[%d]" % index
        if not isinstance(node, dict):
            errors.append(location + ": must be an object")
            continue
        entity_id = node.get("entity_id")
        if not nonempty_string(entity_id):
            errors.append(location + ": entity_id must be a non-empty string")
            continue
        if entity_id in nodes:
            errors.append(location + ": duplicate entity_id %r" % entity_id)
            continue
        nodes[entity_id] = node
        evidence = node.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(location + ": node evidence must be one object, not an array")
            evidence_sources = set()
        else:
            evidence_sources = check_evidence_item(evidence, location, registered_sources, errors)
        own_source = node.get("source_id")
        if own_source is not None and not nonempty_string(own_source):
            errors.append(location + ": source_id, when present, must be a non-empty string")
            own_source = None
        if nonempty_string(own_source) and own_source not in registered_sources:
            errors.append("%s: source_id %r is not registered in sources" % (location, own_source))
        evidence_source = evidence.get("source_id") if isinstance(evidence, dict) else None
        if nonempty_string(own_source) and nonempty_string(evidence_source) and own_source != evidence_source:
            errors.append(location + ": node source_id differs from evidence.source_id")
        resolved_source = own_source if nonempty_string(own_source) else evidence_source
        if not nonempty_string(resolved_source):
            errors.append(location + ": cannot determine the node's paper source_id")
        else:
            node_sources[entity_id] = resolved_source
        if not nonempty_string(node.get("label")):
            errors.append(location + ": label must be a non-empty string")

    raw_edges = graph.get("edges")
    if not isinstance(raw_edges, list):
        errors.append("edges must be an array")
        raw_edges = []
    edges = {}
    for index, edge in enumerate(raw_edges):
        location = "edges[%d]" % index
        if not isinstance(edge, dict):
            errors.append(location + ": must be an object")
            continue
        edge_id = edge.get("edge_id")
        if not nonempty_string(edge_id):
            errors.append(location + ": edge_id must be a non-empty string")
            continue
        if edge_id in edges:
            errors.append(location + ": duplicate edge_id %r" % edge_id)
            continue
        edges[edge_id] = edge
        source = edge.get("source")
        target = edge.get("target")
        if not nonempty_string(source) or source not in nodes:
            errors.append("%s: source endpoint %r does not exist in nodes" % (location, source))
        if not nonempty_string(target) or target not in nodes:
            errors.append("%s: target endpoint %r does not exist in nodes" % (location, target))
        if not nonempty_string(edge.get("predicate")):
            errors.append(location + ": predicate must be a non-empty string")
        evidence = edge.get("evidence")
        evidence_sources = set()
        if not isinstance(evidence, list):
            errors.append(location + ": edge evidence must be an array")
        elif not evidence:
            errors.append(location + ": edge evidence array must not be empty")
        else:
            for evidence_index, item in enumerate(evidence):
                evidence_sources.update(check_evidence_item(
                    item, "%s.evidence[%d]" % (location, evidence_index), registered_sources, errors
                ))
        own_source = edge.get("source_id")
        if own_source is not None:
            if not nonempty_string(own_source) or own_source not in registered_sources:
                errors.append(location + ": top-level source_id is not a registered paper source")
            elif own_source not in evidence_sources:
                errors.append(location + ": top-level source_id is absent from edge evidence")
        if source in node_sources and target in node_sources:
            required = {node_sources[source], node_sources[target]}
            if len(required) > 1:
                if len(evidence_sources) < 2 or not required.issubset(evidence_sources):
                    errors.append(
                        "%s: cross-paper edge %s requires evidence from both endpoint sources %s"
                        % (location, edge_id, sorted(required))
                    )

    queries = graph.get("queries")
    if not isinstance(queries, list):
        errors.append("queries must be an array")
        queries = []
    for index, query in enumerate(queries):
        location = "queries[%d]" % index
        if not isinstance(query, dict):
            errors.append(location + ": must be an object")
            continue
        if "query_spec" not in query:
            errors.append(location + ": missing query_spec")
        for reference_location, edge_id in iter_edge_id_references(query, location):
            if not nonempty_string(edge_id) or edge_id not in edges:
                errors.append("%s: referenced edge_id %r is absent from main graph edges" % (
                    reference_location, edge_id
                ))
    return errors, nodes, edges, registered_sources


def status_errors(graph):
    if not isinstance(graph, dict):
        return []
    errors = []
    queries = graph.get("queries")
    count = len(queries) if isinstance(queries, list) else 0
    status = graph.get("status")
    reason = graph.get("status_reason")
    if status == "success" and count < 3:
        errors.append("status success requires at least 3 executable queries; found %d" % count)
    if status == "partial" and count < 3:
        if not nonempty_string(reason):
            errors.append("partial with %d queries requires status_reason with the true count and unfinished cause" % count)
        else:
            if str(count) not in reason:
                errors.append("partial status_reason must state the real executable query count %d" % count)
            if len(reason.strip()) < 8:
                errors.append("partial status_reason must explain why the remaining queries are unfinished")
    return errors


def require_spec_keys(spec, allowed):
    unknown = sorted(set(spec) - allowed)
    if unknown:
        raise ToolError("query_spec has unknown field(s): %s" % ", ".join(unknown))


def optional_string(spec, field):
    value = spec.get(field)
    if value is not None and not nonempty_string(value):
        raise ToolError("query_spec.%s must be a non-empty string when present" % field)
    return value


def edge_matches_filters(edge, spec, nodes, allow_label=True, allow_edge_id=True):
    allowed = {"op", "predicate", "source_id"}
    if allow_label:
        allowed.add("label_contains")
    if allow_edge_id:
        allowed.add("edge_id")
    predicate = optional_string(spec, "predicate")
    source_id = optional_string(spec, "source_id")
    if predicate is not None and edge.get("predicate") != predicate:
        return False
    if source_id is not None:
        evidence_sources = {
            item.get("source_id") for item in edge.get("evidence", []) if isinstance(item, dict)
        }
        if source_id not in evidence_sources:
            return False
    if allow_label:
        needle = optional_string(spec, "label_contains")
        if needle is not None:
            needle = needle.casefold()
            source_label = str(nodes.get(edge.get("source"), {}).get("label", "")).casefold()
            target_label = str(nodes.get(edge.get("target"), {}).get("label", "")).casefold()
            if needle not in source_label and needle not in target_label:
                return False
    if allow_edge_id:
        edge_id = optional_string(spec, "edge_id")
        if edge_id is not None and edge.get("edge_id") != edge_id:
            return False
    return True


def execute_query(graph, nodes, edges, spec):
    if not isinstance(spec, dict):
        raise ToolError("query_spec must be an object")
    operation = spec.get("op")
    if operation not in OPERATIONS:
        raise ToolError("query_spec.op must be one of filter_edges, neighbors, path")

    matched = []
    paths = None
    if operation == "filter_edges":
        require_spec_keys(spec, {"op", "predicate", "source_id", "label_contains", "edge_id"})
        # Validate filter types even when an earlier filter rejects every edge.
        for field in ("predicate", "source_id", "label_contains", "edge_id"):
            optional_string(spec, field)
        for edge_id in sorted(edges):
            edge = edges[edge_id]
            if edge_matches_filters(edge, spec, nodes):
                matched.append(edge_id)

    elif operation == "neighbors":
        require_spec_keys(spec, {"op", "entity_id", "seed", "direction", "predicate", "source_id"})
        for field in ("entity_id", "seed", "direction", "predicate", "source_id"):
            optional_string(spec, field)
        if ("entity_id" in spec) == ("seed" in spec):
            raise ToolError("neighbors requires exactly one of entity_id or seed")
        seed = spec.get("entity_id", spec.get("seed"))
        if seed not in nodes:
            raise ToolError("neighbors seed %r does not exist in main graph nodes" % seed)
        direction = spec.get("direction", "any")
        if direction not in {"out", "in", "any"}:
            raise ToolError("neighbors.direction must be out, in, or any")
        for edge_id in sorted(edges):
            edge = edges[edge_id]
            incident = (
                direction == "any" and seed in {edge.get("source"), edge.get("target")}
            ) or (
                direction == "out" and edge.get("source") == seed
            ) or (
                direction == "in" and edge.get("target") == seed
            )
            if incident and edge_matches_filters(edge, spec, nodes, allow_label=False, allow_edge_id=False):
                matched.append(edge_id)

    else:  # path
        require_spec_keys(spec, {"op", "start", "end", "max_depth"})
        start = optional_string(spec, "start")
        end = optional_string(spec, "end")
        if start is None or end is None:
            raise ToolError("path requires non-empty start and end entity IDs")
        if start not in nodes or end not in nodes:
            raise ToolError("path start/end must exist in main graph nodes")
        max_depth = spec.get("max_depth")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 1 <= max_depth <= 3:
            raise ToolError("path.max_depth must be an integer from 1 through 3")

        outgoing = {entity_id: [] for entity_id in nodes}
        for edge_id in sorted(edges):
            edge = edges[edge_id]
            if edge.get("source") in outgoing:
                outgoing[edge["source"]].append(edge)
        for adjacency in outgoing.values():
            adjacency.sort(key=lambda item: (item["edge_id"], item.get("target", "")))

        found = []
        if start == end:
            found = [([start], [])]
        else:
            queue = deque([(start, [start], [])])
            shortest_depth = None
            while queue:
                current, node_path, edge_path = queue.popleft()
                if shortest_depth is not None and len(edge_path) >= shortest_depth:
                    continue
                if len(edge_path) >= max_depth:
                    continue
                for edge in outgoing.get(current, []):
                    target = edge["target"]
                    if target in node_path:  # every shortest path can be simple
                        continue
                    next_nodes = node_path + [target]
                    next_edges = edge_path + [edge["edge_id"]]
                    if target == end:
                        shortest_depth = len(next_edges)
                        found.append((next_nodes, next_edges))
                    elif shortest_depth is None:
                        queue.append((target, next_nodes, next_edges))
        found.sort(key=lambda item: (len(item[1]), tuple(item[1]), tuple(item[0])))
        paths = [{"node_ids": node_path, "edge_ids": edge_path} for node_path, edge_path in found]
        matched = sorted({edge_id for _, edge_path in found for edge_id in edge_path})

    matched = sorted(set(matched))
    result_subgraph = []
    evidence = []
    seen_evidence = set()
    for edge_id in matched:
        edge = edges[edge_id]
        result_subgraph.append({
            "edge_id": edge_id,
            "source": edge["source"],
            "predicate": edge["predicate"],
            "target": edge["target"],
        })
        for item in edge["evidence"]:
            fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if fingerprint not in seen_evidence:
                seen_evidence.add(fingerprint)
                evidence.append(copy.deepcopy(item))
    execution = {
        "operation": operation,
        "matched_edge_ids": matched,
        "result_count": len(matched),
    }
    if paths is not None:
        execution["paths"] = paths
    return {
        "result_subgraph": result_subgraph,
        "evidence": evidence,
        "execution": execution,
    }


def execute_all(graph):
    errors, nodes, edges, _ = graph_structure_errors(graph)
    errors.extend(status_errors(graph))
    if errors:
        raise ToolError("; ".join(errors))
    updated = copy.deepcopy(graph)
    for index, query in enumerate(updated["queries"]):
        try:
            computed = execute_query(updated, nodes, edges, query["query_spec"])
        except (ToolError, KeyError, TypeError) as exc:
            raise ToolError("queries[%d]: %s" % (index, exc))
        query.update(computed)
    return updated


def validate_graph(graph):
    errors, nodes, edges, _ = graph_structure_errors(graph)
    errors.extend(status_errors(graph))
    query_reports = []
    if not errors:
        for index, query in enumerate(graph["queries"]):
            report = {"index": index, "valid": True, "errors": []}
            try:
                expected = execute_query(graph, nodes, edges, query["query_spec"])
                for field in ("result_subgraph", "evidence", "execution"):
                    if query.get(field) != expected[field]:
                        report["errors"].append(
                            "%s differs from deterministic recomputation from query_spec and main graph" % field
                        )
            except (ToolError, KeyError, TypeError) as exc:
                report["errors"].append(str(exc))
            report["valid"] = not report["errors"]
            query_reports.append(report)
            errors.extend("queries[%d]: %s" % (index, message) for message in report["errors"])
    return {
        "valid": not errors,
        "status": graph.get("status") if isinstance(graph, dict) else None,
        "query_count": len(graph.get("queries", [])) if isinstance(graph, dict) and isinstance(graph.get("queries"), list) else 0,
        "errors": errors,
        "queries": query_reports,
    }


def command_query(args):
    graph = load_json(args.graph)
    if args.update and args.out:
        raise ToolError("--update and --out are mutually exclusive")
    updated = execute_all(graph)
    destination = args.graph if args.update else (args.out or "executed.json")
    atomic_write_json(destination, updated)
    print("executed %d queries; wrote %s" % (len(updated["queries"]), destination))
    return 0


def command_validate(args):
    try:
        graph = load_json(args.graph)
        report = validate_graph(graph)
    except ToolError as exc:
        report = {"valid": False, "query_count": 0, "errors": [str(exc)], "queries": []}
    atomic_write_json(args.report, report)
    if report["valid"]:
        print("valid: %d queries recomputed and matched" % report["query_count"])
        return 0
    print("invalid: %d error(s); report %s" % (len(report["errors"]), args.report), file=sys.stderr)
    return 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    query_parser = subparsers.add_parser("query", help="recompute every query from the main graph")
    query_parser.add_argument("--graph", required=True, help="input result.json")
    query_parser.add_argument("--out", help="output JSON (default: executed.json)")
    query_parser.add_argument("--update", action="store_true", help="atomically replace --graph")
    query_parser.set_defaults(function=command_query)
    validate_parser = subparsers.add_parser("validate", help="compare stored query outputs with recomputation")
    validate_parser.add_argument("--graph", required=True, help="executed result.json")
    validate_parser.add_argument("--report", required=True, help="validation report JSON")
    validate_parser.set_defaults(function=command_validate)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.function(args)
    except ToolError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
