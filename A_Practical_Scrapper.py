#!/usr/bin/env python 
import subprocess
import feedparser
import re
import os
import sys
import urllib2
import argparse

verboseprint = lambda *a: None 

def Icreator( num ):
   string = ""
   for i in range( 0, num ):
      string += "I"
   return string

def stripper( basename, filename ):
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
   pageId = 1
   feed = feedparser.parse( baseurl + str( pageId ))
   done = False
   print( "Finding Start of Books" )
   while ( not done ):
      verboseprint("Searching RSS Page " + str( pageId ))
      for item in feed.entries:
         if "Prologue" in item.title:
            pageIds.append( pageId )
      pageId += 1
      feed = feedparser.parse( baseurl + str( pageId ))
      if len(pageIds) == 3:
         done = True
   verboseprint( 'Books start at: %s' %pageIds )
   return pageIds

def grabRSS( book ):
   baseurl = "https://practicalguidetoevil.wordpress.com/feed/?paged="
   pageIds = findBaseRSS( baseurl )
   chapters = []
   add = 0
   if( book == 1 ):
      for pageId in range( pageIds[1], pageIds[2] + 1 ):
         feed = feedparser.parse( baseurl + str( pageId ))
         for entry in feed.entries:
            if 'Epilogue' in entry.title:  add = 1
            if add == 1:  chapters.append( entry )
            if 'Prologue' in entry.title:  add = 0
   if( book == 2 ):
      for pageId in range( pageIds[0], pageIds[1] + 1 ):
         feed = feedparser.parse( baseurl + str( pageId ))
         for entry in feed.entries:
            if 'Epilogue' in entry.title and add == 0:  add = 1
            if add == 1:  chapters.append( entry )
            if 'Prologue' in entry.title and add == 1:  add = 2
   if( book == 3):
      add = 1
      for pageId in range( 0, pageIds[0] + 1 ):
         feed = feedparser.parse( baseurl + str( pageId ))
         for entry in feed.entries:
            if add == 1:  chapters.append( entry )
            if 'Prologue' in entry.title:  add = 0
   chapters.reverse()
   for c in chapters: c.title = c.title.encode('ASCII', 'ignore')
   getHTMLs( chapters )
   return chapters
   
def getHTMLs( chapters ):
   if not os.path.exists( directory): os.makedirs(directory)
   for chapter in chapters:
      page = urllib2.urlopen( chapter.link )
      data = page.read()
      fileTitle = directory + chapter.title + ".html"

      with open( fileTitle, "w" ) as htmlFile:
         htmlFile.write(data)
      verboseprint( fileTitle + " Written")

def massProcess( chapters ):
   temps = []
   for chapter in chapters:
      filename = directory + chapter.title + ".html"
      basename = chapter.title
      stripper( basename, filename ) 
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
   if args.individual:
      for chapter in chapters:
         filename = directory + chapter.title + ".html"
         basename = directory + chapter.title
         stripper( basename, filename )   
         if( os.path.exists( basename + '.docx' ) == False or 
            args.force ):
            cmd = [ 'pandoc', '-o', basename + '.docx', filename ]
            subprocess.call( cmd )
            verboseprint( basename + '.docx' + " Converted" )
         else:
            verboseprint( basename + '.docx' + " Exists" )
   else:
      massProcess( chapters )
      verboseprint( "Converted Book " + str(book) + " into Book.docx")
      createEpub( book )

def createEpub( book ):
   cmd = [ 'pandoc', '-o', "Book.html", 'Book.docx' ]
   verboseprint( cmd )
   subprocess.call( cmd )
   verboseprint( "Converted Book.docx into Book.html" )
   cmd = [ 'pandoc', '-o', "Book.md", 'Book.html', '--parse-raw' ]
   verboseprint( cmd )
   subprocess.call( cmd )
   verboseprint( "Converted Book.html into Book.md" )
   
   data = "---\n"
   data += "title:\n"
   data += "- type: main\n"
   data += "  text: A Pracitcal Guide To Evil\n"
   data += "- type: subtitle\n"
   data += "  text: Book " + Icreator( book ) + "\n"
   data += "author: David Verburg\n"
   data += "language: en-UK\n"
   data += "..."
  
   with open("title.txt", "w") as meta:
      meta.write(data)
   title = "Book_" + Icreator( book ) + ".epub"
   cmd = [ 'pandoc', '-S', '-o', title, 'title.txt', 'Book.md' ]
   verboseprint( cmd )
   subprocess.call( cmd )
   print( "Converted Book " + str(book) + " into " + title )

def cleanup( chapters ):
   verboseprint( "Cleaning Up")
   for chapter in chapters:
      filename = directory + chapter.title + ".html"
      os.remove( filename )
   if not args.leave and not args.individual:
      os.remove( "Book.docx")
   if not args.individual:
      os.remove( "title.txt")
      os.remove( "Book.md")
      os.remove( "Book.html")
      os.rmdir( directory )

def main():
   book = input( 'Which book do you want (1/2/3/)? ' )
   con = ""
   if book is 3: 
      con = raw_input( 'Warning: book 3 is experimental. Continue (y/n)? ')
   if con == 'n': exit(0)
   chapters = grabRSS( book )
   processAndConvert( book, chapters )
   cleanup( chapters )
   
   


parser = argparse.ArgumentParser(description='Strips and converts A Practical Guide To Evil from Wordpress into docx.')
parser.add_argument('-v', '--verbose', action='store_true',
                     help='Print information on progress')
parser.add_argument('-f', '--force', action='store_true',
                     help='Force conversion even if file already exists')
parser.add_argument('-l', '--leave', action='store_true',
                     help='Leaves Book.docx file after conversion')
parser.add_argument('-i', '--individual', action='store_true',
                     help='Converts each chapter into a seperate docx file')
args = parser.parse_args()
if args.individual and args.leave:
   print( "Cannot have both -l and -i as flags" )
   exit(1)

directory = "./Chapters/"
if( args.verbose ):
   def verboseprint( *args ): 
      for arg in args: print( arg )

main()
		

