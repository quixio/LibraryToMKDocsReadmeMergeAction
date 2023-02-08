import os
import traceback
import shutil
from pathlib import Path
import json
from typing import List


logs = []

# get the environment variables
library_repo_path = os.environ["INPUT_LIBRARY_REPO_PATH"]  # "library"
path_to_docs = os.environ["INPUT_DOCS_PATH"]  # "docs"
nav_replacement_placeholder = os.environ["INPUT_REPLACEMENT_PLACEHOLDER"]  #ConnectorsGetInsertedHere
connectors_tile_replacement_placeholder = "#connectors_tile_replacement"
readme_destination = os.environ["INPUT_README_DEST"]  # "docs/docs/library_readmes/connectors"


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


class LibrayJsonFile(File):
    readme_path = ''
    json = ''
    short_description = ''


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


def get_files_for_tag(json_data, folder_path: str, tag: str, tag_value: str, search_pattern: str):
    files = []

    for _ in json_has_tag(json_data, tag, tag_value):
        files = get_files(folder_path, search_pattern)

    return files


def has_tag(json_data, tag: str, tag_value: str):
    for _ in json_has_tag(json_data, tag, tag_value):
        return True
    return False


def load_json_file(path):
    if not os.path.exists(path):
        raise Exception("File {} not found".format(path))

    f = open(path, "r")
    contents = f.read()
    return json.loads(contents)


def replace_chr(value):
    exclude_list = "\\/*?. "
    found = []
    for i, v in enumerate(value):
        if v not in exclude_list:
            found.append(v)
    return "".join(found)


def copy_files(files, target_dir):

    if not os.path.exists(target_dir + "/"):
        log(f"copy_files:: {target_dir} does not exist. Creating..")
        os.makedirs(os.path.dirname(target_dir + "/"), exist_ok=True)

    for file in files:
        new_filename = replace_chr(file.json["name"]) + ".md"
        dest = "{}/{}".format(target_dir, new_filename)

        if os.path.exists(dest):
            os.remove(dest)

        shutil.copy2(file.readme_path, dest)
        file.readme_docs_path = dest

    return files


def get_library_item_with_tag(files: List[File], tag: str, tag_value: str) -> List[LibrayJsonFile]:
    found: List[LibrayJsonFile] = []

    for file in files:
        json_data = load_json_file(file.full_path)

        for _ in json_has_tag(json_data, tag, tag_value):
            f = LibrayJsonFile(file.name, file.path)
            f.json = json_data
            found.append(f)

    return found


def get_named_files_associated_with_library_file(library_files: List[LibrayJsonFile], name: str, search_pattern: str) -> List[LibrayJsonFile]:

    for libraryFile in library_files:
        files = get_files(libraryFile.path, search_pattern)
        for file in files:
            if str(file.name).lower() == name:
                libraryFile.readme_path = file.full_path

    return library_files


def get_item_by_tag(library_files: List[LibrayJsonFile], tag, tag_value):
    sources = []
    for t in library_files:
        if has_tag(t.json["tags"], tag, tag_value):
            sources.append(t)
    return sources


def build_nav_dict(library_files: List[LibrayJsonFile]):
    nav = {}
    for library_files in library_files:
        lib_id = library_files.json["libraryItemId"]
        nav[lib_id] = {
            "name": library_files.json["name"],
            "readme": library_files.readme_docs_path,
            "short_description": library_files.json["shortDescription"]
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

    line = '<div class ="grid cards" markdown >'
    nav_replacement_lines.append(line)

    for n in nav_dict:
        path_to_readme = nav_dict[n]["readme"].replace("docs/", "")
        name = nav_dict[n]['name']
        nav_replacement_lines.append(f"")
        nav_replacement_lines.append(f" - __{name}__")
        nav_replacement_lines.append(f"")
        nav_replacement_lines.append(f"     ---")
        nav_replacement_lines.append(f"")
        nav_replacement_lines.append(f"     {nav_dict[n]['short_description']}")
        nav_replacement_lines.append(f"")
        nav_replacement_lines.append(f"     [:octicons-arrow-right-24: {name}](../../{path_to_readme})")

    nav_replacement_lines.append("</div>")
    return nav_replacement_lines


def gen_nav_replacement(tech_readmes, section_title, tag, tag_value):
    tagged_items = get_item_by_tag(tech_readmes, tag, tag_value)
    nav_dict = build_nav_dict(tagged_items)
    return build_nav(nav_dict, section_title)


def gen_landing_page_replacement(tech_readmes, section_title, tag, tag_value):
    tagged_items = get_item_by_tag(tech_readmes, tag, tag_value)
    nav_dict = build_nav_dict(tagged_items)
    return build_landing_page(nav_dict, section_title)


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


def main():
    try:

        library_file_dictionary = get_files(library_repo_path, 'library.json')

        # filter library files down to specific tag and value
        tech_connector_library_files = get_library_item_with_tag(library_file_dictionary, "type", "Tech connectors")

        # get readme's for those library items, filtering on tag and value
        tech_readmes = get_named_files_associated_with_library_file(tech_connector_library_files, "readme.md", "*.md")

        tech_readmes = copy_files(tech_readmes, readme_destination)

        # generate the nav replacements
        nav_replacement = []

        sources_nav_replacement = gen_nav_replacement(tech_readmes, "Sources", "Pipeline Stage", "Source")
        destinations_nav_replacement = gen_nav_replacement(tech_readmes, "Destinations", "Pipeline Stage", "Destination")

        # to have the technologies category or any other category that might repeat readmes
        # (or use readmes for a second or 3rd time)
        # we'd have to determine the categories first, then find the readme to go with it,
        # we'd also have to copy the file and give it a unique name
        # otherwise mkdocs will select the last nav item to link to that md file rather than the nav item clicked
        # technologies_nav_replacement = gen_nav_replacement(tech_readmes, "Technologies", "Technology", "")

        # add them to the nav array
        nav_replacement.extend(sources_nav_replacement)
        nav_replacement.extend(destinations_nav_replacement)
        # nav_replacement.extend(technologies_nav_replacement)

        # log(f"Nav replacement built\n [{nav_replacement}]")

        # get the nav file
        nav_files = get_files(path_to_docs, 'mkdocs.yml')
        if len(nav_files) == 0:
            log("mkdocs.yml not found")
            raise Exception(f"mkdocs.yml not found in {path_to_docs}")

        # log(f"Updating nav file: {nav_files[0].full_path}")

        log(f"Yaml file path: {nav_files[0].full_path}")

        # join with new line
        n = "\n".join(nav_replacement)
        log(f"Nav replacement string: {n}")
        update_file(nav_files[0].full_path, nav_replacement_placeholder, "\n".join(nav_replacement))

        # generate landing page tiles
        sources_landing_page_content = ["## Sources"]
        destinations_landing_page_content = ["\n\n## Destinations"]

        sources_landing_page_content.extend(gen_landing_page_replacement(tech_readmes, "Sources", "Pipeline Stage", "Source"))
        destinations_landing_page_content.extend(gen_landing_page_replacement(tech_readmes, "Destinations", "Pipeline Stage", "Destination"))
        landing_page_content = sources_landing_page_content
        landing_page_content.extend(destinations_landing_page_content)


        path = "docs"
        log(f"{path} files")
        for f in Path(path).iterdir():
            log(f"\n{f}")

        # get the connectors index file
        path = "docs/platform"
        log(f"{path} files")
        for f in Path(path).iterdir():
            log(f"\n{f}")

        # get the connectors index file
        path = "docs/platform/connectors"
        log(f"{path} files")
        for f in Path(path).iterdir():
            log(f"\n{f}")


        files = get_files(path, 'index.md')
        if len(files) == 0:
            log("index.md not found")
            raise Exception(f"index.md not found in {path}")

        log(f"Yaml file path: {files[0].full_path}")

        update_file(files[0].full_path, connectors_tile_replacement_placeholder, "\n".join(landing_page_content))


    except Exception as e:
        print(f"Error: {traceback.print_exc()}")
        log(f"Error: {traceback.print_exc()}")
    finally:
        set_action_output("logs", logs)


if __name__ == "__main__":
    main()
