#!/usr/bin/env python3
import subprocess
import io
import os
import sys
import argparse
from itertools import chain
import concurrent.futures
import pstats
import cProfile
import requests
from pip._internal import main as pipmain


def profile(func):
    def wrapper(*fargs, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        retval = func(*fargs, **kwargs)
        pr.disable()
        s = io.StringIO()
        sortby = "cumulative"
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        return retval

    return wrapper


# Auto installs feedparser
try:
    import feedparser
except:
    pipmain(["install", "--user", "feedparser"])

verboseprint = lambda *a: None
parser = argparse.ArgumentParser(
    description="Strips and converts A Practical Guide To Evil from Wordpress into epub and mobi."
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="Print information on progress"
)
parser.add_argument(
    "-l",
    "--leave",
    action="store_true",
    help="Doesn't cleanup intermideate HTML Chapters, Book files after conversion",
)
args = parser.parse_args()

# GLOBAL VARS
directory = "./.Chapters/"
NUM_OF_BOOKS = 6
# Max rss page to look for... threads end up wasting 0.001s looking at invalid urls
MAX_RSS_ID = 100

if args.verbose:

    def verboseprint(*fargs):
        for arg in fargs:
            print(arg)


def setup_dependencies():
    pandoc_cmd = ["pandoc", "-v"]
    calibre_cmd = ["ebook-convert", "--version"]

    pandoc_error = (
        "pandoc failed... Is pandoc installed?\n"
        'Linux: "apt-get install pandoc"\n'
        'MacOS: "brew install pandoc"\n'
    )
    calibre_error = (
        "ebook-convert failed... Is calibre installed?\n"
        'Linux: "apt-get install calibre"\n'
        'MacOS: "brew cask install calibre"\n'
    )
    fail = False
    try:
        res = subprocess.check_output(pandoc_cmd)
    except:

        print("Attempting to install pandoc")
        try:
            if sys.platform == "darwin":
                cmd = ["brew", "install", "pandoc"]
                subprocess.call(cmd)
            elif sys.platform.startswith("linux"):
                cmd = ["apt-get", "install", "pandoc"]
                subprocess.call(cmd)
            else:
                res = subprocess.check_output(pandoc_cmd)
        except:
            fail = True
            print(pandoc_error)

    try:
        res = subprocess.check_output(calibre_cmd)
    except:
        print("Attempting to install calibre")
        try:
            if sys.platform == "darwin":
                cmd = ["brew", "cask", "install", "calibre"]
                subprocess.call(cmd)
            elif sys.platform.startswith("linux"):
                cmd = ["apt-get", "install", "calibre"]
                subprocess.call(cmd)
            else:
                res = subprocess.check_output(calibre_cmd)
        except:
            fail = True
            print(calibre_error)
    if fail:
        sys.exit(1)


def Icreator(num):
    ones = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
    tens = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX"]
    string = ones[num % 10]
    num = num // 10
    if num != 0:
        string = tens[num % 10] + string
    return string


def injectTitle(chapter):
    staticHTML = "<!DOCTYPE html>\n" '<html lang="en">\n' '<meta charset="UTF-8">\n'
    titleHTML = (
        staticHTML + "\n<header>\n\t<h1>" + chapter.title + "</h1>\n</header>\n<body>"
    )
    chapter.content[0].value = titleHTML + chapter.content[0].value
    chapter.content[0].value += "\n</body>\n"


def grabRssPageEntries(page):
    request = requests.get(page[0])
    # Pull out all entries if the page is RSS, otherwise return empty
    if request.status_code == 200:
        feed = feedparser.parse(request.text)
        verboseprint("Finished parsing %d" % page[1])
        return feed.entries
    else:
        return []


# Grab all rss pages pool out the work. Filter the empty results and return a single list
# of entries sorted by publication date
def grabRssPages(baseurl):
    rssPages = [(baseurl + str(i), i) for i in range(1, MAX_RSS_ID)]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Convert the results iterable to a list
        results = [*executor.map(grabRssPageEntries, rssPages)]
    # Filter out empty lists
    results = filter(None, results)
    # Merge lists into single list
    flat = chain.from_iterable(results)
    result = list(flat)
    # Sort entries by date
    result.sort(key=lambda entry: entry.published_parsed)
    return result


def writeHTML(chapter):
    fileTitle = directory + chapter.title + ".html"
    injectTitle(chapter)
    with open(fileTitle, "w") as htmlFile:
        htmlFile.write(chapter.content[0].value)
    verboseprint(fileTitle + " Written")


def writeHTMLs(chapters):
    if not os.path.exists(directory):
        os.makedirs(directory)
    for c in chapters:
        writeHTML(c)


def grabBook(book, rssEntries):
    chapters = []
    currentBook = 0
    for entry in rssEntries:
        if entry.title == "Prologue":
            currentBook += 1
        if currentBook == book:
            chapters.append(entry)
    writeHTMLs(chapters)
    return [chapter.title for chapter in chapters]


def processChapters(book, chapters):
    print("Processing Book %d Chapters" % book)
    temps = []
    for chapter in chapters:
        filename = directory + chapter + ".html"
        temps.append(filename)

    cmd = ["pandoc", "-s"]
    cmd.extend(temps)
    cmd.append("-o")
    cmd.append("Book.docx")
    verboseprint(cmd)
    try:
        subprocess.call(cmd)
    except:
        print("pandoc failed... Is pandoc installed?")
        print('Linux: "apt-get install pandoc"')
        print('MacOS: "brew install pandoc"')
        sys.exit(0)


def createEpub(book):
    cmd = ["pandoc", "-s", "Book.docx", "-t", "markdown", "-o", "Book.md"]
    verboseprint(cmd)
    subprocess.call(cmd)
    verboseprint("Converted Book.docx into Book.md")

    data = "---\n"
    data += "title:\n"
    data += "- type: main\n"
    data += "  text: A Practical Guide To Evil Book " + Icreator(book) + "\n"
    data += "author: David Verburg\n"
    data += "language: en-UK\n"
    data += "..."

    with open("title.txt", "w") as meta:
        meta.write(data)
    title = "A_Practical_Guide_To_Evil_Book_" + Icreator(book)
    cmd = ["pandoc", "-o", title + ".epub", "title.txt", "Book.md"]
    verboseprint(cmd)
    subprocess.call(cmd)
    cmd = ["ebook-convert", title + ".epub", title + ".mobi"]
    verboseprint(cmd)
    try:
        subprocess.call(cmd)
    except:
        print("ebook-convert failed... Is calibre installed?")
        print('Linux: "apt-get install calibre"')
        print('MacOS: "brew cask install calibre"')

    print(("Saved Book " + str(book) + " as " + title))


def processAndConvert(book, chapters):
    # It is faster to convert HTML Chapters-> Book.docx -> Book.md
    # than converting directly to Markdown
    processChapters(book, chapters)
    verboseprint("Converted Book " + str(book) + " into Book.md")
    createEpub(book)


def cleanup(chapters):
    if args.leave:
        return
    verboseprint("Cleaning Up")
    for chapter in chapters:
        filename = directory + chapter + ".html"
        os.remove(filename)
    os.rmdir(directory)
    os.remove("title.txt")
    os.remove("Book.md")


def inputChoice():
    books = []
    choice = ""
    while len(choice) == 0:
        print("[1-6] Get Book #")
        print("[a]   Get All Books")
        print("[q]   Quit")
        choice = input("Which book do you want? ")
        if choice.isdigit() and int(choice) <= NUM_OF_BOOKS:
            books = [int(choice)]
            if int(choice) is NUM_OF_BOOKS:
                print("Book %s is incomplete, grabbing all avaliable chapters" % choice)
            else:
                print("Making book %s" % choice)
        elif choice == "a":
            books = list(range(1, NUM_OF_BOOKS + 1))
            print("Making all books")
        elif choice in ["q", "e"]:
            continue
        else:
            print("Book", choice, "does not exist")
            choice = ""
    return books


def main():
    setup_dependencies()
    books = inputChoice()
    if len(books) == 0:
        return
    baseurl = "https://practicalguidetoevil.wordpress.com/feed/?paged="
    # Each entry is a RSS meta + chapter text
    rssEntries = grabRssPages(baseurl)
    for b in books:
        chapterTitles = grabBook(b, rssEntries)
        processAndConvert(b, chapterTitles)
        cleanup(chapterTitles)


if __name__ == "__main__":
    main()
