/**
 * Service for extracting URN entities from text.
 *
 * Entities are represented in text as URNs with the format:
 * <urn:EntityType:entity-name>
 *
 * This service parses these URNs and returns structured Entity objects.
 */

export interface Entity {
  urn: string;
  type: string;
  id: string;
  displayName: string;
}

export class EntityExtractor {
  private readonly URN_PATTERN = /<urn:([^:]+):([^>]+)>/g;

  /**
   * Extract entities from assistant message text.
   *
   * @param text - The text to extract entities from
   * @returns Array of unique entities found in the text
   */
  extract(text: string): Entity[] {
    const entities: Entity[] = [];
    const matches = text.matchAll(this.URN_PATTERN);

    for (const match of matches) {
      const [fullUrn, type, id] = match;
      if (!fullUrn || !type || !id) continue;

      entities.push({
        urn: fullUrn,
        type,
        id,
        displayName: id.replace(/-/g, " ").replace(/_/g, " "),
      });
    }

    // Deduplicate by URN
    const uniqueEntities = entities.filter(
      (entity, index, self) =>
        index === self.findIndex((e) => e.urn === entity.urn),
    );

    return uniqueEntities;
  }
}
