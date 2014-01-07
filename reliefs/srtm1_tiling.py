#/usr/bin/env python
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
#   srtm1_tiling.py to create 0.1 deg heightmaps and textures from SRTM-1 data             
#                                                                                    
#   (c) 2014, Yves Sablonier, yves.at.sablonier.ch                                                                                                                                 

import sys, subprocess, os

global mode

# different gdal versions using different import
try:
    from osgeo import gdal
except ImportError:
    import gdal
	
if sys.argv[1] == "--help" or sys.argv[1] == "-h" or sys.argv[1] == "" or sys.argv[1] == "help" or sys.argv[1] == "":
   print """Usage: python srtm1_tiling.py <deminputfile> <tilesfolder> <max-resolution> <mode>
   			
Modes:  - mode '0' mode creates ENVI heightmaps with .bin ending (without the hdr file).
- mode '1' creates PNG files.
   			
Example for heightmaps with max. resolution of 256x256 pixel / 0.1 degree:
python srtm1_tiling.py N35W125.tif heightmaps 256 0

Example for textures with max. resolution of 256x256 pixel / 0.1 degree:
python srtm1_tiling.py N35W125.tif textures 256 0"""

   sys.exit(0)

try:
	deminputfile = sys.argv[1]
	demtilesfolder = sys.argv[2]
	resolution = [sys.argv[3]]
	mode = sys.argv[4]
	
	if not os.path.exists(deminputfile):
		print "Error: inputfile does not exist."

except:
	print "Error: Could not run the script."

# This is not dynamic yet, we create 0.1 degree tiles
step = 0.10



def get_tiles(start_lon,start_lat,res):

	for j in range (10):
		lon_name = str("%.2f" % start_lon).replace(".", "")
		lat_name = str("%.2f" % start_lat).replace(".", "")
		clippingparam = "gdalwarp -overwrite -ts "+res+" "+res+" -te -"+str(start_lon)+" "+str(start_lat)+" -"+str(start_lon-step)+" "+str(start_lat+step)+" "+deminputfile+" "+demtilesfolder+"/"+res+"/N"+lat_name+"W"+lon_name+"_"+res+"x"+res+".tif"
		
		if (mode == "0"):
			translateparam = "gdal_translate -ot UInt16 -of ENVI "+demtilesfolder+"/"+res+"/N"+lat_name+"W"+lon_name+"_"+res+"x"+res+".tif"+" "+demtilesfolder+"/"+res+"/N"+lat_name+"W"+lon_name+"_"+res+"x"+res+".bin"
		
		if (mode == "1"):
			translateparam = "gdal_translate -of PNG "+demtilesfolder+"/"+res+"/N"+lat_name+"W"+lon_name+"_"+res+"x"+res+".tif"+" "+demtilesfolder+"/"+res+"/N"+lat_name+"W"+lon_name+"_"+res+"x"+res+".png"
		start_lon = start_lon + step
		subprocess.call(clippingparam, shell=True)
		subprocess.call(translateparam, shell=True)
		
	removegeotiff = "rm -R "+demtilesfolder+"/"+res+"/*.tif"
	removehdr = "rm -R "+demtilesfolder+"/"+res+"/*.hdr"
	subprocess.call(removegeotiff, shell=True)
	subprocess.call(removehdr, shell=True)
	
def tiling(res):
	# Lat/lon should be dynamically generated of course, dmd.
	# Needs extent of the origin to check against.
	start_lon = 37.0
	start_lat = 122.1
	for i in range(10):
		get_tiles(start_lat,start_lon,res)
		start_lon = start_lon+step

# Create all resolutions above >= 4x4	
for i in resolution:
	if int(i)/2 > 3:
		resolution.append(str(int(i)/2))
		
if not os.path.exists(demtilesfolder):
	os.mkdir(demtilesfolder)
		
for i in resolution:
	if not os.path.exists(demtilesfolder+"/"+i):
		os.mkdir(demtilesfolder+"/"+i)
	tiling(i)
	
