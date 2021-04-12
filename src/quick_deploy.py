import requests
import json

url = "https://api.github.com/repos/JF002/InfiniTime/releases"
version_blacklist = (
    "0.6.0",
    "0.6.1",
    "0.6.2",
    "0.7.0",
    "0.7.1",
    "0.8.0-develop",
    "0.8.1-develop",
    "0.8.2-develop",
    "0.9.0-develop",
    "0.9.0",
    "0.8.3",
    "0.8.2"
)


def get_quick_deploy_list():
    r = requests.get(url)
    d = json.loads(r.content)
    quick_deploy_list = []
    for item in d:
        for asset in item["assets"]:
            if (
                asset["content_type"] == "application/zip"
                and item["tag_name"] not in version_blacklist
            ):
                helper_dict = {
                    "tag_name": item["tag_name"],
                    "name": asset["name"],
                    "browser_download_url": asset["browser_download_url"],
                }
                quick_deploy_list.append(helper_dict)
    return quick_deploy_list


def get_tags(full_list):
    tags = set()
    for element in full_list:
        tags.add(element["tag_name"])
    return sorted(tags, reverse=True)

def get_assets_by_tag(tag, full_list):
    asset_list = []
    for element in full_list:
        if tag == element["tag_name"]:
            asset_list.append(element["name"])
    return asset_list

def get_download_url(name, tag, full_list):
    for element in full_list:
        if tag == element["tag_name"] and name == element["name"]:
            return element["browser_download_url"]