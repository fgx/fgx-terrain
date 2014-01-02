#!/usr/bin/env python
# -*- coding: utf-8 -*-
#                                                                                    
#                                                  _                                 
#                                  __             /:\    O   _                       
#                                 /::\         __/:/  _ O  ,':\                      
#                                 |:/        ,'::_|  /_\__/:,'                       
#                             O  /_/      _,'::,' \\   |::,'                         
#                                        /_::,'       /__/                           
#                                          |/   ,-'\__                               
#                                          |_,-':::::_\             _ O              
#         _/                        /  O  _|:::::_::/              /:\               
#        /_/                        \    /::::::/ \/                \  _             
#       O            /\                  |:::::/                 _ O ,':\            
#                   /_|          /\    ,':::::/   /\         /\,':\ /:::|            
#                     \      /\ //    /::::::/               \___/ /,--''           
#                              /|     |:::::|     /\  /            \                 
#                          /  /__\    `--.::/    O   /|                              
#                      /\ //              \/         \/  O     O                     
#                                                                                    
#                                                                                                      
#   creaty_reliefs.py to create reliefs with SRTM-3 data and merged DEMs in          
#   tilesizes i.e. 5x5, see note below!*                                             
#                                                                                    
#   (c) 2012-2014, Yves Sablonier, yves.at.sablonier.ch                                   
#                                                                                    
#   This program is free software; you can redistribute it and/or                    
#   modify it under the terms of the GNU General Public License                      
#   as published by the Free Software Foundation; either version 2                   
#   of the License, or (at your option) any later version.                           
#                                                                                    
#   This program is distributed in the hope that it will be useful,                  
#   but WITHOUT ANY WARRANTY; without even the implied warranty of                   
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                    
#   GNU General Public License for more details.                                     
#                                                                                    
#                                                                                       
#   Requirements:                                                                    
#
#   gdal full >= 1.9.x                                                               
#   ImageMagick >= 6.7.9                                                             
#   Python >= 2.6.6                                                                  
#                                                                                    
#   * Please note: This script is far from nice and efficient code and               
#   is not consolidated. It runs on a machine dedicated to create reliefs            
#   only. One relief with 25 hgt files takes about 2-3 minutes on a faster           
#   machine. You will encounter a lot of warnings, mostly because                    
#   Imagemagick doesn't handle geotiff tags well. Please ignore ;-)    
#
#   Dev-Notes
#   ---------
#	SRTM-1 variant: Setting resolution to 18001 pixel instead of 6001
#   needs a parameter once, see line 333 etc.                 

import sys, subprocess, os

# different gdal versions using different import
try:
    from osgeo import gdal
except ImportError:
    import gdal
	
from optparse import OptionParser

##======================================================================
## Parse Options
usage = "usage: create_reliefs.py  -i <hgtinputdir> -t <tempdir> -t <reliefdir> -m <mergedir> "

parser = OptionParser(usage=usage)

parser.add_option("-i",  nargs=1, action="store", dest="hgtdir", help="hgt input dir" )
parser.add_option("-t",  nargs=1, action="store", dest="tempdir", help="temp dir" )

parser.add_option("-r",  nargs=1, action="store", dest="reliefdir", help="relief dir" )
parser.add_option("-m",  nargs=1, action="store", dest="mergedir", help="merge dir" )
(opts, args) = parser.parse_args()

print opts, args
if opts.hgtdir == None or opts.tempdir == None or opts.reliefdir == None or opts.mergedir == None:
	print "FATAL: arguments missing"
	parser.print_help()
	sys.exit(1)

try:
	if not os.path.exists(opts.tempdir):
		os.mkdir(opts.tempdir)
		
	if not os.path.exists(opts.reliefdir):
		os.mkdir(opts.reliefdir)
		
	if not os.path.exists(opts.mergedir):
		os.mkdir(opts.mergedir)
except:
	print "Error: Could not create directories."
	sys.exit(0)
	

## Converience

# defines the grid, i.e. 5x5
# this merges 25 hgt files into one
chunksize = 5

testcount = 0
hgtfile = ""
checklist = []

e = 0

startnorth = 0
endnorth = 5
starteast = 0
endeast = 5
startsouth = 0
endsouth = 5
startwest = 0
endwest = 5
		
		
########## Reassign projection to imagemagic output file #############

# Geotifflib is not able to handle imagemagick, or better: TIFFs manipulated
# with imagemagick loose georeference tags in header. Usually I have reassigned
# the tags with geotifcp from geotifflib but geotifcp doesn't understand the
# imagemagick tiffs anymore. geotifcp may work for other (commercial) image 
# processors ... but, there is an easier way to do this anyway, using GDAL
# to take the projection/transform from a file and assign it to another:

def copyprojection(inputfile, outputfile):

	datasetin = gdal.Open(inputfile)
	if datasetin is None:
		print 'Unable to open', inputfile, 'for reading'
		sys.exit(1)

	projection   = datasetin.GetProjection()
	geotransform = datasetin.GetGeoTransform()

	if projection is None and geotransform is None:
		print 'No projection found in file' + inputfile
		sys.exit(1)

	datasetout = gdal.Open(outputfile, gdal.GA_Update)

	if outputfile is None:
		print 'Unable to open', output, 'for writing'
		sys.exit(1)

	datasetout.SetGeoTransform(geotransform)
	datasetout.SetProjection(projection)


########## Imagework parameters #############

# This defines the image processing parameters for the jobs to be done with
# gdal and imagemagick.
#
# mergeparam: this merges the .hgt files in one single file chunksize x chunksize
# hillshade: two passes with different angles, multiply
# coastline: creating a fake colour relief to get 0 as ocean-mask and rgb projection/transform
# imageshack: multiply and running imagemagick functions, modulate
# finish: combine images
# geotag: the tag is adapted elsewhere, just move the finished file to relief dir
# clean: remove temporary files in temp dir

def imageworkparam(shiftedfilenamex,mergelist):

	global hillshadeparam1,hillshadeparam2,hillshadeparam3
	global hillshadeparam1_mpc,hillshadeparam2_mpc
	global coastlineparam1,coastlineparam2, coastlineparam3, coastlineparam4
	global coastlineparam1_mpc,coastlineparam2_mpc
	global imageshackparam1,imageshackparam2,imageshackparam3,imageshackparam4,imageshackparam5
	global finishparam1,finishparam2
	global geotagparam1, geotagparam2
	global cleanparam
	global mergeparam2

	tempdir = opts.tempdir ## Shortcut for now
	
	# Merge all .hgt files to the new 5x5 chunks
	mergeparam = "gdal_merge.py -o "+tempdir+"/merged_"+shiftedfilenamex+".tif -ot UInt16 "+tempdir+"/"+shiftedfilenamex+".tif "
	
	# Create the hillshades, from two angles, multiply.
	hillshadeparam1 = "gdaldem hillshade "+tempdir+"/merged_"+shiftedfilenamex+".tif "+tempdir+"/relief1_"+shiftedfilenamex+".tif -z 0.05 -s 9650.0 -az 315.0 -alt 38.0 -of GTiff"
	hillshadeparam1_mpc = "convert "+tempdir+"/relief1_"+shiftedfilenamex+".tif "+tempdir+"/relief1_"+shiftedfilenamex+".mpc"
	hillshadeparam2 = "gdaldem hillshade "+tempdir+"/merged_"+shiftedfilenamex+".tif "+tempdir+"/relief2_"+shiftedfilenamex+".tif -z 0.05 -s 7015.0 -az 55.0 -alt 38.0 -of GTiff"
	hillshadeparam2_mpc = "convert "+tempdir+"/relief2_"+shiftedfilenamex+".tif "+tempdir+"/relief2_"+shiftedfilenamex+".mpc"
	hillshadeparam3 = "composite -compose Multiply "+tempdir+"/relief1_"+shiftedfilenamex+".mpc "+tempdir+"/relief2_"+shiftedfilenamex+".mpc "+tempdir+"/multiply_"+shiftedfilenamex+".mpc"
	
	# Mask coastline (set sea color in maskmap.txt)
	# Do some image work to get smoother coastline at the end
	coastlineparam1 = "gdaldem color-relief "+tempdir+"/merged_"+shiftedfilenamex+".tif colourmaps/maskmap.txt "+tempdir+"/coastline1_"+shiftedfilenamex+".tif"
	coastlineparam1_mpc = "convert "+tempdir+"/coastline1_"+shiftedfilenamex+".tif "+tempdir+"/coastline1_"+shiftedfilenamex+".mpc"
	coastlineparam2 = "gdaldem color-relief "+tempdir+"/merged_"+shiftedfilenamex+".tif colourmaps/colourmap-coastonly.txt "+tempdir+"/coastline2_"+shiftedfilenamex+".tif"
	coastlineparam2_mpc = "convert "+tempdir+"/coastline2_"+shiftedfilenamex+".tif "+tempdir+"/coastline2_"+shiftedfilenamex+".mpc"
	
	# The blur radius should never be smaller than the sigma and a int, but 0 will take '3'. I set
	# the radius to 1 for now, looks ok so far, doesn't it
	coastlineparam3 = "convert -blur 1x0.5 "+tempdir+"/coastline1_"+shiftedfilenamex+".mpc "+tempdir+"/blur_"+shiftedfilenamex+".mpc"
	
	
	# Do some work on the relief
	imageshackparam1 = "composite -compose Multiply "+tempdir+"/relief1_"+shiftedfilenamex+".mpc "+tempdir+"/relief2_"+shiftedfilenamex+".mpc "+tempdir+"/multiply_"+shiftedfilenamex+".mpc" 
	imageshackparam2 = "convert "+tempdir+"/multiply_"+shiftedfilenamex+".mpc  -size 1x1 xc:'rgb(204,153,51)' -fx '1-(1-v.p{0,0})*(1-u)' "+tempdir+"/multiply_"+shiftedfilenamex+".mpc" 
	imageshackparam3 = "composite -compose Darken "+tempdir+"/multiply_"+shiftedfilenamex+".mpc "+tempdir+"/relief1_"+shiftedfilenamex+".mpc "+tempdir+"/darken_"+shiftedfilenamex+".mpc"
	imageshackparam4 = "convert -modulate 120,100 "+tempdir+"/darken_"+shiftedfilenamex+".mpc "+tempdir+"/darken_mod_"+shiftedfilenamex+".mpc"
	imageshackparam5 = "convert "+tempdir+"/darken_mod_"+shiftedfilenamex+".mpc  -fill white -colorize 70%  "+tempdir+"/finish_"+shiftedfilenamex+".mpc"
	
	# Bring it all together
	
	# don't need the blur here?
	finishparam1 = "composite -compose Darken "+tempdir+"/finish_"+shiftedfilenamex+".mpc "+tempdir+"/blur_"+shiftedfilenamex+".mpc "+tempdir+"/end1_"+shiftedfilenamex+".tif"
	# without the blur
	#finishparam1 = "composite -compose Darken "+tempdir+"/finish_"+shiftedfilenamex+".tif "+tempdir+"/coastline1_"+shiftedfilenamex+".tif "+tempdir+"/end1_"+shiftedfilenamex+".tif"

	
	finishparam2 = "composite -compose Multiply "+tempdir+"/end1_"+shiftedfilenamex+".tif "+tempdir+"/coastline2_"+shiftedfilenamex+".mpc "+tempdir+"/end2_"+shiftedfilenamex+".tif"	
	# This moves the reassigned geotiff (tag comes from the coastline colour file, 
	# thanks to fake colourrelief used as colourmask for sea we have one ...
	# Move merged DEM files to merged directory
	# geotagparam name should be changed to something meaningful
	geotagparam1 = "mv "+tempdir+"/end2_"+shiftedfilenamex+".tif "+opts.reliefdir+"/"+shiftedfilenamex+".tif"
	geotagparam2 = "mv "+tempdir+"/merged_"+shiftedfilenamex+".tif "+opts.mergedir+"/"+shiftedfilenamex+".tif"
	
	# Clean temp dir
	cleanparam = "rm -R "+tempdir+"/*"

	
	stringlist = ""
	for i in mergelist:
		stringlist = stringlist+str(i)+" "
	mergeparam2 = mergeparam+stringlist


########## Imagework job #############

# Beside of geotag assignement done directly with gdal these are python subprocesses
# at the moment. Someone should take care what can be taken out to more direct ogr2ogr
# and gdal work, nut guess the imagemagick work remains subprocesses.
	
def imageworkjob(shiftedfilenamex,ogrparam,rasterparam):

	global fileinlist

	subprocess.call(ogrparam, shell=True)
	subprocess.call(rasterparam, shell=True)
	subprocess.call(mergeparam2, shell=True)
	subprocess.call(hillshadeparam1, shell=True)
	subprocess.call(hillshadeparam1_mpc, shell=True)
	subprocess.call(hillshadeparam2, shell=True)
	subprocess.call(hillshadeparam2_mpc, shell=True)
	subprocess.call(hillshadeparam3, shell=True)
	subprocess.call(coastlineparam1, shell=True)
	subprocess.call(coastlineparam1_mpc, shell=True)
	subprocess.call(coastlineparam2, shell=True)
	subprocess.call(coastlineparam2_mpc, shell=True)
	subprocess.call(coastlineparam3, shell=True)
	subprocess.call(imageshackparam1, shell=True)
	subprocess.call(imageshackparam2, shell=True)
	subprocess.call(imageshackparam3, shell=True)
	subprocess.call(imageshackparam4, shell=True)
	subprocess.call(imageshackparam5, shell=True)
	subprocess.call(finishparam1, shell=True)
	subprocess.call(finishparam2, shell=True)
			
	copyprojection(tempdir+"/coastline1_"+shiftedfilenamex+".tif",""+tempdir+"/end2_"+shiftedfilenamex+".tif")
	subprocess.call(geotagparam1, shell=True)
	subprocess.call(geotagparam2, shell=True)
			
	subprocess.call(cleanparam, shell=True)
	fileinlist = 0



########## Going East #############

def count_north_e(startpoint,endpoint):
	global starteast, endeast
	for n in range(startpoint,endpoint):
		if n < 10:
			northstring = "N0" + str(n)
		else:
			northstring = "N" + str(n)
		
		count_east(northstring, starteast, endeast)
		
def count_south_e(startpoint,endpoint):
	global starteast, endeast
	for n in range(startpoint,endpoint):
		if n < 10:
			southstring = "S0" + str(n)
		else:
			southstring = "S" + str(n)
		
		count_east(southstring, starteast, endeast)

def count_east(northstring, starteast, endeast):
	global testcount, hgtfile, checklist
	for e in range(starteast, endeast):
		#e = e + 1
		if e < 10:
			hgtfile = northstring + "E00" + str(e+1)
		elif e < 100:
			hgtfile = northstring + "E0" + str(e+1)
		elif e < 1000:
			hgtfile = northstring + "E" + str(e+1)
		testcount += 1
		
		checklist.append(hgtfile)

def count_north_e(startpoint,endpoint):
	global starteast, endeast
	for n in range(startpoint,endpoint):
		if n < 10:
			northstring = "N0" + str(n)
		else:
			northstring = "N" + str(n)
		
		count_east(northstring, starteast, endeast)
		
def count_south_e(startpoint,endpoint):
	global starteast, endeast
	for n in range(startpoint,endpoint):
		if n < 10:
			southstring = "S0" + str(n)
		else:
			southstring = "S" + str(n)
		
		count_east(southstring, starteast, endeast)

def countnortheast():
	global startnorth, endnorth
	global checklist
	shiftedfilenamex = ""
	shiftedfilenamex_n = ""
	shiftedfilenamex_e = ""
	
	#hgtfile = opts.hgtfile # shortcut for now
	
	for i in range(18):
		count_north_e(startnorth,endnorth)
		
		shpfilename = hgtfile
		spliteast = int(hgtfile.split("E")[1]) # east goes plus
		splitnorth = int(hgtfile.split("E")[0].strip("N")) # north goes plus
		
		if int(hgtfile.split("E")[0].strip("N")) < 10:
			shiftedfilenamex_n = "N0"+str(int(hgtfile.split("E")[0].strip("N"))-4)
			if int(hgtfile.split("E")[1].strip("E"))-5 < 10:
				shiftedfilenamex_e = "E00"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 100:
				shiftedfilenamex_e = "E0"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 1000:
				shiftedfilenamex_e = "E"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			shiftedfilenamex = shiftedfilenamex_n+shiftedfilenamex_e
		else:
			shiftedfilenamex_n = "N"+str(int(hgtfile.split("E")[0].strip("N"))-4)
			if int(hgtfile.split("E")[1].strip("E"))-5 < 10:
				shiftedfilenamex_e = "E00"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 100:
				shiftedfilenamex_e = "E0"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 1000:
				shiftedfilenamex_e = "E"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			shiftedfilenamex = shiftedfilenamex_n+shiftedfilenamex_e
		
		ogrparam = "ogr2ogr -f 'ESRI Shapefile' "+opts.tempdir+"/"+shiftedfilenamex+".shp earthshape/earth.shp -clipsrc "+str(spliteast-5)+" "+str(splitnorth-4)+" "+str(spliteast)+" "+str(splitnorth+1)+" -overwrite"
		rasterparam = "gdal_rasterize -of GTiff -ot UInt16 -a shapeid -ts 18001 18001 -l "+shiftedfilenamex+" "+opts.tempdir+"/"+shiftedfilenamex+".shp "+opts.tempdir+"/"+shiftedfilenamex+".tif"
						
		fileinlist = 0
		
		if len(checklist) < 25:
			checklist.append(hgtfile)
			
			
		mergelist = []
		for file in checklist:
			shiftedfilename = ""
			shiftedfilename_n = ""
			shiftedfilename_e = ""
			if int(file.split("E")[0].strip("N")) < 10:
				shiftedfilename_n = "N0"+str(int(file.split("E")[0].strip("N")))
				if int(file.split("E")[1].strip("E"))-1 < 10:
					shiftedfilename_e = "E00"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E"))-1 < 100:
					shiftedfilename_e = "E0"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E"))-1 < 1000:
					shiftedfilename_e = "E"+str(int(file.split("E")[1].strip("E"))-1)
				shiftedfilename = shiftedfilename_n+shiftedfilename_e
			else:
				shiftedfilename_n = "N"+str(int(file.split("E")[0].strip("N")))
				if int(file.split("E")[1].strip("E"))-1 < 10:
					shiftedfilename_e = "E00"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E"))-1 < 100:
					shiftedfilename_e = "E0"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E"))-1 < 1000:
					shiftedfilename_e = "E"+str(int(file.split("E")[1].strip("E"))-1)
				shiftedfilename = shiftedfilename_n+shiftedfilename_e
				
			
			hgtfilepath = ""+opts.hgtdir+"/"+shiftedfilename+".hgt"
			if os.path.exists(hgtfilepath):
				mergelist.append(hgtfilepath)
				fileinlist = 1
		
		imageworkparam(shiftedfilenamex,mergelist)
		
		# when a file exist in the mergelist do the job
		if fileinlist > 0:
			imageworkjob(shiftedfilenamex,ogrparam,rasterparam)
		
		startnorth += 5
		endnorth += 5
		
		# reset checklist
		checklist = []

def countsoutheast():
	global startsouth, endsouth
	global checklist
	shiftedfilenamex = ""
	shiftedfilenamex_n1 = ""
	shiftedfilenamex_n2 = ""
	shiftedfilenamex_e = ""
	
	for i in range(18):
		count_south_e(startsouth,endsouth)
		
		shpfilename = hgtfile
		spliteast = int(hgtfile.split("E")[1]) # east goes plus
		splitsouth = int(hgtfile.split("E")[0].strip("S"))*-1.0 # south goes minus
		
		if int(hgtfile.split("E")[0].strip("S")) < 10:
			shiftedfilenamex_n1 = "S0"+str(int(hgtfile.split("E")[0].strip("S"))+1)
			shiftedfilenamex_n2 = shiftedfilenamex_n1.replace("S010","S10")
			if int(hgtfile.split("E")[1].strip("E"))-5 < 10:
				shiftedfilenamex_e = "E00"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 100:
				shiftedfilenamex_e = "E0"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 1000:
				shiftedfilenamex_e = "E"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			shiftedfilenamex = shiftedfilenamex_n2+shiftedfilenamex_e
		else:
			shiftedfilenamex_n1 = "S"+str(int(hgtfile.split("E")[0].strip("S"))+1)
			shiftedfilenamex_n2 = shiftedfilenamex_n1.replace("S010","S10")
			if int(hgtfile.split("E")[1].strip("E"))-5 < 10:
				shiftedfilenamex_e = "E00"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 100:
				shiftedfilenamex_e = "E0"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			elif int(hgtfile.split("E")[1].strip("E"))-5 < 1000:
				shiftedfilenamex_e = "E"+str(int(hgtfile.split("E")[1].strip("E"))-5)
			shiftedfilenamex = shiftedfilenamex_n2+shiftedfilenamex_e
		
		ogrparam = "ogr2ogr -f 'ESRI Shapefile' "+opts.tempdir+"/"+shiftedfilenamex+".shp earthshape/earth.shp -clipsrc "+str(spliteast-5)+" "+str(splitsouth-1)+" "+str(spliteast)+" "+str(splitsouth+4)+" -overwrite"
		rasterparam = "gdal_rasterize -of GTiff -ot UInt16 -a shapeid -ts 18001 18001 -l "+shiftedfilenamex+" "+opts.tempdir+"/"+shiftedfilenamex+".shp "+opts.tempdir+"/"+shiftedfilenamex+".tif"
		
		
		fileinlist = 0
		
		if len(checklist) < 25:
			checklist.append(hgtfile)
			
			
		mergelist = []
		for file in checklist:
			shiftedfilename = ""
			shiftedfilename_n1 = ""
			shiftedfilename_n2 = ""
			shiftedfilename_e = ""
			if int(file.split("E")[0].strip("S")) < 10:
				shiftedfilename_n1 = "S0"+str(int(file.split("E")[0].strip("S"))+1)
				shiftedfilename_n2 = shiftedfilename_n1.replace("S010","S10")
				if int(file.split("E")[1].strip("E")) < 10:
					shiftedfilename_e = "E00"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E")) < 100:
					shiftedfilename_e = "E0"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E")) < 1000:
					shiftedfilename_e = "E"+str(int(file.split("E")[1].strip("E"))-1)
				shiftedfilename = shiftedfilename_n2+shiftedfilename_e
			else:
				shiftedfilename_n1 = "S"+str(int(file.split("E")[0].strip("S"))+1)
				shiftedfilename_n2 = shiftedfilename_n1.replace("S010","S10")
				if int(file.split("E")[1].strip("E")) < 10:
					shiftedfilename_e = "E00"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E")) < 100:
					shiftedfilename_e = "E0"+str(int(file.split("E")[1].strip("E"))-1)
				elif int(file.split("E")[1].strip("E")) < 1000:
					shiftedfilename_e = "E"+str(int(file.split("E")[1].strip("E"))-1)
				shiftedfilename = shiftedfilename_n2+shiftedfilename_e
				
			
			hgtfilepath = ""+opts.hgtdir+"/"+shiftedfilename+".hgt"
			
			#print hgtfilepath
			
			if os.path.exists(hgtfilepath):
				mergelist.append(hgtfilepath)
				fileinlist = 1
		
		imageworkparam(shiftedfilenamex,mergelist)
		
		
		# when a file exist in the mergelist do the job
		if fileinlist > 0:
			imageworkjob(shiftedfilenamex,ogrparam,rasterparam)
		
		startsouth += 5
		endsouth += 5
		
		# reset checklist
		checklist = []
		
		
for i in range(36):
	countnortheast()

	starteast += 5
	endeast += 5

	startnorth = 0
	endnorth = 5
	
starteast = 0
endeast = 5
	
for i in range(36):
	countsoutheast()

	starteast += 5
	endeast += 5

	startsouth = 0
	endsouth = 5

# Reset
checklist = []


########## Going West #############

def count_west(northstring, startwest, endwest):
	global testcount, hgtfile, checklist
	for e in range(startwest, endwest):
		#e = e + 1
		if e < 10:
			hgtfile = northstring + "W00" + str(e+1)
		elif e < 100:
			hgtfile = northstring + "W0" + str(e+1)
		elif e < 1000:
			hgtfile = northstring + "W" + str(e+1)
		testcount += 1
		
		checklist.append(hgtfile)

def count_north_w(startpoint,endpoint):
	global startwest, endwest
	for n in range(startpoint,endpoint):
		if n < 10:
			northstring = "N0" + str(n)
		else:
			northstring = "N" + str(n)
		
		count_west(northstring, startwest, endwest)
		
def count_north_w(startpoint,endpoint):
	global startwest, endwest
	for n in range(startpoint,endpoint):
		if n < 10:
			northstring = "N0" + str(n)
		else:
			northstring = "N" + str(n)
		
		count_west(northstring, startwest, endwest)
		
def count_south_w(startpoint,endpoint):
	global startwest, endwest
	for n in range(startpoint,endpoint):
		if n < 10:
			southstring = "S0" + str(n)
		else:
			southstring = "S" + str(n)
		
		count_west(southstring, startwest, endwest)


def countnorthwest():
	global startnorth, endnorth
	global checklist
	shiftedfilenamex = ""
	shiftedfilenamex_n = ""
	shiftedfilenamex_e = ""
	shiftedfilenamex_e2 = ""
	
	for i in range(18):
		count_north_w(startnorth,endnorth)
		
		shpfilename = hgtfile
		splitwest = int(hgtfile.split("W")[1])*-1.0 # west goes minus
		splitnorth = int(hgtfile.split("W")[0].strip("N")) # north goes plus
		
		if int(hgtfile.split("W")[0].strip("N")) < 10:
			shiftedfilenamex_n = "N0"+str(int(hgtfile.split("W")[0].strip("N"))-4)
			if int(hgtfile.split("W")[1].strip("W"))-5 < 10:
				shiftedfilenamex_e = "W00"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 100:
				shiftedfilenamex_e = "W0"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 1000:
				shiftedfilenamex_e = "W"+str(int(hgtfile.split("W")[1].strip("W")))
			shiftedfilenamex_e2 = shiftedfilenamex_e.replace("W0100","W100").replace("W0010","W010")
			shiftedfilenamex = shiftedfilenamex_n+shiftedfilenamex_e2
		else:
			shiftedfilenamex_n = "N"+str(int(hgtfile.split("W")[0].strip("N"))-4)
			if int(hgtfile.split("W")[1].strip("W"))-5 < 10:
				shiftedfilenamex_e = "W00"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 100:
				shiftedfilenamex_e = "W0"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 1000:
				shiftedfilenamex_e = "W"+str(int(hgtfile.split("W")[1].strip("W")))
			shiftedfilenamex_e2 = shiftedfilenamex_e.replace("W0100","W100").replace("W0010","W010")
			shiftedfilenamex = shiftedfilenamex_n+shiftedfilenamex_e2
		
		ogrparam = "ogr2ogr -f 'ESRI Shapefile' "+opts.tempdir+"/"+shiftedfilenamex+".shp earthshape/earth.shp -clipsrc "+str(splitwest)+" "+str(splitnorth-4)+" "+str(splitwest+5)+" "+str(splitnorth+1)+" -overwrite"
		rasterparam = "gdal_rasterize -of GTiff -ot UInt16 -a shapeid -ts 18001 18001 -l "+shiftedfilenamex+" "+opts.tempdir+"/"+shiftedfilenamex+".shp "+opts.tempdir+"/"+shiftedfilenamex+".tif"
						
		fileinlist = 0
		
		if len(checklist) < 25:
			checklist.append(hgtfile)
			
			
		mergelist = []
		for file in checklist:
			shiftedfilename = ""
			shiftedfilename_n = ""
			shiftedfilename_e = ""
			if int(file.split("W")[0].strip("N")) < 10:
				shiftedfilename_n = "N0"+str(int(file.split("W")[0].strip("N")))
				if int(file.split("W")[1].strip("W"))-1 < 10:
					shiftedfilename_e = "W00"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W"))-1 < 100:
					shiftedfilename_e = "W0"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W"))-1 < 1000:
					shiftedfilename_e = "W"+str(int(file.split("W")[1].strip("W")))
				shiftedfilename_e2 = shiftedfilename_e.replace("W0100","W100").replace("W0010","W010")
				shiftedfilename = shiftedfilename_n+shiftedfilename_e2
			else:
				shiftedfilename_n = "N"+str(int(file.split("W")[0].strip("N")))
				if int(file.split("W")[1].strip("W"))-1 < 10:
					shiftedfilename_e = "W00"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W"))-1 < 100:
					shiftedfilename_e = "W0"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W"))-1 < 1000:
					shiftedfilename_e = "W"+str(int(file.split("W")[1].strip("W")))
				shiftedfilename_e2 = shiftedfilename_e.replace("W0100","W100").replace("W0010","W010")
				shiftedfilename = shiftedfilename_n+shiftedfilename_e2
				
			
			hgtfilepath = "%s/%s.hgt" % (opts.hgtdir, shiftedfilename)
			if os.path.exists(hgtfilepath):
				mergelist.append(hgtfilepath)
				fileinlist = 1
		
		imageworkparam(shiftedfilenamex,mergelist)
		
		# when a file exist in the mergelist do the job
		if fileinlist > 0:
			imageworkjob(shiftedfilenamex,ogrparam,rasterparam)
		
		startnorth += 5
		endnorth += 5
		
		# reset checklist
		checklist = []

def countsouthwest():
	global startsouth, endsouth
	global checklist
	shiftedfilenamex = ""
	shiftedfilenamex_n = ""
	shiftedfilenamex_w = ""
	shiftedfilenamex_w2 = ""
	
	for i in range(18):
		count_south_w(startsouth,endsouth)
		
		shpfilename = hgtfile
		splitwest = int(hgtfile.split("W")[1])*-1.0 # west goes minus
		splitsouth = int(hgtfile.split("W")[0].strip("S"))*-1.0 # south goes minus
		
		if int(hgtfile.split("W")[0].strip("S")) < 10:
			shiftedfilenamex_n1 = "S0"+str(int(hgtfile.split("W")[0].strip("S"))+1)
			shiftedfilenamex_n2 = shiftedfilenamex_n1.replace("S010","S10")
			if int(hgtfile.split("W")[1].strip("W"))-5 < 10:
				shiftedfilenamex_w = "W00"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 100:
				shiftedfilenamex_w = "W0"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 1000:
				shiftedfilenamex_w = "W"+str(int(hgtfile.split("W")[1].strip("W")))
			shiftedfilenamex_w2 = shiftedfilenamex_w.replace("W0100","W100").replace("W0010","W010")
			shiftedfilenamex = shiftedfilenamex_n2+shiftedfilenamex_w2
			
		else:
			shiftedfilenamex_n1 = "S"+str(int(hgtfile.split("W")[0].strip("S"))+1)
			shiftedfilenamex_n2 = shiftedfilenamex_n1.replace("S010","S10")
			if int(hgtfile.split("W")[1].strip("W"))-5 < 10:
				shiftedfilenamex_w = "W00"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 100:
				shiftedfilenamex_w = "W0"+str(int(hgtfile.split("W")[1].strip("W")))
			elif int(hgtfile.split("W")[1].strip("W"))-5 < 1000:
				shiftedfilenamex_w = "W"+str(int(hgtfile.split("W")[1].strip("W")))
			shiftedfilenamex_w2 = shiftedfilenamex_w.replace("W0100","W100").replace("W0010","W010")
			shiftedfilenamex = shiftedfilenamex_n2+shiftedfilenamex_w2
		
		ogrparam = "ogr2ogr -f 'ESRI Shapefile' "+opts.tempdir+"/"+shiftedfilenamex+".shp earthshape/earth.shp -clipsrc "+str(splitwest)+" "+str(splitsouth-1)+" "+str(splitwest+5)+" "+str(splitsouth+4)+" -overwrite"
		rasterparam = "gdal_rasterize -of GTiff -ot UInt16 -a shapeid -ts 18001 18001 -l "+shiftedfilenamex+" "+opts.tempdir+"/"+shiftedfilenamex+".shp "+opts.tempdir+"/"+shiftedfilenamex+".tif"
		
		
		fileinlist = 0
		
		if len(checklist) < 25:
			checklist.append(hgtfile)
			
			
		mergelist = []
		for file in checklist:
			shiftedfilename = ""
			shiftedfilename_n = ""
			shiftedfilename_w = ""
			if int(file.split("W")[0].strip("S")) < 10:
				shiftedfilename_n1 = "S0"+str(int(file.split("W")[0].strip("S"))+1)
				shiftedfilename_n2 = shiftedfilename_n1.replace("S010","S10")
				if int(file.split("W")[1].strip("W")) < 10:
					shiftedfilename_w = "W00"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W")) < 100:
					shiftedfilename_w = "W0"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W")) < 1000:
					shiftedfilename_w = "W"+str(int(file.split("W")[1].strip("W")))
				shiftedfilename_w2 = shiftedfilename_w.replace("W0100","W100").replace("W0010","W010")
				shiftedfilename = shiftedfilename_n2+shiftedfilename_w2
			else:
				shiftedfilename_n1 = "S"+str(int(file.split("W")[0].strip("S"))+1)
				shiftedfilename_n2 = shiftedfilename_n1.replace("S010","S10")
				if int(file.split("W")[1].strip("W")) < 10:
					shiftedfilename_w = "W00"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W")) < 100:
					shiftedfilename_w = "W0"+str(int(file.split("W")[1].strip("W")))
				elif int(file.split("W")[1].strip("W")) < 1000:
					shiftedfilename_w = "W"+str(int(file.split("W")[1].strip("W")))
				shiftedfilename_w2 = shiftedfilename_w.replace("W0100","W100").replace("W0010","W010")
				shiftedfilename = shiftedfilename_n2+shiftedfilename_w2
			
			hgtfilepath = ""+opts.hgtdir+"/"+shiftedfilename+".hgt"
			if os.path.exists(hgtfilepath):
				mergelist.append(hgtfilepath)
				fileinlist = 1
		
		imageworkparam(shiftedfilenamex,mergelist)
		
		# when a file exist in the mergelist do the job
		if fileinlist > 0:
			imageworkjob(shiftedfilenamex,ogrparam,rasterparam)
		
		startsouth += 5
		endsouth += 5
		
		# reset checklist
		checklist = []
		
		
for i in range(36):
	countnorthwest()

	startwest += 5
	endwest += 5

	startnorth = 0
	endnorth = 5
	
startwest = 0
endwest = 5
	
for i in range(36):
	countsouthwest()

	startwest += 5
	endwest += 5

	startsouth = 0
	endsouth = 5

# Reset
checklist = []

	

	
	


		