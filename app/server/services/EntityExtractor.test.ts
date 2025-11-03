/**
 * Unit tests for EntityExtractor service
 */

import { describe, it, expect, beforeEach } from "vitest";
import { EntityExtractor, type Entity } from "./EntityExtractor";

describe("EntityExtractor", () => {
  let extractor: EntityExtractor;

  beforeEach(() => {
    extractor = new EntityExtractor();
  });

  describe("extract", () => {
    it("should extract a single entity from text", () => {
      const text = "The service <urn:Application:payment-service> handles payments.";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(1);
      expect(entities[0]).toEqual({
        urn: "<urn:Application:payment-service>",
        type: "Application",
        id: "payment-service",
        displayName: "payment service",
      });
    });

    it("should extract multiple entities from text", () => {
      const text =
        "The <urn:Application:api-gateway> routes to <urn:Application:auth-service> and <urn:Application:user-service>.";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(3);
      expect(entities[0]!.id).toBe("api-gateway");
      expect(entities[1]!.id).toBe("auth-service");
      expect(entities[2]!.id).toBe("user-service");
    });

    it("should handle entities with underscores in ID", () => {
      const text = "Found <urn:Namespace:kube_system> namespace.";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(1);
      expect(entities[0]).toEqual({
        urn: "<urn:Namespace:kube_system>",
        type: "Namespace",
        id: "kube_system",
        displayName: "kube system",
      });
    });

    it("should replace hyphens with spaces in display name", () => {
      const text = "<urn:Service:api-gateway-service>";

      const entities = extractor.extract(text);

      expect(entities[0]!.displayName).toBe("api gateway service");
    });

    it("should replace underscores with spaces in display name", () => {
      const text = "<urn:Route:api_v2_endpoint>";

      const entities = extractor.extract(text);

      expect(entities[0]!.displayName).toBe("api v2 endpoint");
    });

    it("should replace both hyphens and underscores in display name", () => {
      const text = "<urn:Application:my-service_v2>";

      const entities = extractor.extract(text);

      expect(entities[0]!.displayName).toBe("my service v2");
    });

    it("should deduplicate entities with same URN", () => {
      const text =
        "The <urn:Application:auth-service> is used by <urn:Application:auth-service> everywhere.";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(1);
      expect(entities[0]!.id).toBe("auth-service");
    });

    it("should handle text with no entities", () => {
      const text = "This is just plain text with no URNs.";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(0);
    });

    it("should handle empty string", () => {
      const entities = extractor.extract("");

      expect(entities).toHaveLength(0);
    });

    it("should handle different entity types", () => {
      const text = `
        Found <urn:Application:app1>,
        <urn:Service:svc1>,
        <urn:Namespace:ns1>,
        <urn:Route:route1>,
        <urn:Cluster:cluster1>
      `;

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(5);
      expect(entities.map((e) => e.type)).toEqual([
        "Application",
        "Service",
        "Namespace",
        "Route",
        "Cluster",
      ]);
    });

    it("should handle URNs with numeric IDs", () => {
      const text = "<urn:Application:app-123> and <urn:Service:v2-api>";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(2);
      expect(entities[0]!.id).toBe("app-123");
      expect(entities[1]!.id).toBe("v2-api");
    });

    it("should handle URNs at start of text", () => {
      const text = "<urn:Application:first> is the first service.";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(1);
      expect(entities[0]!.id).toBe("first");
    });

    it("should handle URNs at end of text", () => {
      const text = "The last service is <urn:Application:last>";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(1);
      expect(entities[0]!.id).toBe("last");
    });

    it("should handle multiple URNs on same line", () => {
      const text =
        "<urn:Application:app1> <urn:Application:app2> <urn:Application:app3>";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(3);
    });

    it("should handle URNs with dots in ID", () => {
      const text = "<urn:Domain:api.example.com>";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(1);
      expect(entities[0]!.id).toBe("api.example.com");
    });

    it("should handle malformed URNs gracefully (missing type)", () => {
      const text = "<urn::missing-type> and <urn:Valid:valid-id>";

      const entities = extractor.extract(text);

      // Should skip the malformed one
      expect(entities).toHaveLength(1);
      expect(entities[0]!.id).toBe("valid-id");
    });

    it("should handle malformed URNs gracefully (missing id)", () => {
      const text = "<urn:Type:> and <urn:Valid:valid-id>";

      const entities = extractor.extract(text);

      // Should skip the malformed one
      expect(entities).toHaveLength(1);
      expect(entities[0]!.id).toBe("valid-id");
    });

    it("should preserve order of first occurrence when deduplicating", () => {
      const text = `
        <urn:Application:first>
        <urn:Application:second>
        <urn:Application:first>
        <urn:Application:third>
      `;

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(3);
      expect(entities.map((e) => e.id)).toEqual(["first", "second", "third"]);
    });

    it("should handle URNs in multi-line text", () => {
      const text = `
        Line 1: <urn:Application:app1>
        Line 2: <urn:Service:svc1>
        Line 3: <urn:Namespace:ns1>
      `;

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(3);
    });

    it("should handle URNs with special characters in ID", () => {
      const text = "<urn:Application:my-app@v2.0>";

      const entities = extractor.extract(text);

      expect(entities).toHaveLength(1);
      expect(entities[0]!.id).toBe("my-app@v2.0");
    });
  });
});
