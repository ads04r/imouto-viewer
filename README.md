Imouto Viewer
=============

A web app for visualising life annotations and other 'quantified self' data.

![Imouto Viewer sample event screen](viewer/static/viewer/graphics/imouto-screenshot.png)

Imouto
------
**Imouto** is a life annotation system designed to help you maintain a 
digital record of your life with minimal effort, focused on keeping your 
data local and private. Originally developed in an academic setting 
-- which means it was written by a lone PhD student and very badly maintained --
Imouto prioritizes user privacy over cloud-based solutions.

It is **NOT** production ready.

For those interested, 'imouto' (妹) is a Japanese word, it translates as
'little sister'.

## Imouto Viewer

**Imouto Viewer** is the user-facing component of the Imouto ecosystem.
The philosophy behind Imouto is that data collection should be seamless
and unobtrusive, especially in a world full of wearables and fitness
trackers. Imouto Viewer aims to make sense of the data you collect, 
helping you visualize and understand various aspects of your life, 
without having to rely on cloud services run by people you've never met.

### What Can You Do With Imouto Viewer?

- **Import Data:** Out of the box, Imouto Viewer is limited; for its most
  useful functionality, you’ll need to run the
  [Imouto Location Manager](https://github.com/ads04r/imouto-location-manager)
  alongside it. But sensor data, such as heart rate and step count, and more
  esoteric data, such as photo metadata and IM messages, can be imported via
  the Viewer.
- **Create Life Events:** High-level annotation like life events may be
  created manually, or automatically with a bit of extra configuration effort.
- **Visualize Unique Data:** The viewer can display many types of data,
  and will generate human-readable reports for lazy diarists.
- **Custom Data Support:** The system is designed to be extensible,
  so you can process and display any kind of data that matters to you.

### Framework & Extensibility

While much of the sample data is unique to the original author (e.g., step
counts from a Pebble smartwatch), the long-term goal is to develop a
flexible framework for importing and processing arbitrary data formats.
Current functionality supports the Garmin FIT file format primarily.

## Getting Started

> **Note:** This project is under active development and is not ready for production use. The documentation and code will change frequently.

### Prerequisites

- Python 3.x
- [Imouto Location Manager](https://github.com/ads04r/imouto-location-manager) (for GPS data import)
- Basic understanding of running web applications and managing databases

## License

This project is released under the MIT License.
