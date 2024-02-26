import os
import traceback
import shutil
from pathlib import Path
import json
from typing import List
import re

## TODO
# docs builds should clone docs repo into a subfolder for cleaner look and easier debug
# there are some hard coded paths here, remove and add as env vars where appropriate
# add different debug levels


connectors_md_path = ''
logs = []

library_repo_path = os.getenv("INPUT_LIBRARY_REPO_PATH", "samples")
path_to_docs = os.getenv("INPUT_DOCS_PATH", "")
nav_replacement_placeholder = os.getenv("INPUT_REPLACEMENT_PLACEHOLDER", "#ConnectorsGetInsertedHere")
connectors_tile_replacement_placeholder = os.getenv("INPUT_CONNECTORS_TITLE_REPLACEMENT", "[//]: <> (#connectors_tile_replacement)")
readme_destination = ""
CONNECTOR_TAG = os.getenv("INPUT_CONNECTORS_TAG", "Connectors")
NAV_INDENTATION = int(os.getenv("INPUT_NAV_INDENT_SPACES", "6"))

# for testing
#library_repo_path = "C:\Code\Quix\GitHub\quix-library"

class File:
    name = ''
    name = ''
    path = ''
    full_path = ''

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.full_path =  os.path.join(self.path, self.name)
        pass

class LibraryJsonFile(File):
    title = ''
    description = ''
    icon_file_path = ''
    icon_file = ''
    has_icon = False
    readme_file_path = ''
    base_path = ''
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


def use_fwd_slash(s):
    return s.replace("\\", "//")


def copy_files(connector_descriptors: List[LibraryJsonFile], target_dir):
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
        log(f"{file_path} exists. Removing..")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                log("###########################")
                log(f"Error deleting file file: " + e)
                log("###########################")

    # private function to copy a file
    def copy_file(file_source, file_dest):
        log(f"Copying from [{file_source}] to [{file_dest}]")
        shutil.copy2(file_source, file_dest)

    def check_dir_exists(dir):
        if not os.path.exists(dir):
                raise Exception(f"{dir} not found")
    
    def check_file_exists(file):
        if not os.path.exists(file):
                raise Exception(f"{file} not found")

    def copy_image_files(connector: LibraryJsonFile, target_dir):

        # first get the images files from the current readme
        # then copy them to the target directory

        with open(connector.readme_file_path, 'r') as file:
            file_contents = file.read()

        images = re.findall("!\[.+\]\((.*?)[\?|\)]", file_contents)
        log(f"Images found in {connector.readme_file_path} = {images}")

        for image in images:
            source_image_path = os.path.join(connector.base_path, image)
            dest_image_path = os.path.join(target_dir, image)
            if os.path.exists(source_image_path):
                shutil.copy2(source_image_path, dest_image_path)
            else:
                log(f"{image} not found in {connector.base_path}")


    # for each identified connector:
    for connector in connector_descriptors:
        # determine new file names
        new_readme_filename = (replace_chr(f"{connector.title}-{suffix(connector)}") + ".md").lower()
        
        # clean up old files
        remove_file_if_exists(new_readme_filename)

        try:

            # copy the files to the dest dir

            check_dir_exists(target_dir)
            
            copy_file(connector.readme_file_path, os.path.join(target_dir, new_readme_filename))

            copy_image_files(connector, target_dir)

            # update the connector with the new file paths
            connector.readme_file_path = os.path.join(target_dir, new_readme_filename)

            if connector.has_icon:
                new_icon_filename = (replace_chr(f"{connector.title}-{suffix(connector)}-") + connector.icon_file).lower()
                remove_file_if_exists(new_icon_filename)

                check_dir_exists(target_dir)
                check_file_exists(connector.icon_file_path)
                copy_file(use_fwd_slash(connector.icon_file_path), os.path.join(target_dir, new_icon_filename))

                connector.icon_file_path = os.path.join(target_dir, new_icon_filename)
                log(f"Connector [{connector.name}] icon path is {connector.icon_file_path}")

        except Exception as e:
            log("###########################")
            log(f"Error copy files:" + e)
            log("###########################")


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
                    #f.icon_file_path = f"{file.path}/{icon_file}"
                    f.icon_file_path = os.path.join(file.path, icon_file)
                    f.has_icon = True

                f.readme_file_path = get_file_path(file.path, "readme.md", "*.md")
                f.base_path = file.path
                f.is_source = get_json_value(json_data, "tags")['Pipeline Stage'][0] == "Source"
                f.is_destination = get_json_value(json_data, "tags")['Pipeline Stage'][0] == "Destination"
                log(f"Connector [{f.title}], IconFilePath={f.icon_file_path}. ReadmePath={f.readme_file_path}")

                # todo remove
                f.json = json_data
                found.append(f)
            except Exception as e:
                log("Error " + e)

    return found


def build_nav_dict(library_files: List[LibraryJsonFile], is_source=False, is_destination=False):
    log("Building nav dictionary")
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
            log(f"NavItem={nav[lib_id]}")
    return nav


def build_nav(nav_dict, section_title):
    nav_replacement_lines = []
    nav_title_indentation = NAV_INDENTATION  # spaces
    spaces = ""
    spaces += ' ' * nav_title_indentation

    log(f"Adding nav entries for '{section_title}'")

    line = f"{spaces}- '{section_title}':"
    log(line)
    nav_replacement_lines.append(line)
    for n in nav_dict:
        path_to_readme = nav_dict[n]["readme"].replace("docs" + os.sep, "")
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
        path_to_readme = nav_dict[n]["readme"].replace("docs" + os.sep, "").replace(".md", ".html")
        path_to_icon = nav_dict[n]["icon"].replace("docs" + os.sep, "")
        log(f" readme={path_to_readme}")
        log(f" icon={path_to_icon}")
        nav_replacement_lines.append(f"<li>")
        nav_replacement_lines.append(f"<div style='display:flex'>")
        if path_to_icon != "":
            nav_replacement_lines.append(f"<img src='../{path_to_icon}' style='max-width:40px;border-radius:8px;'>")
        nav_replacement_lines.append(f"<p style='min-width: 100px;margin-top:7px'>")
        nav_replacement_lines.append(f"<strong style='margin-left:9px;border-radius: 8px;'>{nav_dict[n]['name']}</strong>")
        nav_replacement_lines.append(f"</p>")
        nav_replacement_lines.append(f"</div>")
        nav_replacement_lines.append(f"<hr>")
        nav_replacement_lines.append(f"<p>{nav_dict[n]['short_description']}</p>")
        nav_replacement_lines.append(f"<p><a href='../{path_to_readme}'><span class='twemoji'><svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'><path d='M13.22 19.03a.75.75 0 0 0 1.06 0l6.25-6.25a.75.75 0 0 0 0-1.06l-6.25-6.25a.75.75 0 1 0-1.06 1.06l4.97 4.97H3.75a.75.75 0 0 0 0 1.5h14.44l-4.97 4.97a.75.75 0 0 0 0 1.06z' fill-rule='evenodd'></path></svg></span> {name}</a></p>")
        nav_replacement_lines.append(f"</li>")

    nav_replacement_lines.append("</ul></div>")
    return nav_replacement_lines


def update_file(nav_file_path, find_text, replacement_text):

    log(f"Replacing {find_text} in {nav_file_path} with:")
    log(replacement_text)

    with open(nav_file_path, 'r') as file:
        file_data = file.read()
    file_data = file_data.replace(find_text, replacement_text)
    with open(nav_file_path, 'w') as file:
        file.write(file_data)


def set_action_output(name: str, value: str):
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(f"{name}={value}\n")


def log(message):
    print(f"\n{message}")
    logs.append(f"\n{message}")


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
    log("Building connectors landing page")
    
    log("Sources...")
    sources = build_nav_dict(tech_connector_representation, is_source=True)
    sources_landing_page_items = build_landing_page(sources, "Sources")

    log("Destinations...")
    destinations = build_nav_dict(tech_connector_representation, is_destination=True)
    destinations_landing_page_items = build_landing_page(destinations, "Destinations")

    sources_landing_page_items.extend(destinations_landing_page_items)

    # get the connectors index file
    # path = "docs/platform/connectors"
    # log(f"Looking for index.md in: {path}")

    landing_page_replacement_text = "\n".join(sources_landing_page_items)

    fp = os.path.join("docs", "connectors", "index.md")
    update_file(fp, connectors_tile_replacement_placeholder, landing_page_replacement_text)


def log_file_structure(starting_directory = ""):
    
    def scan(d, cb, spacer = 0):
        object = os.scandir(d)

        # iterate all the directories and files in the specified path
        for n in object :
            if n.is_dir() or n.is_file():
                padding = ''
                padding += ' ' * spacer
                log(padding + n.name)
                #if(n.name == "index.md") and "connectors" in n.path:
                #    cb(n.path)
            if n.is_dir():
                scan(n, cb, spacer + 4)
        object.close()

    def found_path_callback(s):
        log("***found it here " + s)

    scan(starting_directory, found_path_callback)

    # log(f"index.md should be in: docs/platform/connectors/index.md")
    # if os.path.exists("docs/platform/connectors/index.md"):
    #     log("***it exists!")

def sort_library_list(library_list: List[LibraryJsonFile]):
    def get_name(json):
        try:
            return json.title
        except AttributeError:
            return 0

    library_list.sort(key=get_name)
    

def main():
    try:
        log("*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*")
        log("Config Values:")
        log(f"library_repo_path: {library_repo_path}")
        log(f"path_to_docs: {path_to_docs}")
        log(f"nav_replacement_placeholder: {nav_replacement_placeholder}")
        log(f"connectors_tile_replacement_placeholder: {connectors_tile_replacement_placeholder}")
        log(f"CONNECTOR_TAG: {CONNECTOR_TAG}")
        log(f"NAV_INDENTATION: {NAV_INDENTATION}")
        log("*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*")

        readme_destination = os.path.join("docs", "connectors")

        # find library.json files
        library_file_dictionary = get_files(library_repo_path, 'library.json')

        # get details of tech connectors incl icon and readme paths
        tech_connectors = get_library_item_with_tag(library_file_dictionary, "type", CONNECTOR_TAG)

        sort_library_list(tech_connectors)

        # copy readmes and icons to dest folder
        copy_files(tech_connectors, readme_destination)

        # add all connectors to the nav list in mkdocs.yaml
        add_connectors_to_navigation(tech_connectors)

        # build connectors landing page
        update_connectors_landing_page(tech_connectors)

    except Exception as e:
        log(f"Error: {traceback.print_exc()}")

        log_file_structure()
    finally:
        set_action_output("logs", logs)


if __name__ == "__main__":
    main()
