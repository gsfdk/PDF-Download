#!/usr/bin/env python3
"""
Gmail PDF Auto-Downloader
Searches Gmail for emails matching configured subject keywords,
downloads PDF attachments, classifies them by filename pattern,
and uploads to the corresponding Google Drive subfolder.
"""

import json
import logging
import os
import sys

import classifier
import drive_client
import gmail_client
import tracker

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "run.log")),
    ],
)
log = logging.getLogger(__name__)


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        log.error("config.json not found. Please create it before running.")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def setup_drive_folders(drive_service, config: dict) -> dict:
    """
    Creates 5 subfolders in Google Drive if their IDs are not yet set,
    then saves the IDs back to config.json.
    """
    parent_id = config["drive_parent_folder_id"]
    if parent_id.startswith("<"):
        log.error(
            "Please set 'drive_parent_folder_id' in config.json to your Google Drive folder ID."
        )
        sys.exit(1)

    changed = False
    for rule in config["classifications"]:
        if not rule["drive_folder_id"]:
            log.info(f"Creating Drive subfolder: {rule['name']}")
            folder_id = drive_client.create_subfolder(drive_service, rule["name"], parent_id)
            rule["drive_folder_id"] = folder_id
            log.info(f"  Created → {folder_id}")
            changed = True

    if changed:
        save_config(config)
        log.info("Saved subfolder IDs to config.json")

    return config


def run():
    config = load_config()
    keywords = config["gmail_subject_keywords"]
    classifications = config["classifications"]

    log.info("Authenticating with Google APIs...")
    creds = gmail_client.authenticate()
    gmail_service = gmail_client.build_gmail_service(creds)
    drive_service = drive_client.build_drive_service(creds)

    # Ensure Drive subfolders exist
    config = setup_drive_folders(drive_service, config)
    classifications = config["classifications"]

    log.info(f"Searching Gmail for emails with keywords: {keywords}")
    messages = gmail_client.search_emails(gmail_service, keywords)
    log.info(f"Found {len(messages)} matching email(s)")

    total_downloaded = 0
    total_skipped = 0

    for msg in messages:
        message_id = msg["id"]
        attachments = gmail_client.get_pdf_attachments(gmail_service, message_id)

        for att in attachments:
            filename = att["filename"]
            attachment_id = att["attachment_id"]

            if tracker.is_downloaded(message_id, attachment_id):
                log.info(f"  SKIP (already downloaded): {filename}")
                total_skipped += 1
                continue

            rule = classifier.classify(filename, classifications)
            folder_id = rule["drive_folder_id"]
            folder_name = rule["name"]

            log.info(f"  Uploading '{filename}' → '{folder_name}' ...")
            drive_client.upload_pdf(drive_service, filename, att["data"], folder_id)
            tracker.mark_downloaded(message_id, attachment_id)
            log.info(f"  Done.")
            total_downloaded += 1

    log.info(
        f"Finished. Downloaded: {total_downloaded}, Skipped (duplicates): {total_skipped}"
    )


if __name__ == "__main__":
    run()
