/**
 * GET /api/entity/:urn/relationships
 *
 * Fetches one level of relationships (edges and connected nodes) for a given entity URN.
 * Returns nodes and edges in Cytoscape.js format.
 */

import { createLogger } from "../../../lib/logger";
import {
  getReversePredicates,
  getRelationshipPredicates,
  buildOutgoingRelationshipsQuery,
  buildIncomingRelationshipsQuery,
} from "../../../lib/dgraph-schema";

const log = createLogger("entity-relationships-api");

interface CytoscapeNode {
  data: {
    id: string;
    label: string;
    type: string;
    urn: string;
    displayName: string;
    color: string;
    size: number;
    metadata?: Record<string, any>;
  };
}

interface CytoscapeEdge {
  data: {
    id: string;
    source: string;
    target: string;
    label: string;
    type: string;
  };
}

/**
 * Get color for entity type
 */
function getColorForType(type: string): string {
  const colorMap: Record<string, string> = {
    Application: "#60a5fa",
    Service: "#34d399",
    Endpoint: "#fbbf24",
    Route: "#a78bfa",
    Namespace: "#f472b6",
    User: "#818cf8",
    Role: "#2dd4bf",
    Cluster: "#fb923c",
    ExternalResource: "#22d3ee",
    Alert: "#f87171",
    SLO: "#a3e635",
    JiraProject: "#c084fc",
  };
  return colorMap[type] || "#94a3b8";
}

/**
 * Get size for entity type
 */
function getSizeForType(type: string): number {
  const sizeMap: Record<string, number> = {
    Application: 50,
    Service: 50,
    Endpoint: 40,
    Route: 40,
    Namespace: 35,
    User: 30,
    Role: 30,
  };
  return sizeMap[type] || 35;
}

/**
 * Clean up predicate name for display
 * Removes urn:predicate: prefix and converts camelCase to readable format
 */
function cleanPredicateName(predicate: string): string {
  // Remove urn:predicate: prefix and angle brackets
  let cleaned = predicate.replace(/^<?urn:predicate:/, "").replace(/>?$/, "");

  // Convert camelCase to space-separated words
  // hasNamespace -> has Namespace -> has namespace
  cleaned = cleaned.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();

  // Capitalize first letter
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export default defineEventHandler(async (event) => {
  try {
    const urn = getRouterParam(event, "urn");

    if (!urn) {
      throw createError({
        statusCode: 400,
        message: "Missing URN parameter",
      });
    }

    // Decode URN (it comes URL-encoded)
    const decodedUrn = decodeURIComponent(urn);

    log.info({ urn: decodedUrn }, "Fetching entity relationships");

    const config = useRuntimeConfig(event);
    const dgraphUrl = config.dgraphUrl;

    // Parse URN to extract type and id
    // Format: <urn:Type:id> or urn:Type:id
    const urnMatch = decodedUrn.match(/<?urn:([^:]+):([^>]+)>?/);
    if (!urnMatch) {
      throw createError({
        statusCode: 400,
        message: "Invalid URN format",
      });
    }

    const entityType = urnMatch[1]!;
    const entityId = urnMatch[2]!;

    log.info({ entityType, entityId }, "Parsed URN");

    // Query to find the entity and get its direct relationships (both outgoing AND incoming)
    //
    // We'll make TWO separate queries:
    // 1. Get outgoing relationships (what this entity points to)
    // 2. Get incoming relationships (what points to this entity) using reverse predicates

    // Get all relationship predicates from schema (for outgoing relationships)
    const relationshipPredicates = await getRelationshipPredicates();

    log.info(
      { entityType, entityId, relationshipPredicateCount: relationshipPredicates.length },
      "Building outgoing relationships query with dynamic predicates",
    );

    // Build the outgoing query dynamically based on schema
    const query = buildOutgoingRelationshipsQuery(
      entityType,
      entityId,
      relationshipPredicates,
    );

    log.info({ query }, "Sending DQL query to Dgraph");

    const response = await fetch(`${dgraphUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: query,
    });

    if (!response.ok) {
      const errorText = await response.text();
      log.error({ status: response.status, errorText }, "Dgraph query failed");
      throw new Error(
        `Dgraph query failed: ${response.status} ${response.statusText}`,
      );
    }

    const responseText = await response.text();
    log.info(
      { responseText: responseText.substring(0, 500) },
      "Raw Dgraph response",
    );

    const data = JSON.parse(responseText);

    log.info(
      {
        hasEntity: !!data.data?.entity,
        entityLength: data.data?.entity?.length || 0,
        hasIncoming: !!data.data?.incoming,
        incomingLength: data.data?.incoming?.length || 0,
        rawData: JSON.stringify(data.data).substring(0, 500),
      },
      "Dgraph response received",
    );

    if (!data.data?.entity || data.data.entity.length === 0) {
      log.warn(
        { urn: decodedUrn, entityType, entityId },
        "No entity found in Dgraph response",
      );
      return {
        nodes: [],
        edges: [],
      };
    }

    // Get the first matching entity
    const sourceEntity = data.data.entity[0];
    const sourceUid = sourceEntity.uid;

    // Extract name and type from the entity
    // Since we used expand(_all_), name and type are in the expanded predicates
    // Fallback to URN values (entityId and entityType are guaranteed by regex check above)
    let sourceName: string = entityId!;
    let sourceType: string = entityType!;

    // Look for name and type in the entity's predicates
    for (const [predicate, value] of Object.entries(sourceEntity)) {
      if (predicate === "name" && typeof value === "string") {
        sourceName = value;
      } else if (predicate === "type" && typeof value === "string") {
        sourceType = value;
      }
    }

    const nodes: CytoscapeNode[] = [];
    const edges: CytoscapeEdge[] = [];
    const seenNodes = new Set<string>();

    // Extract scalar metadata from source entity
    const scalarMetadata: Record<string, any> = {};
    const skipPredicates = new Set([
      "uid",
      "name",
      "type",
      "_source_file", // Internal metadata
      "_inferred", // Internal flag
      "_note", // Internal note
    ]);

    for (const [predicate, value] of Object.entries(sourceEntity)) {
      // Skip special fields and relationships (objects/arrays)
      if (skipPredicates.has(predicate)) continue;
      if (typeof value === "object" && value !== null) continue;

      // Store scalar values
      scalarMetadata[predicate] = value;
    }

    // Add source node (with angle brackets to match frontend format)
    const sourceNodeId = `<urn:${sourceType}:${sourceName}>`;
    nodes.push({
      data: {
        id: sourceNodeId,
        label: sourceName,
        type: sourceType,
        urn: sourceNodeId,
        displayName: sourceName.replace(/-/g, " ").replace(/_/g, " "),
        color: getColorForType(sourceType),
        size: getSizeForType(sourceType),
        // Include scalar metadata
        metadata: scalarMetadata,
      },
    });
    seenNodes.add(sourceNodeId);

    // Process all predicates (relationships)
    for (const [predicate, value] of Object.entries(sourceEntity)) {
      // Skip special fields
      if (predicate === "uid" || predicate === "name" || predicate === "type") {
        continue;
      }

      // Handle array of related entities
      if (Array.isArray(value)) {
        for (const relatedEntity of value) {
          if (typeof relatedEntity === "object" && relatedEntity.uid) {
            const targetName = relatedEntity.name || relatedEntity.uid;
            const targetType = relatedEntity.type || "Unknown";
            const targetNodeId = `<urn:${targetType}:${targetName}>`;

            // Add node if not seen
            if (!seenNodes.has(targetNodeId)) {
              nodes.push({
                data: {
                  id: targetNodeId,
                  label: targetName,
                  type: targetType,
                  urn: targetNodeId,
                  displayName: targetName.replace(/-/g, " ").replace(/_/g, " "),
                  color: getColorForType(targetType),
                  size: getSizeForType(targetType),
                },
              });
              seenNodes.add(targetNodeId);
            }

            // Add edge
            const edgeLabel = cleanPredicateName(predicate);
            const edgeId = `${sourceNodeId}-${predicate}-${targetNodeId}`;
            edges.push({
              data: {
                id: edgeId,
                source: sourceNodeId,
                target: targetNodeId,
                label: edgeLabel,
                type: predicate,
              },
            });
          }
        }
      }
      // Handle single related entity
      else if (
        typeof value === "object" &&
        value !== null &&
        (value as any).uid
      ) {
        const relatedEntity = value as any;
        const targetName = relatedEntity.name || relatedEntity.uid;
        const targetType = relatedEntity.type || "Unknown";
        const targetNodeId = `<urn:${targetType}:${targetName}>`;

        // Add node if not seen
        if (!seenNodes.has(targetNodeId)) {
          nodes.push({
            data: {
              id: targetNodeId,
              label: targetName,
              type: targetType,
              urn: targetNodeId,
              displayName: targetName.replace(/-/g, " ").replace(/_/g, " "),
              color: getColorForType(targetType),
              size: getSizeForType(targetType),
            },
          });
          seenNodes.add(targetNodeId);
        }

        // Add edge
        const edgeLabel = cleanPredicateName(predicate);
        const edgeId = `${sourceNodeId}-${predicate}-${targetNodeId}`;
        edges.push({
          data: {
            id: edgeId,
            source: sourceNodeId,
            target: targetNodeId,
            label: edgeLabel,
            type: predicate,
          },
        });
      }
    }

    // Now fetch incoming relationships (entities that point TO our source entity)
    // Use Dgraph's reverse edge traversal with ~predicate syntax
    //
    // IMPORTANT: Dynamically query all predicates that have @reverse directive in the schema
    // We query the schema to discover these predicates at runtime (with caching)
    // Querying a predicate without @reverse will cause the entire query to fail

    // Get all reverse predicates from schema (cached)
    const reversePredicates = await getReversePredicates();

    log.info(
      { sourceUid, reversePredicateCount: reversePredicates.length },
      "Building incoming relationships query with dynamic reverse predicates",
    );

    // Build the incoming query dynamically based on schema
    const incomingQuery = buildIncomingRelationshipsQuery(
      sourceUid,
      reversePredicates,
    );

    log.info(
      { sourceUid, incomingQuery },
      "Fetching incoming relationships with reverse edges",
    );

    const incomingResponse = await fetch(`${dgraphUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/dql",
      },
      body: incomingQuery,
    });

    if (incomingResponse.ok) {
      const incomingData = await incomingResponse.json();

      log.info(
        {
          hasData: !!incomingData.data,
          queryBlocks: incomingData.data ? Object.keys(incomingData.data) : [],
          rawIncomingData: JSON.stringify(incomingData).substring(0, 1000),
        },
        "Incoming relationships query complete",
      );

      // Process reverse edges from each query block
      // Each block represents entities connected via a specific reverse predicate
      if (incomingData.data) {
        let totalProcessed = 0;
        let totalSkipped = 0;

        // Iterate through each query block (dependsOn, hasEndpoint, servedBy, etc.)
        for (const [queryBlockName, queryBlockData] of Object.entries(
          incomingData.data,
        )) {
          // Each query block contains an array with one object that has the reverse predicate results
          if (!Array.isArray(queryBlockData) || queryBlockData.length === 0)
            continue;

          const blockResult = queryBlockData[0];
          if (!blockResult || typeof blockResult !== "object") continue;

          // Iterate through reverse predicates in this block
          for (const [reversePredicate, entities] of Object.entries(
            blockResult,
          )) {
            // Skip special fields
            if (reversePredicate === "uid") continue;

            // The predicate name is the reverse predicate with ~ removed
            // Example: ~dependsOn becomes dependsOn
            const predicate = reversePredicate.replace(/^~/, "");

            // Process entities (could be array or single object)
            const entityList = Array.isArray(entities) ? entities : [entities];

            log.info(
              {
                queryBlock: queryBlockName,
                reversePredicate,
                predicate,
                entityCount: entityList.length,
              },
              "Processing reverse predicate",
            );

            for (const incomingEntity of entityList) {
              if (typeof incomingEntity !== "object" || !incomingEntity.uid)
                continue;

              const incomingName = incomingEntity.name;
              const incomingType = incomingEntity.type;

              if (!incomingName || !incomingType) {
                totalSkipped++;
                log.warn(
                  {
                    entity: incomingEntity,
                    hasName: !!incomingName,
                    hasType: !!incomingType,
                  },
                  "Skipping incoming entity - missing name or type",
                );
                continue;
              }

              totalProcessed++;

              const incomingNodeId = `<urn:${incomingType}:${incomingName}>`;

              // Add incoming node if not seen
              if (!seenNodes.has(incomingNodeId)) {
                nodes.push({
                  data: {
                    id: incomingNodeId,
                    label: incomingName,
                    type: incomingType,
                    urn: incomingNodeId,
                    displayName: incomingName
                      .replace(/-/g, " ")
                      .replace(/_/g, " "),
                    color: getColorForType(incomingType),
                    size: getSizeForType(incomingType),
                  },
                });
                seenNodes.add(incomingNodeId);
              }

              // Add reverse edge (from incoming entity TO our source)
              const edgeLabel = cleanPredicateName(predicate);
              const edgeId = `${incomingNodeId}-${predicate}-${sourceNodeId}`;

              // Only add if edge doesn't already exist (avoid duplicates)
              const edgeExists = edges.some((e) => e.data.id === edgeId);
              if (!edgeExists) {
                edges.push({
                  data: {
                    id: edgeId,
                    source: incomingNodeId,
                    target: sourceNodeId,
                    label: edgeLabel,
                    type: predicate,
                  },
                });
              }
            }
          }
        }

        log.info(
          {
            totalProcessed,
            totalSkipped,
            nodesAdded: nodes.length,
            edgesAdded: edges.length,
          },
          "Finished processing incoming relationships",
        );
      }
    } else {
      const errorText = await incomingResponse.text();
      log.warn(
        { status: incomingResponse.status, errorText },
        "Failed to fetch incoming relationships",
      );
    }

    log.info(
      { nodeCount: nodes.length, edgeCount: edges.length },
      "Relationships fetched (including incoming)",
    );

    return {
      nodes,
      edges,
    };
  } catch (error) {
    log.error(
      {
        error: error instanceof Error ? error.message : String(error),
      },
      "Failed to fetch entity relationships",
    );

    throw createError({
      statusCode: 500,
      message: "Failed to fetch entity relationships",
    });
  }
});
