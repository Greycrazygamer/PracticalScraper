#!/usr/bin/env python 
import subprocess
import re
import os
import sys
import time
import urllib2
import argparse
from multiprocessing import Pool

try:
        import feedparser
except:
        print( "ERROR: feedparser not install\n Run 'pip install feedparser'" )
        exit(0)

verboseprint = lambda *a: None 

parser = argparse.ArgumentParser(description='Strips and converts A Practical Guide To Evil from Wordpress into epub and docx.')
parser.add_argument('-v', '--verbose', action='store_true',
                     help='Print information on progress')
parser.add_argument('-l', '--leave', action='store_true',
                     help='Leaves Book.docx file after conversion')
args = parser.parse_args()

directory = "./.Chapters/"
numOfBooks = 4

if( args.verbose ):
   def verboseprint( *args ): 
      for arg in args: print( arg )


def Icreator( num ):
   string = ""
   for i in range( 0, num ):
      string += "I"
   return string

def stripper( chapter ):
   filename = directory + chapter.title + ".html"
   basename = chapter.title
   tempfile = basename + ".tmp"
   with open( filename, 'r') as src, open( tempfile, "w") as dest:
      delete = False
      for line in src:
         if 'wpcnt' in line:
            delete = True
         if 'masthead' in line:
            delete = True
         if '<a ' in line:
            delete = True
         if 'class=\"entry-meta\"' in line:
            delete = True
         if delete == False:
            dest.write(line)
         if '- .entry-meta' in line:
            delete = False
         if '#masthead' in line:
            delete = False

   with open(tempfile, "r") as readFile:
      lines = readFile.readlines()
   with open(tempfile,'w') as writeFile:
      writeFile.writelines([item for item in lines[:-3]])
      writeFile.write("</article>\n" + "</script>\n" + "</body>\n" + "</html>")
   verboseprint( filename + " Stripped" )
   os.remove( filename )
   os.rename( tempfile, filename )

def findBaseRSS( baseurl ):
   pageIds = []
   dates = []
   pageId = 1
   feed = feedparser.parse( baseurl + str( pageId ))
   done = False
   print( "Finding Start of Books" )
   while ( not done ):
      verboseprint("Searching RSS Page " + str( pageId ))
      for item in feed.entries:
         if "Prologue" in item.title:
            pageIds.append( pageId )
            dates.append(item.published_parsed)
      pageId += 1
      feed = feedparser.parse( baseurl + str( pageId ))
      if len(pageIds) == numOfBooks:
         done = True
   pageIds.reverse()
   dates.reverse()
   print "Found Start of Books "
   verboseprint( '%s' %pageIds )
   return pageIds, dates

def grabRSS( book ):
   baseurl = "https://practicalguidetoevil.wordpress.com/feed/?paged="
   pageIds, prologue_dates = findBaseRSS( baseurl )
   chapters = []
   stop = False
   for pageId in range( pageIds[book-1]+1, pageIds[book]-1, -1 ):
      feed = feedparser.parse( baseurl + str( pageId ))
      
      for entry in reversed(feed.entries):
         if entry.published_parsed == prologue_dates[book]:
            stop = True
         if not stop:
            chapters.append( entry )
   for c in chapters: c.title = c.title.encode('ASCII', 'ignore')
   if chapters[0].title == 'Summary': 
      chapters = chapters[1:]
   while chapters[0].title != 'Prologue':
      verboseprint ("Removing " + chapters[0].title)
      chapters = chapters[1:]
      
   getHTMLs( chapters )
   return chapters

def getHTML( chapter ):
   page = urllib2.urlopen( chapter.link )
   data = page.read()
   fileTitle = directory + chapter.title + ".html"

   with open( fileTitle, "w" ) as htmlFile:
      htmlFile.write(data)
   verboseprint( fileTitle + " Written")
    
def getHTMLs( chapters ):
   if not os.path.exists( directory ): os.makedirs( directory )
   p = Pool( 4 )
   p.map( getHTML, chapters )

def processChapters( chapters ):
   print "Processing Chapters"
   temps = []
   p = Pool( 4 )
   p.map( stripper, chapters )
   
   for chapter in chapters:
      filename = directory + chapter.title + ".html"
      temps.append( filename )
   
   cmd = [ 'pandoc', '-s' ]
   cmd.extend( temps )
   cmd.append( '-o' )
   cmd.append( 'Book.docx' )
   verboseprint( cmd )
   try:
      subprocess.call( cmd )
   except:
      print( "pandoc failed... Is pandoc installed?")
      print( "Linux: \"apt-get install pandoc\"")
      print( "MacOS: \"brew install pandoc\"")
      exit(0)
   

def processAndConvert( book, chapters ):
   processChapters( chapters )
   verboseprint( "Converted Book " + str(book) + " into Book.docx")
   createEpub( book )

def createEpub( book ):
   cmd = [ 'pandoc', '-s', 'Book.docx', '-t', 'markdown', '-o', 'Book.md' ]
   verboseprint( cmd )
   subprocess.call( cmd )
   verboseprint( "Converted Book.docx into Book.md" )
   
   data = "---\n"
   data += "title:\n"
   data += "- type: main\n"
   data += "  text: A Pracitcal Guide To Evil Book " + Icreator( book ) + "\n"
   data += "- type: subtitle\n"
   data += "  text: Book " + Icreator( book ) + "\n" 
   data += "author: David Verburg\n"
   data += "language: en-UK\n"
   data += "..."
  
   with open("title.txt", "w") as meta:
      meta.write(data)
   title = "A_Practical_Guide_To_Evil_Book_" + Icreator( book )
   cmd = [ 'pandoc', '-o', title + ".epub", 'title.txt', 'Book.md' ]
   verboseprint( cmd )
   subprocess.call( cmd )
   cmd = [ 'ebook-convert', title + ".epub",  title + ".mobi" ]
   verboseprint( cmd )
   try:
      subprocess.call( cmd )
   except:
      print( "ebook-convert failed... Is calibre installed?")
      print( "Linux: \"apt-get install calibre\"")
      print( "MacOS: \"brew cask install calibre\"")
   
   print( "Saved Book " + str(book) + " as " + title )

def cleanup( chapters ):
   verboseprint( "Cleaning Up")
   for chapter in chapters:
      filename = directory + chapter.title + ".html"
      os.remove( filename )
   if not args.leave:
      os.remove( "Book.docx")
   os.remove( "title.txt")
   os.remove( "Book.md")
   os.rmdir( directory )

def main():
   book = input( 'Which book do you want (1/2/3/4)? ' )
   if book is 4: 
      print "Book 4 is not finished"
      exit(0)
   chapters = grabRSS( book )
   processAndConvert( book, chapters )
   cleanup( chapters )
   
   

main()
                

