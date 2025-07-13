#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import requests
import json

def print_error(message):
    print(f"\033[91m{message}\033[0m")

def main():
    if len(sys.argv) != 2:
        print_error("Usage: python update_devices.py <GITHUB_TOKEN>")
        sys.exit(1)

    github_token = sys.argv[1]
    base_headers = {"Authorization": f"token {github_token}"}

    print("Fetching OTA branches...")
    response = requests.get(
        "https://api.github.com/repos/Evolution-X/OTA/branches", headers=base_headers
    )
    if response.status_code != 200:
        print_error("Error: Failed to fetch OTA branch data.")
        sys.exit(1)

    branches = [branch["name"] for branch in response.json()]
    if not branches:
        print_error("No OTA branches found.")
        sys.exit(1)

    print("\nOTA branches found:")
    for branch in branches:
        print(f"- {branch}")

    devices_data = {}

    for branch in branches:
        print(f"Fetching devices on {branch}...")
        url = f"https://api.github.com/repos/Evolution-X/OTA/contents/builds?ref={branch}"
        devices_response = requests.get(url, headers=base_headers)

        if devices_response.status_code != 200:
            print_error(f"Error: Failed to fetch devices on {branch}.")
            continue

        devices_on_branch = [
            os.path.splitext(item["name"])[0]
            for item in devices_response.json()
            if item["name"].endswith(".json")
        ]

        if not devices_on_branch:
            print(f"No devices found on {branch}.")
        else:
            for device_codename in devices_on_branch:
                if device_codename not in devices_data:
                    devices_data[device_codename] = {}

                build_url = f"https://raw.githubusercontent.com/Evolution-X/OTA/{branch}/builds/{device_codename}.json"
                build_response = requests.get(build_url)

                if build_response.status_code == 200:
                    try:
                        build_info = build_response.json()
                        initial_images = build_info.get("response", [{}])[0].get("initial_installation_images", [])
                        extra_images = build_info.get("response", [{}])[0].get("extra_images", [])

                        combined_images = list(initial_images)
                        for img in extra_images:
                            if img not in combined_images:
                                combined_images.append(img)
                        devices_data[device_codename][branch] = combined_images

                    except json.JSONDecodeError:
                        print_error(f"    Error: Could not decode JSON from {build_url}")
                        devices_data[device_codename][branch] = []
                else:
                    print_error(f"    Error: Failed to fetch build info for {device_codename} on {branch} (Status: {build_response.status_code})")
                    devices_data[device_codename][branch] = []

    devices_json_array = []
    for device_codename in sorted(devices_data.keys()):
        versions_for_device = {}
        first_populated_images = []
        for branch_name in branches:
            current_images = devices_data.get(device_codename, {}).get(branch_name, [])
            if current_images:
                first_populated_images = current_images
                break

        for branch_name in branches:
            images_for_current_branch = devices_data.get(device_codename, {}).get(branch_name, [])
            if not images_for_current_branch:
                versions_for_device[branch_name] = first_populated_images
            else:
                versions_for_device[branch_name] = images_for_current_branch

        devices_json_array.append({
            "device": device_codename,
            "versions": versions_for_device
        })

    with open("all_images.json", "w") as file:
        json.dump(devices_json_array, file, indent=4)

    print("Done.")

if __name__ == "__main__":
    main()
