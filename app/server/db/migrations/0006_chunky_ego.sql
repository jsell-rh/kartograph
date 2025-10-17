CREATE TABLE `admin_audit_log` (
	`id` text PRIMARY KEY NOT NULL,
	`admin_user_id` text NOT NULL,
	`target_user_id` text,
	`action` text NOT NULL,
	`metadata` text,
	`ip_address` text,
	`user_agent` text,
	`timestamp` integer DEFAULT (unixepoch()) NOT NULL,
	FOREIGN KEY (`admin_user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`target_user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE INDEX `admin_audit_log_admin_user_idx` ON `admin_audit_log` (`admin_user_id`);--> statement-breakpoint
CREATE INDEX `admin_audit_log_target_user_idx` ON `admin_audit_log` (`target_user_id`);--> statement-breakpoint
CREATE INDEX `admin_audit_log_timestamp_idx` ON `admin_audit_log` (`timestamp`);--> statement-breakpoint
CREATE TABLE `message_feedback` (
	`id` text PRIMARY KEY NOT NULL,
	`message_id` text NOT NULL,
	`conversation_id` text NOT NULL,
	`user_id` text NOT NULL,
	`rating` text NOT NULL,
	`feedback_text` text,
	`user_query` text NOT NULL,
	`assistant_response` text NOT NULL,
	`created_at` integer DEFAULT (unixepoch()) NOT NULL,
	FOREIGN KEY (`message_id`) REFERENCES `messages`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`conversation_id`) REFERENCES `conversations`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `message_feedback_message_idx` ON `message_feedback` (`message_id`);--> statement-breakpoint
CREATE INDEX `message_feedback_user_idx` ON `message_feedback` (`user_id`);--> statement-breakpoint
CREATE INDEX `message_feedback_rating_idx` ON `message_feedback` (`rating`);--> statement-breakpoint
CREATE INDEX `message_feedback_timestamp_idx` ON `message_feedback` (`created_at`);--> statement-breakpoint
ALTER TABLE `users` ADD `role` text DEFAULT 'user' NOT NULL;--> statement-breakpoint
ALTER TABLE `users` ADD `is_active` integer DEFAULT true NOT NULL;--> statement-breakpoint
ALTER TABLE `users` ADD `last_login_at` integer;--> statement-breakpoint
ALTER TABLE `users` ADD `disabled_at` integer;--> statement-breakpoint
ALTER TABLE `users` ADD `disabled_by` text;
