
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fnmatch
import os, sys
import zipfile
from lxml import etree
import regex as re

# arguments
omtprj_path = "/home/souto/Repos/capstanlqc/bitext-utils/repos/pisa_2025ft_translation_hr-HR_verification-review"
tm_dpath = f"{omtprj_path}/tm"
locale = "hr-HR" # get it from params or extract it from path or project settings's target_lang


# functions 
def get_target_lang():
    pass


def get_translations(fpath):
    target_tuvs = []
    parser = etree.XMLParser(resolve_entities=False)
    # doc = etree.parse(fpath, parser)
    with open(fpath, 'r') as f:
        xml = f.read()
    doc = etree.fromstring(xml.encode('utf-8'))
    exprs = [f"//tuv[@xml:lang='{locale}']/seg/text()", f"//tuv[@lang='{locale}']/seg/text()"]
    for expr in exprs:
        target_tuvs.extend(get_nodes(doc, expr))

    return strip_tags(target_tuvs)


def get_nodes(doc, expr):
    try: 
        return doc.xpath(expr)
    except IndexError as e:
        add_to_log("Node not found")
        return None


# find TMs
def find_files_in_path(tm_dpath):
    matches = []
    for root, dirnames, filenames in os.walk(tm_dpath):
        # if root.split("/")[-1] == "prev": # trend
        for filename in fnmatch.filter(filenames, '*.tmx*'):
            matches.append(os.path.join(root, filename))

    return matches


# unzip TMs
def unzip_zipped_files(matches):
    for fpath in matches:
        if fpath.endswith(".tmx.zip"):
            parent_dpath = os.path.dirname(fpath)
            with zipfile.ZipFile(fpath, 'r') as zip_ref:
                zip_ref.extractall(parent_dpath)
    return True


# get text nodes
def get_translations_per_file(matches):
    translations_per_file = {}
    for fpath in matches:
        if fpath.endswith(".tmx"):
            fname = os.path.basename(fpath)
            translations_per_file[fname] = get_translations(fpath)
    
    return translations_per_file


def strip_tags(list_of_strings):
    return [re.sub('(&lt;[^&]+&gt;|<[^&]+>)', '', string) for string in list_of_strings]


def find_pattern(translations_per_file, pattern, regex=False):
    matches = {}
    print(f"{pattern.encode('unicode_escape')=}")
    for file, list_of_strs in translations_per_file.items():
        matches[file] = []
        for string in list_of_strs:
            # if regex is False
            if pattern in string:
            # if re.search(fr"{pattern}", string):
                matches[file].extend([string])

    # remove empty keys (files with no segments)
    return {key: value for (key, value) in matches.items() if value}


            # filter translations_per_file to contain only segments with nbsp
            # then strip nbsp and look for same segment in all segments again
            # if found without nbsp, report it (file, segment)



# logic
if __name__ == "__main__":

    tm_files = find_files_in_path(tm_dpath)
    # unzip_zipped_files(tm_files)
    translations_per_file = get_translations_per_file(tm_files)


    substr = "\u00A0"
    # text = "15 °C"
    # x = text.encode("unicode_escape")
    # print(x)
    # if pattern in text:
    #     print("found")


    instances = find_pattern(translations_per_file, substr, False)
    working_translations = get_translations(os.path.join(omtprj_path, "omegat", "project_save.tmx"))

    for file, translations in instances.items():
        for xlat in translations:
            if xlat.replace(substr, ' ') in working_translations:
                print(f"Found xlat '{xlat}'")

    print(instances)
    print()
    print(working_translations)


    print("done")