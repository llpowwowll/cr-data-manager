﻿'''
replaceData

plugin script for ComicRack to replace field content in the library
based on user-defined conditions
the rules are read from file replaceData.dat, located in the script directory

The CR Data Manager plugin is licensed under the Apache 2.0 software
license, available at: http://www.apache.org/licenses/LICENSE-2.0.html

v 0.1.15

by docdoom

revision history

v 0.1.15
fixed - "do you want to see the log" dialogbox always appears behind the Comicrack Window
        (issue 34) (set ComicRack.Window  as parent window handle for all forms)
change - modular rewriting of forms
change - Contains compares now case insensitive
change - StartsWith compares now case insensitive
change - comparison for equality (==) is now case insensitive
change - comparison for less (<) is now case insensitive
change - comparison for lessEqual (<=) is now case insensitive
change - comparison for greater (>) is now case insensitive
change - comparison for greaterEq (>=) is now case insensitive
change - comparison for not equal (<>) is now case insensitive
fix - missing references to globalvars added
change - PageCount added to allowed keys
change - new modifier ContainsAnyOf
change - new modifier ContainsNot
change - new modifier ContainsAllOf

>> revision history for older releases is at http://code.google.com/p/cr-replace-data/wiki/RevisionLog

issues:
exclude duplicate lines from parsing
marker in books if handled by the dataman (tags or notes?)
todo: modifier Before
todo: modifier After
todo: use In as modifier in keys
     e.g. <<Number.In:1,3,8>>
todo: add RegExp as modifier
todo: simulation instead of actual replacing of data
------------------------------------------------------
'''

import clr
import sys
import re
import System
import System.Text
from System import String
from System.IO import File,  Directory, Path, FileInfo, FileStream
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
from System.Windows.Forms import *
from System.Drawing import *

# this handles unicode encoding:
bodyname = System.Text.Encoding.Default.BodyName
sys.setdefaultencoding(bodyname)

DEBUG__ = True

import globalvars
from utils import *
from mainform import mainForm
from displayResultsForm import displayResultsForm
from aboutForm import aboutForm
from progressForm import progressForm
from configuratorForm import configuratorForm

sys.path.append(globalvars.FOLDER)

allowedKeys = [
	'Series',
	'Volume',
	'Imprint',
	'Publisher',
	'Number',
	'FileDirectory',
	'SeriesGroup',
	'Month',
	'Year',
	'MainCharacterOrTeam',
	'Format',
	'AlternateSeries',
	'Count',
	'FilePath',
	'FileName',
	'Genre',
	'Tags',
	'PageCount'
	]

numericalKeys = [
	'Volume',
	'Month',
	'Year',
	'Count',
	'PageCount'
	]

multiValueKeys = [
	'Tags',
	'Genre'
	]
	
allowedVals = [
	'Series',
	'Volume',
	'Imprint',
	'Publisher',
	'Number',
	'SeriesGroup',
	'MainCharacterOrTeam',
	'Format',
	'AlternateSeries',
	'Count',
	'Genre',
	'Tags'
	]


def writeCode(s, level, linebreak):
	''' 
	writes code to dataMan.tmp
	parameters: 
	s - string to write (str)
	level - indentation level (int)
	linebreak - add linebreak? (bool)
	'''
	s = str(s)
	prefix = '\t' * level
	s = prefix + s
	if linebreak == True: s += '\n'
	try:
		File.AppendAllText(globalvars.TMPFILE, s)
		
	except Exception, err:
		print "Error in function writeCode: ", str(err)

def parsedCode():
	try:
		return File.ReadAllText(globalvars.TMPFILE)
	except Exception, err:
		print "Error in function parsedCode: ", str(err)
		
def parseString(s):
	
	# read a line from replaceData.dat and generate python code from it
	
	myCrit = ''				# this will later contain the left part of the rule
	myNewVal = ''			# this will later contain the new value (right part of rule)
	myModifier = ''			# the modifier (like Contains, Range, Calc etc.)

	
	a = String.split(s,"=>")
	i = len(a[0])
	a[0] = String.Trim(a[0])
	i = len(a[0])
	
	# split the string and retrieve the criteria (left part) and newValues (right part) 
	# store those in lists
	try:		
		criteria = a[0].split(">>")			
		newValues = String.split(a[1],">>")
	except Exception, err:
		print str(err)
	
	# iterate through each of the criteria
	for c in criteria:
		#i = len(c)
		if len(c) > 0:
			c = String.Trim(String.replace(c,"<<",""))
			myKey = ''  # only to reference it
			if String.find(c,':') > 0:
				tmp = String.split(c,":",1)
				tmp2 = String.split(tmp[0],".",1)
				myKey = tmp2[0]
				try:
					myModifier = tmp2[1]
				except Exception, err:
					myModifier = ""
			else:
				File.AppendAllText(globalvars.ERRFILE,"Syntax not valid (invalid field %s)\nline: %s)" % (myKey, s))
				return 0

			if c <> "" and not (myKey in allowedKeys):
				File.AppendAllText(globalvars.ERRFILE,"Syntax not valid (invalid field %s)\nline: %s)" % (myKey, s))
				return 0
			myOperator = "=="
			# handling if modifier is appended to field
			# like Volume.Range:1961, 1963
			try:
				if myModifier <> "":
					if str.lower(myModifier) == "range":
						myOperator = "in range"
					elif str.lower(myModifier) == "not":
						myOperator = "<>"
					elif str.lower(myModifier) == "contains":
						myOperator = ""
					elif str.lower(myModifier) == "greater":
						myOperator = ">"
					elif str.lower(myModifier) == "greatereq":
						myOperator = ">="
					elif str.lower(myModifier) == "less":
						myOperator = "<"
					elif str.lower(myModifier) == "lesseq":
						myOperator = "<="
					elif str.lower(myModifier) == "startswith":
						myOperator = "startswith"
					elif str.lower(myModifier) == "containsanyof":
						myOperator = ""
					elif str.lower(myModifier) == "containsnot":
						pass
					elif str.lower(myModifier) == "containsallof":
						pass
					else:
						File.AppendAllText(globalvars.ERRFILE,"Syntax not valid (invalid modifier %s)\nline: %s)" % (myModifier, s))
						return 0
											
			except Exception, err:
				print "error at parseString: " + str(err)

			myVal = tmp[1]
			myVal = String.replace(myVal,"\"","\\\"")
			
			if myOperator == "in range":
				tmp = String.Split(myVal,",")
				myVal = "%d, %d" % (float(tmp[0]), float(tmp[1]) + 1)
				if myKey in numericalKeys:
					myCrit = myCrit + ("book.%s %s (%s) and " % (myKey, myOperator, myVal))
				else:
					myCrit = myCrit + ("float(book.%s) %s (%s) and " % (myKey, myOperator, myVal))
			# ---------------------------------------------------------------------------
			# now begins the interesting part for field Number which is stored as 
			# a string but treated as a numerical value
			elif myOperator in ('==', '>', '>=', '<', '<=') and myKey == 'Number':
				if str.Trim(myVal) == '':
					# fix issue 31
					myCrit = myCrit + ('str(book.Number) %s \'\' and ' % (myOperator))
					print myCrit
				else:
					# if the current value of book.Number is Null it has to be converted to
					# 0 before it can be converted to float
					myCrit = myCrit + ('float(nullToZero(book.Number)) %s float(%s) and ' % (myOperator, myVal))
				print myCrit
			# end of extra handling of Number field
			# ----------------------------------------------------------------------------
			elif str.lower(myModifier) == "contains" and myKey not in numericalKeys:
				myCrit = myCrit + 'comp.contains(book.%s,\"%s\",COMPARE_CASE_INSENSITIVE) == True and ' % (myKey, myVal)
				#MessageBox.Show(myCrit)
				#myCrit = myCrit + ("comp.contains
				# myCrit = myCrit + ("String.find(book.%s,\"%s\") >= 0 and " % (myKey,myVal)) 
			elif str.lower(myModifier) == "containsanyof": # and myKey not in numericalKeys:
				if myKey not in numericalKeys:
					myCrit = myCrit + 'comp.containsAnyOf(book.%s,\"%s\",COMPARE_CASE_INSENSITIVE) == True and ' % (myKey, myVal)
				else:
					File.AppendAllText(globalvars.ERRFILE, "Syntax not valid\nline: %s)\n" % (s))
					File.AppendAllText(globalvars.ERRFILE, "ContainsAnyOf modifier cannot be used in %s field" % (myKey))
					return 0
			elif str.lower(myModifier) == "containsallof": # and myKey not in numericalKeys:
				if myKey not in numericalKeys:
					myCrit = myCrit + 'comp.containsAllOf(book.%s,\"%s\",COMPARE_CASE_INSENSITIVE) == True and ' % (myKey, myVal)
				else:
					File.AppendAllText(globalvars.ERRFILE, "Syntax not valid\nline: %s)\n" % (s))
					File.AppendAllText(globalvars.ERRFILE, "ContainsAllOf modifier cannot be used in %s field" % (myKey))
					return 0

			elif str.lower(myModifier) == "containsnot":
				if myKey not in numericalKeys:
					myCrit = myCrit + 'comp.containsNot(book.%s,\"%s\",COMPARE_CASE_INSENSITIVE) == True and ' % (myKey, myVal)
				else:
					File.AppendAllText(globalvars.ERRFILE, "Syntax not valid\nline: %s)\n" % (s))
					File.AppendAllText(globalvars.ERRFILE, "ContainsNot modifier cannot be used in %s field" % (myKey))
					return 0															
			elif myOperator == "startswith" and myKey not in numericalKeys:
				myCrit = myCrit + ("comp.startsWith(book.%s,\"%s\", COMPARE_CASE_INSENSITIVE) and " % (myKey,myVal))
				#myCrit = myCrit + ("book.%s.startswith(\"%s\") and " % (myKey,myVal))
			elif myOperator == '==' and myKey not in numericalKeys:
				myCrit = myCrit + "comp.equals(book.%s,\"%s\", COMPARE_CASE_INSENSITIVE) and " % (myKey,myVal)
			elif myOperator == '<' and myKey not in numericalKeys:
				myCrit = myCrit + "comp.less(book.%s,\"%s\", COMPARE_CASE_INSENSITIVE) and " % (myKey, myVal)
			elif myOperator == '<=' and myKey not in numericalKeys:
				myCrit = myCrit + "comp.lessEq(book.%s,\"%s\", COMPARE_CASE_INSENSITIVE) and " % (myKey, myVal)
			elif myOperator == '>' and myKey not in numericalKeys:
				myCrit = myCrit + "comp.greater(book.%s,\"%s\", COMPARE_CASE_INSENSITIVE) and " % (myKey, myVal)
			elif myOperator == '>=' and myKey not in numericalKeys:
				myCrit = myCrit + "comp.greaterEq(book.%s,\"%s\", COMPARE_CASE_INSENSITIVE) and " % (myKey, myVal)
			elif myOperator == '<>' and myKey not in numericalKeys:
				myCrit = myCrit + "comp.notEq(book.%s,\"%s\", COMPARE_CASE_INSENSITIVE) and " % (myKey, myVal)
			else:
				# numerical values in CR are -1 if Null
				if myKey in numericalKeys and str.Trim(myVal) == '':
					myVal = -1
				myCrit = myCrit + ("str(book.%s) %s \"%s\" and " % (myKey, myOperator, myVal))
				
			
	myCrit = "if " + String.rstrip(myCrit, " and") + ":"
	writeCode(myCrit,1,True)
	writeCode("f.write(book.Series.encode('utf-8') + ' v' + str(book.Volume) + ' #' + book.Number + ' was touched \\t(%s)\\n')" % a[0], 2, True)
	
	# iterate through each of the newValues
	for n in newValues:
		if len(n) > 0:
			n = String.Trim(String.replace(n,"<<",""))
			if String.find(n,':') > 0:
				tmp = String.split(n,":",1)
				tmp2 = tmp[0]
				myKey = tmp2
				myModifier = ''
				if String.find(tmp2,'.') > 0:
					tmp3 = String.split(tmp2,'.')
					myKey = tmp3[0]
					myModifier = tmp3[1]
			else:
				File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)" % (myKey, s))			
				return 0
			if not (myKey in allowedVals):
				File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)" % (myKey, s))
				return 0
			# to do: handling if function is appended to field
				
			myVal = tmp[1]
			
			writeCode("myOldVal = str(book.%s)" % myKey, 2, True)

			if myModifier <> "":
				if str.lower(myModifier) == "calc":
					if myKey not in numericalKeys and myKey <> 'Number':
						myVal = String.replace(myVal,'{','str(book.')
					else:
						myVal = String.replace(myVal,'{','int(book.')
					myVal = String.replace(myVal,'}',')')
					if myKey == 'Number':
						writeCode("book.%s = str(%s)" % (myKey, myVal), 2, True)
					else:
						writeCode("book.%s = %s" % (myKey, myVal), 2, True)
				if str.lower(myModifier) == "add":
					if myKey in numericalKeys or myKey == 'Number':
						File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)\n" % (myKey, s))
						File.AppendAllText(globalvars.ERRFILE, "Add modifier cannot be used in %s field" % (myKey))
						return 0
					elif myKey in multiValueKeys:
						if len(String.Trim(myVal)) == 0:
							File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)\n" % (myKey, s))
							File.AppendAllText(globalvars.ERRFILE, "Remove modifier needs 1 argument")
							return 0
						else:
							writeCode('book.%s = multiValueAdd(book.%s,"%s")' % (myKey, myKey, myVal), 2, True)
				if str.lower(myModifier) == "replace":
					if myKey in numericalKeys or myKey == 'Number':
						File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)\n" % (myKey, s))
						File.AppendAllText(globalvars.ERRFILE, "Replace modifier cannot be used in %s field" % (myKey))
						return 0
					elif myKey in multiValueKeys:
						tmpVal = myVal.split(',')
						if len(tmpVal) > 1:
							writeCode ('book.%s = multiValueReplace(book.%s,"%s","%s")' % (myKey, myKey, tmpVal[0], tmpVal[1]), 2, True)
						else:
							File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)\n" % (myKey, s))
							File.AppendAllText(globalvars.ERRFILE, "Replace modifier needs 2 arguments")
							return 0
				if str.lower(myModifier) == "remove":
					if myKey in numericalKeys or myKey == 'Number':
						File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)\n" % (myKey, s))
						File.AppendAllText(globalvars.ERRFILE, "Remove modifier cannot be used in %s field" % (myKey))
						return 0
					elif myKey in multiValueKeys:
						if len(String.Trim(myVal)) == 0:
							File.AppendAllText(globalvars.ERRFILE, "Syntax not valid (invalid field %s)\nline: %s)\n" % (myKey, s))
							File.AppendAllText(globalvars.ERRFILE, "Remove modifier needs 1 argument")
							return 0
						else:
							writeCode('book.%s = multiValueRemove(book.%s,"%s\")' % (myKey, myKey, myVal), 2, True)

			else:

				if myKey in numericalKeys:
					if len(myVal) == 0:
						writeCode("book.%s = \'\'\n" % (myKey), 2, True)
					else:
						writeCode("book.%s = %s\n" % (myKey, myVal), 2, True)
				else:
					writeCode("book.%s = \"%s\"" % (myKey, myVal), 2, True)
				myNewVal = myNewVal + ("\t\tbook.%s = \"%s\"" % (myKey, myVal)) 

			writeCode("myNewVal = str(book.%s)" % myKey, 2, True)
			writeCode("if myNewVal <> myOldVal:", 2, True)	
			writeCode("f.write('\\tbook.%s - old value: ' + myOldVal.encode('utf-8') + '\\n')" % (myKey), 3, True)
			writeCode("f.write('\\tbook.%s - new value: ' + myNewVal.encode('utf-8') + '\\n')" % (myKey), 3, True)
			writeCode('book.Tags = multiValueAdd(book.Tags,"DMProc")', 3, True)
			writeCode("else:", 2, True)
			writeCode("f.write('\\t%s - old value was same as new value\\n')" % (myKey), 3, True)
	return -1
	

def dmConfig():

	form = configuratorForm()
	form.setFile(globalvars.DATFILE)
	form.setTitle('Data Manager Configurator')
	form.ShowDialog(ComicRack.MainWindow)
	form.Dispose()


#@Name	Data Manager
#@Image dataMan16.png
#@Hook	Books

def replaceData(books):

	ERROR_LEVEL = 0

	form = mainForm()
	form.ShowDialog(ComicRack.MainWindow)
	form.Dispose()

	if form.DialogResult == DialogResult.No:
		dmConfig()
		return
	elif form.DialogResult <> DialogResult.OK:
		return
	else:
		pass
	
	try:
		File.Delete(globalvars.TMPFILE)
		File.Delete(globalvars.ERRFILE)
	except Exception, err:
		pass
	
	# check if configuration exists
	if not File.Exists(globalvars.DATFILE):
		MessageBox.Show('Please use the Data Manager Configurator first!','Data Manager %s' % globalvars.VERSION)
		return

	# check if configuration has been saved once
	if not File.Exists(globalvars.CHKFILE):
		MessageBox.Show('Please save your configuration first!','Data Manager %s' % globalvars.VERSION)
		return

	writeCode('try:', 0, True)
	
	progBar = progressForm()
	progBar.Show()
	writeCode('from globalvars import *',1,True)
	writeCode('from utils import *',1,True)
	writeCode('comp = comparer()',1,True)
	try:
		s = File.ReadAllLines(globalvars.DATFILE)
		i = 0
		for line in s:
			i += 1
			if String.find(line," => ") and line[0] <> "#":
				if not parseString(line):
					error_message = File.ReadAllText(globalvars.ERRFILE)
					MessageBox.Show("Error in line %d!\n%s" % (i, str(error_message)),"CR Data Manager %s - Parse error" % globalvars.VERSION)
					ERROR_LEVEL = 1
			
	except Exception, err:
		print 'getCode: ', str(err)

	progBar.Dispose()

	writeCode('except Exception,err:', 0, True)
	writeCode('print (\"Error in code generation: %s\" % str(err))', 1, True)
	
	if ERROR_LEVEL == 0:
		theCode = parsedCode()	# read generated code from file
		if DEBUG__:
			print "code generated by CR Data Manager: \n%s" % theCode   # remove in first stable release!
			
		progBar = progressForm()
		progBar.Show()
		progBar.setMax(books.Length)
		touched = 0
		f=open(globalvars.LOGFILE, "w")	# open logfile
		for book in books:
			touched += 1
			progBar.setValue(touched)
			try:
				exec (theCode)
				
			except Exception, err:
				MessageBox.Show('Error while executing the rules. \n%s\nPlease check your rules.' % str(err), 'Data Manager - Version %s' % globalvars.VERSION)
				ERROR_LEVEL = 1
		
		f.close()				# close logfile

		progBar.Dispose()
		
		if ERROR_LEVEL == 0:
			msg = "Finished. I've inspected %d books.\nDo you want to take look at the log file?" % (touched)
	
			form = displayResultsForm()
			form.configure(msg)
			form.ShowDialog(ComicRack.MainWindow)
			form.Dispose()

			if form.DialogResult == DialogResult.Yes:
	
				form = configuratorForm()
				form.setFile(globalvars.LOGFILE)
				form.setTitle('Data Manager Logfile')
				form.ShowDialog(ComicRack.MainWindow)
				form.Dispose()

	try:
		#File.Delete(TMPFILE)
		File.Delete(globalvars.ERRFILE)
	except Exception, err:
		pass
	

