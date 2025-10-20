CREATE TABLE `changelog_entries` (
	`id` text PRIMARY KEY NOT NULL,
	`type` text NOT NULL,
	`title` text NOT NULL,
	`description` text,
	`timestamp` integer DEFAULT (unixepoch()) NOT NULL,
	`author_id` text,
	`author_name` text,
	`metadata` text,
	`pinned` integer DEFAULT false NOT NULL,
	`visibility` text DEFAULT 'public' NOT NULL,
	`created_at` integer DEFAULT (unixepoch()) NOT NULL,
	`updated_at` integer DEFAULT (unixepoch()) NOT NULL,
	FOREIGN KEY (`author_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE INDEX `changelog_entries_type_idx` ON `changelog_entries` (`type`);--> statement-breakpoint
CREATE INDEX `changelog_entries_timestamp_idx` ON `changelog_entries` (`timestamp`);--> statement-breakpoint
CREATE INDEX `changelog_entries_visibility_idx` ON `changelog_entries` (`visibility`);--> statement-breakpoint
CREATE INDEX `changelog_entries_pinned_idx` ON `changelog_entries` (`pinned`);--> statement-breakpoint
CREATE INDEX `changelog_entries_visibility_timestamp_idx` ON `changelog_entries` (`visibility`,`timestamp`);
