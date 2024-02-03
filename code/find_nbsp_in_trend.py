#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# download capstanlqc-pisa/pisa_2025ft_translation_common to repos
# @todo: unzip files pisa_2025ft_translation_common/assets/pisa22/{LOCALE}/PISA_*_MS2022.tmx.zip


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

try:
  import nltk
  # print("NLKT imported fine")
except BaseException as e:
  print(f"An exception occurred: {e}")

nltk.data.path.append("./Data/nltk_data")

try:
# nltk.download('punkt')
  nltk.download('punkt', download_dir='./Data/nltk_data')
  # print("Data downloaded")
except BaseException as e:
  print("An exception occurred" + e)


from collections import Counter

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

    print(f"{omegat_project_fpath=}")
    with open(omegat_project_fpath, 'r') as f:
        omegat_project = f.read()
    
    matches = re.findall(pattern, omegat_project)
    # print("looking for the target language subtag")
    return matches[0]


def get_translations(fpath, locale):

    print(f"{fpath=}")
    print(f"{locale=}")

    if not fpath or not locale:
        return None

    target_tuvs = []
    parser = etree.XMLParser(resolve_entities=False)
    # doc = etree.parse(fpath, parser)
    with open(fpath, 'r') as f:
        xml = f.read()
    doc = etree.fromstring(xml.encode('utf-8'))
    
    exprs = [f"//tuv[@xml:lang='{locale}']/seg/text()", f"//tuv[@lang='{locale}']/seg/text()"]
    for expr in exprs:
        target_tuvs.extend(get_nodes(doc, expr))

    # print(f"{target_tuvs=}")
    # return preprocess(target_tuvs)
    return [strip_tags(tuv) for tuv in target_tuvs]


def get_nodes(doc, expr):
    try: 
        return doc.xpath(expr)
    except IndexError as e:
        add_to_log("Node not found")
        return None


def find_files_in_path(tm_dpath):
    """ Find TMs: might have to be capstanlqc-pisa/pisa_2025ft_translation_common/tm/assets/pisa22/&TARGET_LANG; """
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


def get_translations_per_file(files, target_lang):
    """ get text nodes """
    translations_per_file = {}
    for fpath in files:
        if fpath.endswith(".tmx"):
            fname = os.path.basename(fpath)
            translations_per_file[fname] = preprocess(get_translations(fpath, target_lang))
    
    return translations_per_file


def preprocess(list_of_paragraphs):
    return [strip_tags(sentence) for para in list_of_paragraphs for sentence in do_segmentation(str(para)) 
            if strip_tags(sentence) != '' and strip_tags(sentence) != ' ']


def do_segmentation(paragraph):
    return [sentence for sentence in nltk.sent_tokenize(paragraph)]


def strip_tags(string):
    # return [re.sub('(&lt;[^&]+&gt;|<[^&]+>)', '', sentence)         for sentence in do_segmentation(string)         for string in list_of_strings]
    # return [re.sub('(&lt;[^&]+&gt;|<[^&]+>)', '', sentence) for string in list_of_strings]
    return re.sub('(&lt;[^&]+&gt;|<[^&]+>)', '', string)


def find_pattern(translations_per_file, pattern, regex=False):
    # print(f"{translations_per_file=}")
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
    df.to_excel(f"{omtprj.split('_',3)[3]}_{rpt_suffix}.xlsx", index=False)


def save_report_instances(instances, omtprj, rpt_suffix):
    
    # create a list of tuples in the desired format
    rows = [(key, value.replace(' ', '<NBSP>')) for key, values in instances.items() for value in values]
    # rows_html = [(key, value.replace(' ', '<b><NBSP></b>')) for key, values in instances.items() for value in values]

    # create a df from the list of tuples
    df = pd.DataFrame(rows, columns=['File', 'Text'])
    
    # export
    # df_html.to_html(open(f"{omtprj.split('_',3)[3]}_{rpt_suffix}.html", 'w'))
    df.to_excel(f"{omtprj.split('_',3)[3]}_{rpt_suffix}.xlsx", index=False)

# 'U kojem bi mjesecu učenici trebali posjetiti park ako žele ići u obilazak \xa0u pratnji vodiča?'
# 'U kojem bi mjesecu učenici trebali posjetiti park ako žele ići u obilazak \xa0u pratnji vodiča?'


if __name__ == "__main__":

    target_lang = get_target_lang(omtprj_path)
    # tm_dpath = os.path.join(omtprj_path, "tm")
    tm_dpath = os.path.join("repos", "pisa_2025ft_translation_common", "assets", "pisa22", target_lang)
    print(f"{tm_dpath=}")
    working_tm_fpath = os.path.join(omtprj_path, "omegat", "project_save.tmx")
    omtprj = os.path.basename(omtprj_path.rstrip("/"))
    
    tm_files = find_files_in_path(tm_dpath)
    # unzip_zipped_files(tm_files)
    translations_per_file = get_translations_per_file(tm_files, target_lang)

    # character to be found
    substr = "\u00A0"

    instances = find_pattern(translations_per_file, substr, False)

    if os.path.isfile(working_tm_fpath):
        working_translations = get_translations(working_tm_fpath, target_lang)
        # working_translations.sort()
        # print([x for x in working_translations if "U kojem" in x])        
    else:
        working_translations = []

    # MS (2024-02-03):
    # this dictionary intends to include correspondences including:
    # - the trend segment where nbsp's were issued (= match)
    # - the TMX file where that trend segment was found (= file)
    # - the entry or entries in the current working TM of the trend transfer projects 
    # where that segment was used and the nbsp's were lost (= entry)
    # This task is very raw, didn't get very far... 
    replacement_map = {}
    for file, matches in instances.items():
        print(f"============== {file=} ==============")
        # input("Press Enter to continue...")
        for segment in set(segmentes):
            for entry in working_translations:
                if "U kojem" in segment and "U kojem" in entry:
                    if segment.replace(substr, ' ').replace('\n', ' ') in strip_tags(entry.replace('\n', ' ')) and len(segment) > 3:
                        print(f"{segment=} found in {entry=}")
                        replacement_map.update({entry: [segment, file]})
                    else:
                        print(f"{segment=} NOT found in {entry=}")

    print("\nMatches in TMs containing no-break space(s):")
    print(instances)

    total_unique_items = len(set(item for lst in instances.values() for item in lst))
    with open('counts_per_language.txt', 'a') as file:
        file.write(f'{target_lang}\t{total_unique_items}\n')

    print("\nNecessary corrections (WIP!!!:")
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
# fine tune where reports are written

# todo:
# replacement_map: trend segments are not always found in the working TM, not sure why
# fix (totally naive approach, would need to be reworked substantially)