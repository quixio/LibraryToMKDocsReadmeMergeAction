import os
import traceback
import shutil
from pathlib import Path
import json
from typing import List

connectors_md_path = ''
logs = []

# library_repo_path = "library"
# path_to_docs = "docs"
# nav_replacement_placeholder = "#ConnectorsGetInsertedHere"
# connectors_tile_replacement_placeholder = "#connectors_tile_replacement"
# readme_destination = "docs/docs/library_readmes/connectors"
# CONNECTOR_TAG = "Connectors"

# get the environment variables
library_repo_path = os.environ["INPUT_LIBRARY_REPO_PATH"]  # "library"
path_to_docs = os.environ["INPUT_DOCS_PATH"]  # "docs"
nav_replacement_placeholder = os.environ["INPUT_REPLACEMENT_PLACEHOLDER"]  #ConnectorsGetInsertedHere
connectors_tile_replacement_placeholder = "#connectors_tile_replacement"
readme_destination = os.environ["INPUT_README_DEST"]  # "docs/docs/library_readmes/connectors"
CONNECTOR_TAG = "Connectors"

class File:
    name = ''
    name = ''
    path = ''
    full_path = ''

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.full_path = "{}/{}".format(self.path, self.name)
        pass


class LibraryJsonFile(File):
    title = ''
    description = ''
    icon_file_path = ''
    icon_file = ''
    has_icon = False
    readme_file_path = ''
    is_source = False
    is_destination = False


    readme_path = ''
    json = ''
    short_description = ''
    icon = ''


def get_files(source_dir, search_pattern) -> List[File]:
    found_files = []
    for path in Path(source_dir).rglob(search_pattern):
        file = File(path.name, path.parent)
        found_files.append(file)
    return found_files


def json_has_tag(dict_var, tag, value):
    for k, v in dict_var.items():
        if k.lower() == tag.lower() and (value == "" or value in v):
            yield v
        elif isinstance(v, dict):
            for id_val in json_has_tag(v, tag, value):
                yield id_val


def load_json_file(path):
    if not os.path.exists(path):
        raise Exception("File {} not found".format(path))

    f = open(path, "r")
    contents = f.read()
    return json.loads(contents)


# todo rename to safe_file_name
def replace_chr(value):
    exclude_list = "\\/*?. "
    found = []
    for i, v in enumerate(value):
        if v not in exclude_list:
            found.append(v)
    return "".join(found)


def copy_files_new(connector_descriptors: List[LibraryJsonFile], target_dir):
    if not os.path.exists(target_dir + "/"):
        log(f"copy_files:: {target_dir} does not exist. Creating..")
        os.makedirs(os.path.dirname(target_dir + "/"), exist_ok=True)

    # private function to determine file suffix
    def suffix(connector: LibraryJsonFile) -> str:
        if connector.is_destination:
            return "destination"
        elif connector.is_source: 
            return "source"
        else:
            return ""

    # private function to remove existing file
    def remove_file_if_exists(file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

    # private function to copy a file
    def copy_file(file_source, file_dest):
        shutil.copy2(file_source, file_dest)

    # for each identified connector:
    for connector in connector_descriptors:
        # determine new file names
        new_readme_filename = (replace_chr(f"{connector.title}-{suffix(connector)}") + ".md").lower()
        
        # clean up old files
        remove_file_if_exists(new_readme_filename)

        try:
            # copy the files to the dest dir
            copy_file(connector.readme_file_path, f"{target_dir}/{new_readme_filename}")

            # update the connector with the new file paths
            connector.readme_file_path = f"{target_dir}/{new_readme_filename}"


            if connector.has_icon:
                new_icon_filename = (replace_chr(f"{connector.title}-{suffix(connector)}-") + connector.icon_file).lower()
                remove_file_if_exists(new_icon_filename)
                copy_file(connector.icon_file_path, f"{target_dir}/{new_icon_filename}")
                connector.icon_file_path = f"{target_dir}/{new_icon_filename}"


        except Exception as e:
            pass


def get_file_path(path, file_name, search_pattern):
    files = get_files(path, search_pattern)
    for file in files:
        if str(file.name).lower() == file_name:
            return file.full_path


def get_json_value(json_data, key):

    if key in json_data:
        return json_data[key]

    return ""


def get_library_item_with_tag(files: List[File], tag: str, tag_value: str) -> List[LibraryJsonFile]:
    found: List[LibraryJsonFile] = []

    for file in files:
        json_data = load_json_file(file.full_path)

        for _ in json_has_tag(json_data, tag, tag_value):
            f = LibraryJsonFile(file.name, file.path)

            # todo remove
            try:
                f.title = get_json_value(json_data, "name")
                f.description = get_json_value(json_data, "shortDescription")
                icon_file = get_json_value(json_data, "IconFile")
                
                if icon_file != "":
                    f.icon_file = icon_file
                    f.icon_file_path = f"{file.path}\{icon_file}"
                    f.has_icon = True

                f.readme_file_path = get_file_path(file.path, "readme.md", "*.md")
                f.is_source = get_json_value(json_data, "tags")['Pipeline Stage'][0] == "Source"
                f.is_destination = get_json_value(json_data, "tags")['Pipeline Stage'][0] == "Destination"


                # todo remove
                f.json = json_data
                found.append(f)
            except Exception as e:
                print("error")

    return found


def build_nav_dict(library_files: List[LibraryJsonFile], is_source=False, is_destination=False):
    nav = {}
    for library_file in library_files:
        if library_file.is_source == is_source and library_file.is_destination == is_destination:
            lib_id = library_file.json["libraryItemId"]
            nav[lib_id] = {
                "name": library_file.json["name"],
                "readme": library_file.readme_file_path,
                "short_description": library_file.description,
                "icon": library_file.icon_file_path
            }
    return nav


def build_nav(nav_dict, section_title):
    nav_replacement_lines = []
    nav_title_indentation = 6  # spaces
    spaces = ""
    spaces += ' ' * nav_title_indentation

    log(f"Adding nav entries for '{section_title}'")

    line = f"{spaces}- '{section_title}':"
    log(line)
    nav_replacement_lines.append(line)
    for n in nav_dict:
        path_to_readme = nav_dict[n]["readme"].replace("docs/", "")
        line = f"{spaces}  - '{nav_dict[n]['name']}': '{path_to_readme}'"
        log(line)
        nav_replacement_lines.append(line)
    return nav_replacement_lines


def build_landing_page(nav_dict, section_title):
    nav_replacement_lines = []

    line = f"\n## {section_title}"
    nav_replacement_lines.append(line)

    line = '<div class ="grid cards"><ul>'
    nav_replacement_lines.append(line)

    for n in nav_dict:
        name = nav_dict[n]['name']
        path_to_readme = nav_dict[n]["readme"].replace("docs/", "").replace(".md", ".html")
        path_to_icon = nav_dict[n]["icon"].replace("docs/", "")
        nav_replacement_lines.append(f"<li>")
        nav_replacement_lines.append(f"<div style='display:flex'>")
        if path_to_icon != "":
            nav_replacement_lines.append(f"<img src='../../{path_to_icon}' style='max-width:40px;border-radius:8px;'>")
        nav_replacement_lines.append(f"<p style='min-width: 100px;'>")
        nav_replacement_lines.append(f"<strong style='margin-left:9px;border-radius: 8px;'>{nav_dict[n]['name']}</strong>")
        nav_replacement_lines.append(f"</p>")
        nav_replacement_lines.append(f"</div>")
        nav_replacement_lines.append(f"<hr>")
        nav_replacement_lines.append(f"<p>{nav_dict[n]['short_description']}</p>")
        nav_replacement_lines.append(f"<p><a href='../../{path_to_readme}'><span class='twemoji'><svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'><path d='M13.22 19.03a.75.75 0 0 0 1.06 0l6.25-6.25a.75.75 0 0 0 0-1.06l-6.25-6.25a.75.75 0 1 0-1.06 1.06l4.97 4.97H3.75a.75.75 0 0 0 0 1.5h14.44l-4.97 4.97a.75.75 0 0 0 0 1.06z' fill-rule='evenodd'></path></svg></span> {name}</a></p>")
        nav_replacement_lines.append(f"</li>")

    nav_replacement_lines.append("</ul></div>")
    return nav_replacement_lines


def update_file(nav_file_path, find_text, replacement_text):
    with open(nav_file_path, 'r') as file:
        file_data = file.read()
    file_data = file_data.replace(find_text, replacement_text)
    with open(nav_file_path, 'w') as file:
        file.write(file_data)


def set_action_output(name: str, value: str):
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(f"{name}={value}\n")


def log(message):
    print(message)
    logs.append(message)


def generate_nav(connectors: List[LibraryJsonFile]) -> str:
    
    # list sources
    sources = build_nav_dict(connectors, is_source=True)

    # build sources nav
    sources_nav = build_nav(sources, "Sources")

    # list destinations
    destinations = build_nav_dict(connectors, is_destination=True)
    
    # build destinations nav
    destinations_nav = build_nav(destinations, "Destinations")

    # join both nav lists
    sources_nav.extend(destinations_nav)

    #return as new line joined string
    return "\n".join(sources_nav)


def get_file(path_to_docs, file_name):
    # get the nav file
    files = get_files(path_to_docs, file_name)
    if len(files) == 0:
        log(f"{file_name} not found")
        raise Exception(f"{file_name} not found in {path_to_docs}")
    log(f"Found file path: {files[0].full_path}")
    return files[0].full_path


def add_connectors_to_navigation(tech_connector_representation):
    # generate connectors nav items
    connectors_nav_string = generate_nav(tech_connector_representation)

    # get the main yaml file
    yaml_file_path = get_file(path_to_docs, 'mkdocs.yml')

    log(f"Nav replacement string: {connectors_nav_string}")
    update_file(yaml_file_path, nav_replacement_placeholder, connectors_nav_string)


def update_connectors_landing_page(tech_connector_representation):
    
    sources = build_nav_dict(tech_connector_representation, is_source=True)
    sources_landing_page_items = build_landing_page(sources, "Sources")

    destinations = build_nav_dict(tech_connector_representation, is_destination=True)
    destinations_landing_page_items = build_landing_page(destinations, "Destinations")

    sources_landing_page_items.extend(destinations_landing_page_items)

    # get the connectors index file
    path = "docs/platform/connectors"
    log(f"Looking for index.md in: {path}")

    #brute force to find the connector index.md file!
    def scan(d, spacer, cb):
        object = os.scandir(d)
        
        for n in object :
            if n.is_dir() or n.is_file():
                padding = ''
                padding += ' ' * spacer
                print(padding + n.name)
                if(n.name == "index.md") and "connectors" in n.path:
                    cb(n.path)
            if n.is_dir():
                scan(n, spacer + 4, cb)
        object.close()

    def set_path(s):
        update_file(s, connectors_tile_replacement_placeholder, "\n".join(sources_landing_page_items))

    scan("docs", 0, set_path)


def main():
    try:

        # find library.json files
        library_file_dictionary = get_files(library_repo_path, 'library.json')

        # get details of tech connectors incl icon and readme paths
        tech_connectors = get_library_item_with_tag(library_file_dictionary, "type", CONNECTOR_TAG)

        # copy readmes and icons to dest folder
        copy_files_new(tech_connectors, readme_destination)

        # add all connectors to the nav list in mkdocs.yaml
        add_connectors_to_navigation(tech_connectors)

        # build connectors landing page
        update_connectors_landing_page(tech_connectors)

    except Exception as e:
        print(f"Error: {traceback.print_exc()}")
        log(f"Error: {traceback.print_exc()}")
    finally:
        set_action_output("logs", logs)
        #print(logs)


if __name__ == "__main__":
    main()
