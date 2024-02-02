
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# run as 
# python code/find_spacing_diff.py --path /path/to/omegat_project
# or 
# python code/find_spacing_diff.py --fix y --path /path/to/omegat_project
# (to have it fixed)

import argparse
import json
import fnmatch
import os, sys
import zipfile
from lxml import etree
import regex as re
from rich import print
import pandas as pd
# https://pypi.org/project/prettyformatter/ 
# https://stackoverflow.com/questions/3229419/how-to-pretty-print-nested-dictionaries


# ############# PROGRAM DESCRIPTION ###########################################

text = "Find missing no-break spaces, optionally restores them"
parser = argparse.ArgumentParser(description=text)
parser.add_argument("-V", "--version", help="show program version", action="store_true")
parser.add_argument("-p", "--path", help="specify path to the local clone of the repo hosting the omegat team project")
parser.add_argument("-f", "--fix", help="specify whether no-break spaces should be restored or not")
args = parser.parse_args()

version_text = "OmegaT git project manager 1.0"
if args.version:
    print(version_text)
    sys.exit()

fix = args.fix.strip() if args.fix else None

if args.path:
     omtprj_path = args.path.strip()
else:
     print("No 'path' argument has been provided. Run this script with `--help` for details.")
     sys.exit()

# ############# FUNCTIONS ###########################################

def get_files_by_text(text, instances):
    return [file for file, translations in instances.items() if text in translations]


def get_target_lang(omtprj_path):
    omegat_project_fpath = os.path.join(omtprj_path, "omegat.project")
    # pattern = '(?<=TARGET_LANG ")[a-z]+(?=-[^"]+")'
    pattern = '(?<=TARGET_LANG ")[a-z]+-[^"]+'

    with open(omegat_project_fpath, 'r') as f:
        omegat_project = f.read()
    
    matches = re.findall(pattern, omegat_project)
    # print("looking for the target language subtag")
    return matches[0]


def get_translations(fpath, locale):
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


def find_files_in_path(tm_dpath):
    """ Find TMs """
    matches = []
    for root, dirnames, filenames in os.walk(tm_dpath):
        # if root.split("/")[-1] == "prev": # trend
        for filename in fnmatch.filter(filenames, '*.tmx*'):
            matches.append(os.path.join(root, filename))

    return matches


def unzip_zipped_files(matches):
    """ Unzip TMs """
    for fpath in matches:
        if fpath.endswith(".tmx.zip"):
            parent_dpath = os.path.dirname(fpath)
            with zipfile.ZipFile(fpath, 'r') as zip_ref:
                zip_ref.extractall(parent_dpath)
    return True


def get_translations_per_file(matches, target_lang):
    """ get text nodes """
    translations_per_file = {}
    for fpath in matches:
        if fpath.endswith(".tmx"):
            fname = os.path.basename(fpath)
            translations_per_file[fname] = get_translations(fpath, target_lang)
    
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


def edit_file(fpath, replacement_map, locale):

    exprs = [f"//tuv[@xml:lang='{locale}']/seg", f"//tuv[@lang='{locale}']/seg"]

    parser = etree.XMLParser(resolve_entities=False)
    doc = etree.parse(fpath, parser)

    for expr in exprs:
        if doc.xpath(expr):
            for seg in doc.xpath(expr):
                if seg.text in replacement_map:
                    print(f"Correcting '{seg.text}' to 'replacement_map[seg.text]")
                    seg.text = replacement_map[seg.text]
                    

    # etree.indent(common_repo, space=determine_white_space(omegat_project_fpath), level=3)
    doc.write(fpath, encoding='UTF-8', pretty_print=True, standalone=True)



def save_report_replacements(replacement_map, instances, omtprj, rpt_suffix):
    
    rows = [(key, value, ", ".join(get_files_by_text(value, instances)) )
        for (key, value) in replacement_map.items()]

    # create a df from the list of tuples
    df = pd.DataFrame(rows, columns=['Transferred', 'Original trend', 'File'])

    # export
    df.to_excel(f"{omtprj}_{rpt_suffix}.xlsx", index=False)


def save_report_instances(instances, omtprj, rpt_suffix):
    
    # create a list of tuples in the desired format
    rows = [(key, value) for key, values in instances.items() for value in values]

    # create a df from the list of tuples
    df = pd.DataFrame(rows, columns=['File', 'Text'])

    # export
    df.to_excel(f"{omtprj}_{rpt_suffix}.xlsx", index=False)



if __name__ == "__main__":

    target_lang = get_target_lang(omtprj_path)
    tm_dpath = os.path.join(omtprj_path, "tm")
    omtprj = os.path.basename(omtprj_path.rstrip("/")).lstrip("pisa_2025ft_translation_")
    
    tm_files = find_files_in_path(tm_dpath)
    # unzip_zipped_files(tm_files)
    translations_per_file = get_translations_per_file(tm_files, target_lang)

    # character to be found
    substr = "\u00A0"

    working_tm_fpath = os.path.join(omtprj_path, "omegat", "project_save.tmx")
    instances = find_pattern(translations_per_file, substr, False)

    working_translations = get_translations(working_tm_fpath, target_lang)
    replacement_map = {}

    for file, translations in instances.items():
        for xlat in translations:
            # replace the non-breaking space with a normal space to find 
            if xlat.replace(substr, ' ') in working_translations:
                replacement_map[xlat.replace(substr, ' ')] = xlat
                # print(f"Found xlat '{xlat}'")
    
    print("\nMatches in TMs containing no-break space(s):")
    print(instances)

    print("\nNecessary corrections:")
    print(replacement_map)

    if fix and fix.lower().startswith('y'):
        print("\nRestoring nbsp's in working TM")
        edit_file(working_tm_fpath, replacement_map, target_lang)

    save_report_instances(instances, omtprj, "nbsp_in_trend")
    save_report_replacements(replacement_map, instances, omtprj, "replacements")


    print("\ndone")

# caveats: 
# this assumes that if any no-breaking spaces are found in the trend translation, 
# all of them have been stripped in the new translation. in other words, it won't flag 
# mismatches if one nbsp is missed but another one is there (future improvement if needed)

# todo: 
# perhaps: restrict what files function find_files_in_path finds, to use only trend TMs (not sure
# this is necessary, it depends on what TMs are added to the trend trasnfer projects) and 
# to use only the original TMs files, not the ones that Kos created to increase leverage

# todo:
# fine tune where reports are written