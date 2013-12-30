![FGx Logo]( http://fgx.github.io/images/fgx-cap-40x30.png) FGx Terrain Read Me
==============================================================================

Live demos (using a JavaScript viewer):

<iframe src=3d-globe.html height=300 >
<a href=http://fgx.github.io/fgx-terrain/3d-globe.html><img src=images/3d-globe.png></a>
</iframe>

<iframe src=3d-flatland.html height=300 >
<a href=http://fgx.github.io/fgx-terrain/3d-flatland.html><img src=images/3d-flatland.png></a>
</iframe>
_3D Earth and flat map of California_

 Use your point device to pan, rotate and zoom. Once the projetion issues are sorted out, these models will be overlayed with 2D maps.

## Concept
### Mission
Provide 3D terrain elevation data for the entire earth at 90 meter intervals - freely and easily accessible even to new and intermediate programmers.

###Vision
Develop demos and utilities that use the 3D data in clever ways for all the major coding languages.


## Introduction
Many online mapping services follow the [Slippy Map]( http://wiki.openstreetmap.org/wiki/Slippy_Map ) standard. 
Slippy Map is, in general, a term referring to modern web maps which let you zoom and pan around (the map slips around when you drag the mouse).

Online mapping services that support Slippy Map include Google Maps, Open Street Map, MapQuest, Stamen, ArcGIS and many others.

The basis of a Slippy Map is that the map image is built up of many little square images called "tiles". These are rendered and served from a "tile server".

It is a simple technology that provides an array of benefits and features that allow you to chop and mash map data in many ways. 
But the Slippy Map services generally miss out on a hugely important aspect of our world. The data is 2D but the world is 3D.

FGx Terrain supplies this much needed 3D data - while following the Slippy Map guidelines as closely as possible.

Slippy Map tiles follow a standard format: URL/zoom-level/X/Y.png. Zoom level 0 has one tile. Zoom level 1 has 2x2 tiles. Zoom level 2 has 4x4 tiles. 
All the way up to zoom level 18 which has 2^19 x 2^18 tiles. Every Slippy Map tile is 256 x 256 pixels.

Here is the most basic Slippy Map tile (from OSM):

![http://tile.openstreetmap.org/0/0/0.png]( http://tile.openstreetmap.org/0/0/0.png )

Link: [http://tile.openstreetmap.org/0/0/0.png]( http://tile.openstreetmap.org/0/0/0.png ) 

FGx Terrain supplies the 3D data by mimicking the standard, the URL and supplying a 'height map' for each Slippy Map tile.

![http://fgx.github.io/fgx-terrain/0/0/0.png]( http://fgx.github.io/fgx-terrain/0/0/0.png ) 

Link: [http://fgx.github.io/fgx-terrain/0/0/0.png]( http://fgx.github.io/fgx-terrain/0/0/0.png ) 

The [bitmaps]( http://en.wikipedia.org/wiki/Bitmap ) (or images, [raster graphics]( http://en.wikipedia.org/wiki/Raster_graphics ) ) described here are of a special form.
Each pixel designates an altitude above or below or equal to a datum. Very often, these types of bitmaps are termed 'height maps'.

The current objective is to supply individual height maps for each Slippy Map tile up to zoom Level 7.

For tiles above level 7 there will be simple procedures that interpolate data from large (perhaps 2048 x 2048 pixels) height maps and produce the desired data at run time.
A preliminary version of the interpolator function can be viewed in the [FGx Plane Spotter]( https://github.com/fgx/fgx-plane-spotter/ ) app.

Sample of these procedurs in a variety of languages will be made available.


## Issues & Notes

The current FGx Terrain height maps follow a different projection system than the one used by most Slippy Maps.  We are currently researching the best methods for reconciling the differences. 

This repo currently contains every folder and file required to display height maps for Slippy Map levels 0 to 7.

Currently the folders contain height maps only up to level 4 - after that there is merely a dummy image of the FGx cap.


### Copyright and License
copyright &copy; 2013 Jaanga authors ~ All work herein is under the [MIT License](http://jaanga.github.io/libs/jaanga-copyright-and-mit-license.md)

[FGx copyright notice and license]( https://github.com/fgx/fgx.github.io/blob/master/fgx-copyright-notice-and-license.md )

This repository is at an early and volatile stage. Not all licensing requirements may have been fully met let alone identified. It is the intension of the authors to play fair and all such requirements will either be met or the feature in question will turned off.

### Change Log

2013-12-29 ~ Theo

* Added imges and demos
* Fresh data for zoom levels 0 to 4
* Updates to read me

2013-12-27 ~ Theo

* Read me updates

2013-12-26 ~ Theo

* Folders and files built and added
* files are all dummy images of the FGx Cap

