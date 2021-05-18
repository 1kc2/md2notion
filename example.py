from os import listdir
from os.path import isfile, join
from notion.client import NotionClient
from notion.block import PageBlock
from md2notion.upload import uploadBlock, convert
from md2notion.NotionPyRenderer import addHtmlImgTagExtension, addLatexExtension

from custom.md2notion import convert, CustomNotionPyRenderer

# Obtain the `token_v2` value by inspecting your browser cookies on a logged-in session on Notion.so
client = NotionClient(token_v2="{{ YOUR TOKEN_V2 }}")

client.get_top_level_pages()

page = client.get_block('{{ URL TO THE NOTION PAGE }}')

# This may need to be the absolute path
folder_name = '{{ PATH TO FOLDER CONTAINING MARKDOWN FILES }}'

onlyfiles = [join(folder_name, f) for f in listdir(folder_name) if isfile(join(folder_name, f)) and f.endswith(".md")]

for file in onlyfiles:
    with open(file, "r", encoding="utf-8") as mdFile:
        newPage = page.children.add_new(PageBlock, title=mdFile.name)
        rendered = convert(mdFile, addHtmlImgTagExtension(addLatexExtension(CustomNotionPyRenderer)))
        for blockDescriptor in rendered:
            print(blockDescriptor)
            uploadBlock(blockDescriptor, newPage, mdFile.name)