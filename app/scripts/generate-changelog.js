#!/usr/bin/env node
/**
 * Generate changelog from git commits using conventional commit format
 *
 * This script extracts commits from git history and categorizes them
 * into features, improvements, and bug fixes for the What's New dialog.
 *
 * Runs at build time to auto-populate changelog.
 */

import { execSync } from "child_process";
import { writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Get commits since last version tag
 * If no tags exist, get all commits from the last 30 days
 */
function getCommitsSinceLastVersion() {
  try {
    // Get the latest tag
    const latestTag = execSync("git describe --tags --abbrev=0 2>/dev/null", {
      encoding: "utf-8",
    }).trim();

    // Get commits since that tag
    return execSync(`git log ${latestTag}..HEAD --pretty=format:"%s"`, {
      encoding: "utf-8",
    })
      .trim()
      .split("\n")
      .filter((line) => line);
  } catch (e) {
    // No tags found, get commits from last 30 days
    console.warn("No git tags found, using commits from last 30 days");
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const sinceDate = thirtyDaysAgo.toISOString().split("T")[0];

    return execSync(`git log --since="${sinceDate}" --pretty=format:"%s"`, {
      encoding: "utf-8",
    })
      .trim()
      .split("\n")
      .filter((line) => line);
  }
}

/**
 * Parse conventional commit message
 * Format: type(scope): description
 */
function parseCommit(message) {
  // Match conventional commit format: type(scope)!?: description
  const conventionalRegex = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\(.+\))?!?:\s*(.+)$/;
  const match = message.match(conventionalRegex);

  if (match) {
    const [, type, scope, description] = match;
    return {
      type,
      scope: scope ? scope.slice(1, -1) : null, // Remove parentheses
      description,
    };
  }

  // Fallback: treat as improvement if it doesn't match
  return {
    type: "other",
    scope: null,
    description: message,
  };
}

/**
 * Categorize commits into features, improvements, and bug fixes
 */
function categorizeCommits(commits) {
  const features = [];
  const improvements = [];
  const bugFixes = [];

  for (const commitMessage of commits) {
    // Skip generated commits, merge commits, and version bumps
    if (
      commitMessage.includes("🤖 Generated with") ||
      commitMessage.startsWith("Merge") ||
      commitMessage.startsWith("chore(release)")
    ) {
      continue;
    }

    const { type, description } = parseCommit(commitMessage);

    // Clean up description - remove emoji and generated markers
    let cleanDescription = description
      .replace(/🤖.*$/g, "")
      .replace(/\s+/g, " ")
      .trim();

    // Capitalize first letter
    cleanDescription =
      cleanDescription.charAt(0).toUpperCase() + cleanDescription.slice(1);

    switch (type) {
      case "feat":
        features.push(cleanDescription);
        break;
      case "fix":
        bugFixes.push(cleanDescription);
        break;
      case "refactor":
      case "perf":
      case "docs":
      case "test":
      case "ci":
        improvements.push(cleanDescription);
        break;
      // Skip chore, build, style, and other types
    }
  }

  return {
    features,
    improvements,
    bugFixes,
  };
}

/**
 * Main function
 */
function main() {
  try {
    console.log("Generating changelog from git commits...");

    const commits = getCommitsSinceLastVersion();
    console.log(`Found ${commits.length} commits`);

    const changelog = categorizeCommits(commits);
    console.log(
      `Categorized: ${changelog.features.length} features, ` +
        `${changelog.improvements.length} improvements, ` +
        `${changelog.bugFixes.length} bug fixes`,
    );

    // Write to public directory so it can be imported
    const outputPath = join(__dirname, "..", "public", "changelog.json");
    writeFileSync(outputPath, JSON.stringify(changelog, null, 2));
    console.log(`✓ Changelog written to ${outputPath}`);
  } catch (error) {
    console.error("Error generating changelog:", error);
    // Don't fail the build, just use empty changelog
    const emptyChangelog = {
      features: [],
      improvements: [],
      bugFixes: [],
    };
    const outputPath = join(__dirname, "..", "public", "changelog.json");
    writeFileSync(outputPath, JSON.stringify(emptyChangelog, null, 2));
  }
}

main();
