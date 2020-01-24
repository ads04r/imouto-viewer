Imouto Viewer
=============

A web app for visualising life annotations and other 'quantified self' data.

Imouto
------
Imouto is a life annotation system first introduced in my PhD thesis, and
later improved upon and referenced in several academic papers published by
myself and colleagues. Since I left the field of computer science research,
Imouto has evolved as technology has changed. Now, rather than rely on
a companion app on a PDA for quantifiable life data, it gets the data from
a variety of different off-the-shelf tracking devices such as fitness
trackers and smartwatches. Instead of requiring a seperate Windows
application to import data from elsewhere, it now runs as background
tasks within a web application. I've also ported most of the code to
Python (specifically Django) rather than have a mish-mash of PHP, C# and
whatever else was required at the time.

For those interested, 'imouto' is the japanese word for 'little sister'.

Imouto Viewer
-------------
The viewer is the bit the user sees the most. My goal was always for the
data collection to be completely invisible - ubiquitous, if you like.
In a world where wearable computers such as fitness trackers are common,
this becomes trivial. But the data is only useful if you do something with
it, and that is the point of Imouto Viewer.
