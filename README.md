Imouto Viewer
=============

A web app for visualising life annotations and other 'quantified self' data.

![Imouto Viewer sample event screen](viewer/static/viewer/graphics/imouto-screenshot.png)

Imouto
------
Imouto is a life annotation system with its roots deep in academia
(which means it was written by a lone PhD student and very badly maintained)
It's a way of keeping a digital record of your life with as little user
effort as possible. These days Google will do all this for you for free,
but this is for people who would rather keep their data local.
It is **NOT** production ready.

For those interested, 'imouto' is the japanese word for 'little sister'.

Imouto Viewer
-------------
The viewer is the bit the user sees the most. My goal was always for the
data collection to be completely invisible - ubiquitous, if you like.
In a world where wearable computers such as fitness trackers are common,
this becomes trivial. But the data is only useful if you do something with
it, and that is the point of Imouto Viewer.

I'll be completely honest, the viewer is pretty useless on its own.
You need at least the [location manager](https://github.com/ads04r/imouto-location-manager)
running as well in order to
make it do anything at all, and even then you'll just be able to import
GPS tracks into it, you'll have to do all the high level stuff like creating
life events manually. Where it shines is its ability
to display other types of data which - currently - you need to add
to the database yourself, either manually or using a script.

Most of the data I have is pretty unique to me (I mean, who else tracks
their steps with a Pebble?) but I'm hoping to come up with some
kind of framework that makes it easy for anyone to import and process
any kind of data. I've already got scripts that read Garmin FIT files
and edit features so I can get *something* out the door, and worry
about which formats I'm going to try and support later, because they
*will* change over time (and, in fact, already have, several times).
