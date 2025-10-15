ALTER TABLE `verifications` ADD `updated_at` integer DEFAULT (unixepoch()) NOT NULL;
