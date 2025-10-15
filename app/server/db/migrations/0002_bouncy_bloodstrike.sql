ALTER TABLE `accounts` ADD `password` text;--> statement-breakpoint
ALTER TABLE `conversations` ADD `last_message_at` integer;--> statement-breakpoint
ALTER TABLE `conversations` ADD `message_count` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `conversations` ADD `is_archived` integer DEFAULT false NOT NULL;--> statement-breakpoint
ALTER TABLE `users` DROP COLUMN `password`;
