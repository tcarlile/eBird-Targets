# eBird-Targets
The first version of this script was written to help me prepare for an eleven day birding trip to South and West Texas. Several other birders had shared their eBird trip reports with me. These reports were incredibly helpful, but synthesizing everything was difficult. This script was written to help create something digestible that would allow me to focus on study species and to help in planning daily trip agendas, and in decision making on the fly while out in the field. A trip to Costa Rica prompted a rewrite to streamline and eliminate as many manual steps as possible.

You'll need to do some research first, I can't automate this part! Primarily this is the hotspots that you're interested in visiting. The eBird hotspots map, and other birders are helpful for this bit. Once you have a list of hotspots, you're ready to go. The script will output a table of frequencies of target species across your hotspots of interest.

## Highlights
Starting with a text file containing eBird Hotspot (or region) IDs of interest and a configuration file, this script will: 
- Logon to your eBird account, load the targets page for each hotspot, & parse the targets table
- Combine the hotspot targets tables into a taxonomically sorted table: Species x Hotspot
- Output an excel sheet of the Species x Hotspot table, color coded by frequency
- Output a "Study Guide" for targets, just an HTML file with links to eBird species account pages

## Details & Caveats
List of things that might be worth mentioning
- password stuff
- Hotspot order These should be ordered in the order in which you would like them to app
- Parses anything that shows up on your eBird Lofe List, so both "Native & Naturalized" & 
"Exotic: Provisional" species will be listed in the output.
- Color key: gray < cutoff, red cutoff - 10%, yellow 10-25%, blue 25-50%, green >50%
- Rarities: long staying rarities can yield spurious targets. e.g. Surfbird on south padre island (look up deets)
- languages, only english at the moment
- have not tested with windows line endings only linux/mac

## Usage
This script is run in the command line using the following command: ```python3 targets_parser.py```. The script should be run in a directory containing an ```ebird.cfg``` file, a file containing hotspots of interest, and the Clements/eBird taxonomy csv file (see below for details).

All relevant parameters are passed to the script in a configuration file that must be named ```ebird.cfg```. The format for each parameter passed to the script is ```parameter = value```. The text to the left of the ```=``` should not be changed. See an example config file below, followed by a description of each parameter:

```
[ebird-config]
user = YourUserName
pw = YourPassword
hotspots = hotspots.txt
filebase = YourDestination
bmo = 1
emo = 1
reg = world
list = life
cutoff = 1.5
taxonomy = eBird-Clements-v2024-integrated-checklist-October-2024-rev.csv
taxsort = sort v2024
speccol = English name
```

- ```user = ``` Your eBird username
- ```pw = ``` Your eBird password
- ```hotspots = ``` A text file containing eBird hotspot IDs of interest. You can find the hotspot ID in the hotspot's eBird URL. For example the web address for Mount Auburn Cemetery is ```https://ebird.org/hotspot/L207391```, and the hotspot ID is ```L207391```. See an example file below.
- ```filebase = ``` A prefix for the script's output files. For example, if you're preparing for a trip to Costa Rica you might use a prefix of ```CostaRica```
- ```bmo = ``` The beginning month of your time period of interest. Acceptable vales are ```1-12```
- ```emo = ``` The ending month of your time period of interest. Acceptable vales are ```1-12```
- ```reg = ``` The region list you want targets for. ```world``` specifies targets for your world life list. Other options are the hotspot ID or region ID. 
- ```list = ``` The list you want targets for, options are: ```life```, ```year```, ```month```, ```day```	 
- ```cutoff = ``` A percent cutoff for filtering data. A cutoff of ```1.5``` means that if a species doesn't have a frequency of >= 1.5% in at least one of your hotspots, it is filtered from the output data.
- ```taxonomy = ``` The filename for the current Clements/eBird taxonomy csv file. For example, from Oct 2024 to Oct 2025 this would be ```eBird-Clements-v2024-integrated-checklist-October-2024-rev.csv```.
- ```taxsort = ``` The column header in the taxonomy csv file that specifies the taxonomic sort order (e.g. ```sort v2024```)
- ```speccol = ``` The column header in the taxonomy csv file that specifies the species name (e.g. ```English name```)

An example hotspots file format from my Costa Rica trip. The file can have any name that you want, as long as it's specified in the ```ebird.cfg``` file:
```
L2284561
L447854
L7086691
L487975
L30207900
L444121
L448041
```

## Updates
eBird's yearly taxonomy update will necessitate downloading the latest version of the Clements/eBird checklist, and changing a couple of lines in the configuration file. I won't host these here, but will try to keep these links up to date. 

The 2024 taxonomy downloads page, and a direct link to the relevant 2024 taxonomy file are below.
- https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2024/2024-citation-checklist-downloads/
- https://www.birds.cornell.edu/clementschecklist/wp-content/uploads/2024/10/eBird-Clements-v2024-integrated-checklist-October-2024-rev.csv

Updates to the eBird website will require more significant changes to the code. eBird's 2024 style update required rewriting the code that parses the targets table HTML. Hopefully, the current eBird style will be stable for awhile.

## Dependencies
This script requires python3 with pandas, numpy, BeautifulSoup, requests, csv, and xlsxwriter. The versions I'm using are listed below, but it's unlikely that you will need this exact configuration.
- python3 [3.9.12]
- pandas [1.4.2]
- numpy [1.21.5]
- bs4 [4.11.1]
- requests [2.27.1]
- csv [1.0]
- xlsxwriter [3.0.3]
